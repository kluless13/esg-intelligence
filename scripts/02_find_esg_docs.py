"""
Find ESG documents for ASX companies on ListCorp.

This script searches ListCorp news pages for each company to find
ESG-related documents like sustainability reports and annual reports.

Usage:
    python scripts/02_find_esg_docs.py              # Process all companies
    python scripts/02_find_esg_docs.py --limit 10   # Process first 10 companies
    python scripts/02_find_esg_docs.py --ticker XRO # Process single company
    python scripts/02_find_esg_docs.py --skip-existing  # Skip companies with existing docs
"""
import sys
import sqlite3
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH
from src.scraper.listcorp_news import find_esg_documents, extract_company_slug_from_url


def get_companies_to_process(limit=None, ticker=None, skip_existing=False):
    """
    Get list of companies to process from database.

    Args:
        limit: Maximum number of companies to process
        ticker: Process only this specific ticker
        skip_existing: Skip companies that already have documents

    Returns:
        List of (company_id, ticker, name, listcorp_url) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if ticker:
        # Process single company
        cursor.execute("""
            SELECT id, ticker, name, listcorp_url
            FROM companies
            WHERE ticker = ?
        """, (ticker.upper(),))
    elif skip_existing:
        # Skip companies that already have documents
        cursor.execute("""
            SELECT c.id, c.ticker, c.name, c.listcorp_url
            FROM companies c
            LEFT JOIN documents d ON c.id = d.company_id
            WHERE d.id IS NULL
            ORDER BY c.ticker
        """ + (f" LIMIT {limit}" if limit else ""))
    else:
        # Get all companies (or limited number)
        query = "SELECT id, ticker, name, listcorp_url FROM companies ORDER BY ticker"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)

    companies = cursor.fetchall()
    conn.close()

    return companies


def save_documents(company_id, documents):
    """
    Save found documents to the database.

    Args:
        company_id: Database ID of the company
        documents: List of document dictionaries from scraper

    Returns:
        Number of documents successfully inserted
    """
    if not documents:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    for doc in documents:
        try:
            cursor.execute("""
                INSERT INTO documents (
                    company_id, title, document_type, financial_year,
                    publication_date, listcorp_news_url, extraction_status
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (
                company_id,
                doc['title'],
                doc['document_type'],
                doc['financial_year'],
                doc['publication_date'],
                doc['listcorp_news_url']
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate document (same company_id + listcorp_news_url)
            pass
        except Exception as e:
            print(f"      Error inserting document: {e}")

    conn.commit()
    conn.close()

    return inserted


def main():
    """Main function to find ESG documents for companies."""
    parser = argparse.ArgumentParser(description='Find ESG documents on ListCorp')
    parser.add_argument('--limit', type=int, help='Process only N companies')
    parser.add_argument('--ticker', type=str, help='Process only this ticker (e.g., XRO)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip companies that already have documents')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')

    args = parser.parse_args()

    print("=" * 70)
    print("ESG Intelligence - Find ESG Documents on ListCorp")
    print("=" * 70)
    print()

    # Get companies to process
    companies = get_companies_to_process(
        limit=args.limit,
        ticker=args.ticker,
        skip_existing=args.skip_existing
    )

    if not companies:
        print("No companies to process!")
        if args.ticker:
            print(f"Ticker '{args.ticker}' not found in database.")
        return

    total = len(companies)
    print(f"Processing {total} companies...")
    print()

    # Track statistics
    total_docs_found = 0
    companies_with_docs = 0
    companies_no_docs = 0
    errors = 0

    # Process each company
    for i, (company_id, ticker, name, listcorp_url) in enumerate(companies, 1):
        # Extract company slug from URL
        if not listcorp_url:
            print(f"[{i}/{total}] {ticker:6} - {name:40} - ⚠ No ListCorp URL")
            errors += 1
            continue

        slug = extract_company_slug_from_url(listcorp_url)
        if not slug:
            print(f"[{i}/{total}] {ticker:6} - {name:40} - ⚠ Cannot extract slug from URL")
            errors += 1
            continue

        # Find ESG documents
        try:
            documents = find_esg_documents(ticker, slug, verbose=args.verbose)

            # Save to database
            inserted = save_documents(company_id, documents)

            if inserted > 0:
                companies_with_docs += 1
                total_docs_found += inserted
                print(f"[{i}/{total}] {ticker:6} - {name:40} - ✓ Found {inserted} documents")

                # Show document details
                if args.verbose and documents:
                    for doc in documents[:3]:  # Show first 3
                        print(f"          • {doc['title']} ({doc['financial_year'] or 'N/A'})")
                    if len(documents) > 3:
                        print(f"          ... and {len(documents) - 3} more")
            else:
                companies_no_docs += 1
                print(f"[{i}/{total}] {ticker:6} - {name:40} - ○ No ESG docs")

        except Exception as e:
            errors += 1
            print(f"[{i}/{total}] {ticker:6} - {name:40} - ✗ Error: {e}")

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Companies processed:       {total}")
    print(f"Companies with docs:       {companies_with_docs}")
    print(f"Companies without docs:    {companies_no_docs}")
    print(f"Errors:                    {errors}")
    print(f"Total documents found:     {total_docs_found}")
    print()

    if total_docs_found > 0:
        print("✓ Documents saved to database!")
        print()
        print("Next steps:")
        print("  1. Check documents: sqlite3 data/esg_intel.db \"SELECT COUNT(*) FROM documents;\"")
        print("  2. Extract text: python scripts/03_extract_text.py")
    else:
        print("No documents found. This might mean:")
        print("  1. Companies don't have ESG reports on ListCorp")
        print("  2. The HTML structure doesn't match our scraper")
        print("  3. Try running with --verbose to see details")


if __name__ == "__main__":
    main()
