#!/usr/bin/env python3
"""
Download ESG reports using Playwright browser automation.

This script uses a real browser to:
1. Navigate to each report URL
2. Handle JavaScript, redirects, and authentication
3. Automatically download files to the correct location
4. Track download status and metadata

Usage:
    python scripts/download_reports_browser.py              # Download all
    python scripts/download_reports_browser.py --ticker CBA # Single company
    python scripts/download_reports_browser.py --dry-run    # Preview only
    python scripts/download_reports_browser.py --headless   # Hide browser window
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DB_PATH

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORT_LINKS_FILE = DATA_DIR / "report_links.json"
EXCEL_DIR = DATA_DIR / "excel"
PDF_DIR = DATA_DIR / "pdfs"
DOWNLOADS_DIR = DATA_DIR / "downloads_temp"  # Temporary download location


def get_save_path(ticker: str, file_type: str, url: str) -> Path:
    """Determine where to save the downloaded file."""
    if file_type == 'xlsx':
        save_dir = EXCEL_DIR / ticker
    else:
        save_dir = PDF_DIR / ticker

    # Extract filename from URL
    filename = url.split('/')[-1].split('?')[0]

    # Clean up filename
    filename = filename.replace('%20', '_').replace(' ', '_')

    # Ensure proper extension
    if file_type == 'xlsx' and not filename.endswith('.xlsx'):
        filename += '.xlsx'
    elif file_type == 'pdf' and not filename.endswith('.pdf'):
        filename += '.pdf'

    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / filename


def download_with_browser(url: str, save_path: Path, browser, headless: bool = True) -> dict:
    """
    Download a file using Playwright browser automation.

    Returns:
        dict with download status, file_size, etc.
    """
    result = {
        'success': False,
        'file_size': 0,
        'error': None,
        'local_path': str(save_path)
    }

    context = None
    try:
        print(f"  🌐 Opening in browser: {url[:80]}...")

        # Create a new context and page
        context = browser.new_context(
            accept_downloads=True,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Ensure save directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Use expect_download to wait for download
            with page.expect_download(timeout=60000) as download_info:
                # Navigate to the URL - this should trigger download for direct file links
                page.goto(url, timeout=60000)

            # Get the download object
            download = download_info.value

            # Save the download
            download.save_as(save_path)

            # Verify the file was saved
            if save_path.exists():
                file_size = save_path.stat().st_size
                result['success'] = True
                result['file_size'] = file_size
                print(f"  ✅ Downloaded: {save_path.name} ({file_size:,} bytes)")
            else:
                result['error'] = "Download completed but file not found"
                print(f"  ❌ Download completed but file not found")

        except PlaywrightTimeout:
            # No download was triggered - try direct fetch as fallback
            print(f"  🔄 No download event, trying direct fetch...")
            try:
                response = page.goto(url, wait_until='networkidle', timeout=30000)

                if response and response.ok:
                    # Get the response body
                    body = response.body()

                    if body and len(body) > 0:
                        with open(save_path, 'wb') as f:
                            f.write(body)

                        file_size = save_path.stat().st_size
                        result['success'] = True
                        result['file_size'] = file_size
                        print(f"  ✅ Downloaded directly: {save_path.name} ({file_size:,} bytes)")
                    else:
                        result['error'] = "Empty response body"
                        print(f"  ❌ Empty response body")
                else:
                    result['error'] = f"HTTP {response.status if response else 'N/A'}"
                    print(f"  ❌ Failed: HTTP {response.status if response else 'N/A'}")

            except Exception as e:
                result['error'] = str(e)[:100]
                print(f"  ❌ Direct fetch failed: {str(e)[:50]}")

        except Exception as e:
            result['error'] = str(e)[:100]
            print(f"  ❌ Error: {str(e)[:50]}")

    except Exception as e:
        result['error'] = str(e)[:100]
        print(f"  ❌ Browser error: {str(e)[:50]}")

    finally:
        if context:
            try:
                context.close()
            except:
                pass

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
    parser = argparse.ArgumentParser(description='Download ESG reports using browser automation')
    parser.add_argument('--ticker', type=str, help='Download for specific company ticker only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without downloading')
    parser.add_argument('--skip-existing', action='store_true', help='Skip files that already exist locally')
    parser.add_argument('--type', choices=['xlsx', 'pdf', 'all'], default='all', help='File type to download')
    parser.add_argument('--headless', action='store_true', default=False, help='Run browser in headless mode (no window)')
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
    print(f"ESG Report Downloader (Browser Mode)")
    print(f"{'='*60}")
    print(f"Companies: {len(companies)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'DOWNLOAD'}")
    print(f"Browser: {'Headless' if args.headless else 'Visible'}")
    print(f"Type filter: {args.type}")
    print(f"{'='*60}\n")

    if not args.dry_run:
        # Start Playwright
        with sync_playwright() as p:
            print("🚀 Launching browser...")
            browser = p.chromium.launch(headless=args.headless)

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

                    result = download_with_browser(url, save_path, browser, args.headless)

                    if result['success']:
                        downloaded += 1
                        # Update database
                        update_database(ticker, report, result, conn)
                    else:
                        failed += 1

                    # Rate limiting
                    time.sleep(2)

            browser.close()
    else:
        # Dry run mode
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

                if file_type == 'web':
                    skipped += 1
                    continue

                if args.type != 'all' and file_type != args.type:
                    continue

                total_files += 1
                save_path = get_save_path(ticker, file_type, url)

                if args.skip_existing and save_path.exists():
                    print(f"  ⏭️  Already exists: {save_path.name}")
                    skipped += 1
                else:
                    print(f"  🔍 Would download: {title} ({year})")
                    print(f"      → {save_path}")

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
