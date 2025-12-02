#!/usr/bin/env python3
"""
Download ESG reports using simple HTTP requests with proper headers.

This script uses direct HTTP requests to download files, which works better
than browser automation for these direct file links.

Usage:
    python scripts/download_reports_simple.py              # Download all
    python scripts/download_reports_simple.py --ticker CBA # Single company
    python scripts/download_reports_simple.py --dry-run    # Preview only
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import time
import sys
import requests
from urllib.parse import urlparse, unquote

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DB_PATH

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORT_LINKS_FILE = DATA_DIR / "report_links.json"
EXCEL_DIR = DATA_DIR / "excel"
PDF_DIR = DATA_DIR / "pdfs"

# Request headers - key is to look like a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1',
}


def get_filename_from_url(url: str) -> str:
    """Extract clean filename from URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = path.split('/')[-1]

    # Clean up filename
    filename = filename.replace('%20', '_').replace(' ', '_')

    # Handle query parameters in filename
    if '?' in filename:
        filename = filename.split('?')[0]

    return filename


def get_save_path(ticker: str, file_type: str, url: str) -> Path:
    """Determine where to save the downloaded file."""
    if file_type == 'xlsx':
        save_dir = EXCEL_DIR / ticker
    else:
        save_dir = PDF_DIR / ticker

    filename = get_filename_from_url(url)
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / filename


def download_file(url: str, save_path: Path, timeout: int = 120) -> dict:
    """
    Download a file from URL using requests with proper headers.

    Returns:
        dict with download status, file_size, etc.
    """
    result = {
        'success': False,
        'file_size': 0,
        'error': None,
        'local_path': str(save_path)
    }

    try:
        print(f"  📥 Downloading: {url[:80]}...")

        # Use a session for better connection handling
        session = requests.Session()
        session.headers.update(HEADERS)

        # Make the request
        response = session.get(
            url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
            verify=True
        )

        if response.status_code == 200:
            # Ensure parent directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file in chunks
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = save_path.stat().st_size
            result['success'] = True
            result['file_size'] = file_size

            print(f"  ✅ Saved: {save_path.name} ({file_size:,} bytes)")
        else:
            result['error'] = f"HTTP {response.status_code}"
            print(f"  ❌ Failed: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
        print(f"  ❌ Failed: Timeout after {timeout}s")
    except requests.exceptions.RequestException as e:
        result['error'] = str(e)[:100]
        print(f"  ❌ Failed: {str(e)[:50]}")
    except Exception as e:
        result['error'] = str(e)[:100]
        print(f"  ❌ Error: {str(e)[:50]}")

    return result


def update_database(ticker: str, report: dict, download_result: dict, conn: sqlite3.Connection):
    """Update database with downloaded report metadata."""
    cursor = conn.cursor()

    # First, ensure company exists and get company_id
    cursor.execute("SELECT id FROM companies WHERE ticker = ?", (ticker,))
    row = cursor.fetchone()

    if not row:
        print(f"  ⚠️  Company {ticker} not in database, skipping DB update")
        return

    company_id = row[0]

    # Check if document already exists
    cursor.execute("""
        SELECT id FROM documents
        WHERE company_id = ? AND document_url = ?
    """, (company_id, report['url']))

    existing = cursor.fetchone()

    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE documents SET
                local_path = ?,
                file_size = ?,
                downloaded_at = ?,
                extraction_status = 'downloaded'
            WHERE id = ?
        """, (
            download_result['local_path'],
            download_result['file_size'],
            datetime.now().isoformat(),
            existing[0]
        ))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO documents (
                company_id, title, document_type, financial_year,
                document_url, listcorp_news_url, local_path, file_size, downloaded_at,
                extraction_status, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'downloaded', 'manual_search')
        """, (
            company_id,
            report['title'],
            report.get('category', 'unknown'),
            report.get('year'),
            report['url'],
            '',
            download_result['local_path'],
            download_result['file_size'],
            datetime.now().isoformat()
        ))

    conn.commit()


def ensure_db_columns():
    """Ensure database has required columns for downloads."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(documents)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # Add missing columns
    new_columns = [
        ("local_path", "TEXT"),
        ("file_size", "INTEGER"),
        ("downloaded_at", "TIMESTAMP"),
        ("source", "TEXT DEFAULT 'unknown'"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}")
                print(f"  Added column: {col_name}")
            except sqlite3.OperationalError:
                pass

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Download ESG reports using simple HTTP requests')
    parser.add_argument('--ticker', type=str, help='Download for specific company ticker only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without downloading')
    parser.add_argument('--skip-existing', action='store_true', help='Skip files that already exist locally')
    parser.add_argument('--type', choices=['xlsx', 'pdf', 'all'], default='all', help='File type to download')
    args = parser.parse_args()

    # Load report links
    if not REPORT_LINKS_FILE.exists():
        print(f"❌ Report links file not found: {REPORT_LINKS_FILE}")
        return 1

    with open(REPORT_LINKS_FILE) as f:
        data = json.load(f)

    companies = data.get('companies', {})

    if args.ticker:
        ticker = args.ticker.upper()
        if ticker not in companies:
            print(f"❌ Ticker {ticker} not found in report_links.json")
            print(f"Available: {', '.join(companies.keys())}")
            return 1
        companies = {ticker: companies[ticker]}

    # Ensure DB has required columns
    if not args.dry_run:
        ensure_db_columns()

    # Stats
    total_files = 0
    downloaded = 0
    skipped = 0
    failed = 0

    # Connect to database
    conn = sqlite3.connect(DB_PATH) if not args.dry_run else None

    print(f"\n{'='*60}")
    print(f"ESG Report Downloader (Simple HTTP Mode)")
    print(f"{'='*60}")
    print(f"Companies: {len(companies)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'DOWNLOAD'}")
    print(f"Type filter: {args.type}")
    print(f"{'='*60}\n")

    for ticker, company in companies.items():
        company_name = company.get('company_name', ticker)
        reports = company.get('reports', [])

        print(f"\n📊 {ticker} - {company_name}")
        print(f"   {len(reports)} reports available")

        for report in reports:
            url = report.get('url', '')
            file_type = report.get('type', 'pdf')
            year = report.get('year', 'unknown')
            title = report.get('title', 'Unknown')

            # Skip web-only reports
            if file_type == 'web':
                print(f"  ⏭️  Skipping web report: {title}")
                skipped += 1
                continue

            # Filter by type
            if args.type != 'all' and file_type != args.type:
                continue

            total_files += 1

            # Determine save location
            save_path = get_save_path(ticker, file_type, url)

            # Check if exists
            if args.skip_existing and save_path.exists():
                print(f"  ⏭️  Already exists: {save_path.name}")
                skipped += 1
                continue

            if args.dry_run:
                print(f"  🔍 Would download: {title} ({year})")
                print(f"      → {save_path}")
            else:
                result = download_file(url, save_path)

                if result['success']:
                    downloaded += 1
                    # Update database
                    update_database(ticker, report, result, conn)
                else:
                    failed += 1

                # Rate limiting - be nice to servers
                time.sleep(2)

    if conn:
        conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total files:  {total_files}")
    print(f"Downloaded:   {downloaded}")
    print(f"Skipped:      {skipped}")
    print(f"Failed:       {failed}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("This was a dry run. Run without --dry-run to download files.")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
