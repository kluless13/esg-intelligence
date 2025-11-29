"""
Find ESG documents by crawling company websites.

This is MORE EFFECTIVE than scraping ListCorp announcements because:
1. Most companies publish sustainability reports on their websites
2. Can find multi-year archives (FY2021-2025)
3. Discovers standalone ESG reports, climate disclosures, databas, etc.

Usage:
    python scripts/02b_find_via_website.py --ticker XRO -v         # Test single company
    python scripts/02b_find_via_website.py --limit 10              # Process 10 companies
    python scripts/02b_find_via_website.py --skip-existing         # Skip companies with docs
"""

import sys
import sqlite3
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH
from src.scraper.company_website import find_esg_reports


def get_companies_to_process(limit=None, ticker=None, skip_existing=False):
    """
    Get companies to crawl for website documents.

    Args:
        limit: Maximum number of companies to process
        ticker: Process only this ticker
        skip_existing: Skip companies that already have website docs

    Returns:
        List of (company_id, ticker, name, website) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    conditions = []

    if ticker:
        conditions.append(f"ticker = '{ticker.upper()}'")

    if skip_existing:
        # Skip companies that already have documents from 'website' source
        conditions.append("""
            id NOT IN (
                SELECT DISTINCT company_id
                FROM documents
                WHERE source = 'website'
            )
        """)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT id, ticker, name, website
        FROM companies
        WHERE {where_clause}
        ORDER BY ticker
    """

    if limit and not ticker:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    companies = cursor.fetchall()
    conn.close()

    return companies


def update_company_website(company_id: int, domain: str):
    """Save company website domain to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE companies
        SET website = ?
        WHERE id = ?
    """, (domain, company_id))

    conn.commit()
    conn.close()


def save_document(company_id: int, ticker: str, report: dict) -> bool:
    """
    Save discovered report to documents table.

    Args:
        company_id: Company ID
        ticker: Company ticker
        report: Report dict with url, title, type, source_page

    Returns:
        True if saved (new document), False if duplicate
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if we already have this URL
    cursor.execute("""
        SELECT id FROM documents
        WHERE (listcorp_news_url = ? OR pdf_url = ?)
    """, (report['url'], report['url']))

    if cursor.fetchone():
        conn.close()
        return False  # Already exists

    # Determine document type from title
    title_lower = report['title'].lower()
    if 'sustainability' in title_lower or 'esg' in title_lower:
        doc_type = 'sustainability_report'
    elif 'annual' in title_lower:
        doc_type = 'annual_report'
    elif 'climate' in title_lower or 'tcfd' in title_lower:
        doc_type = 'climate_disclosure'
    elif 'databook' in title_lower or 'data book' in title_lower:
        doc_type = 'esg_databook'
    else:
        doc_type = 'sustainability_report'

    # Try to extract year from title
    import re
    year_match = re.search(r'20\d{2}|FY\d{2}', report['title'])
    financial_year = None
    if year_match:
        year_str = year_match.group()
        if year_str.startswith('FY'):
            financial_year = f"FY20{year_str[2:]}"
        else:
            # Convert to FY format (assuming it's the year end)
            financial_year = f"FY{year_str}"

    # Insert document
    cursor.execute("""
        INSERT INTO documents (
            company_id,
            title,
            document_type,
            financial_year,
            listcorp_news_url,
            pdf_url,
            source,
            extraction_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        report['title'],
        doc_type,
        financial_year,
        report['source_page'],  # Store source page URL
        report['url'] if report['type'] == 'pdf' else None,
        'website',
        'pending'
    ))

    conn.commit()
    conn.close()
    return True


def main():
    """Main function to crawl company websites for ESG documents."""
    parser = argparse.ArgumentParser(description='Find ESG documents on company websites')
    parser.add_argument('--limit', type=int, help='Process only N companies')
    parser.add_argument('--ticker', type=str, help='Process single company by ticker')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip companies that already have website docs')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output')

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    print("=" * 80)
    print("ESG Intelligence - Website Crawler (Milestone 2b)")
    print("=" * 80)
    print()

    # Get companies to process
    companies = get_companies_to_process(
        limit=args.limit,
        ticker=args.ticker,
        skip_existing=args.skip_existing
    )

    if not companies:
        print("No companies to process!")
        if args.skip_existing:
            print("All companies already have website documents.")
        return

    total = len(companies)
    print(f"Processing {total} companies...")
    print()

    # Statistics
    total_websites_found = 0
    total_reports_found = 0
    total_reports_saved = 0
    companies_with_reports = 0

    # Process each company
    for i, (company_id, ticker, name, existing_website) in enumerate(companies, 1):
        print(f"[{i}/{total}] {ticker} - {name}")

        # Use existing website if we have it, otherwise will fetch from ListCorp
        domain = existing_website

        # Find reports
        reports = find_esg_reports(ticker, name, domain)

        # If we found a website and didn't have one stored, save it
        if not existing_website and reports:
            # Extract domain from first report URL
            from urllib.parse import urlparse
            domain = urlparse(reports[0]['url']).netloc.replace('www.', '')
            update_company_website(company_id, domain)
            total_websites_found += 1

        # Save reports to database
        saved_count = 0
        for report in reports:
            if save_document(company_id, ticker, report):
                saved_count += 1
                print(f"  ✓ {report['title']}")

        if saved_count > 0:
            companies_with_reports += 1

        total_reports_found += len(reports)
        total_reports_saved += saved_count

        if not reports:
            print(f"  ⚠ No reports found")

        print()  # Blank line between companies

    # Print summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Companies processed:         {total}")
    print(f"Websites discovered:         {total_websites_found}")
    print(f"Companies with reports:      {companies_with_reports} ({companies_with_reports/total*100:.1f}%)")
    print(f"Total reports found:         {total_reports_found}")
    print(f"New reports saved:           {total_reports_saved}")
    print(f"Duplicates skipped:          {total_reports_found - total_reports_saved}")
    print()

    if total_reports_saved > 0:
        print("✓ Website crawling completed!")
        print()
        print("Next steps:")
        print("  1. Check what was found:")
        print(f"     sqlite3 data/esg_intel.db \"SELECT c.ticker, d.title, d.source FROM documents d JOIN companies c ON d.company_id = c.id WHERE d.source = 'website' LIMIT 10;\"")
        print()
        print("  2. Extract text from new documents:")
        print("     python scripts/03_extract_text.py")
        print()
        print("  3. Analyze with AI:")
        print("     python scripts/04_analyze_with_ai.py --dry-run")
    else:
        print("⚠ No new reports found.")
        print()
        print("Troubleshooting:")
        print("  1. Try with verbose mode: --ticker XRO -v")
        print("  2. Check if website exists for companies:")
        print("     sqlite3 data/esg_intel.db \"SELECT ticker, name, website FROM companies LIMIT 10;\"")
        print("  3. Manually test website discovery:")
        print("     python -c \"from src.scraper.company_website import find_esg_reports; find_esg_reports('XRO', 'Xero Limited')\"")


if __name__ == "__main__":
    main()
