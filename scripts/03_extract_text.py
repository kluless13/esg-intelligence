"""
Extract text from ESG documents using Docling.

This script processes documents from the database and extracts their text content
using IBM's Docling library (97.9% table accuracy on sustainability reports!).

Usage:
    python scripts/03_extract_text.py               # Process all pending documents
    python scripts/03_extract_text.py --limit 5     # Process 5 documents
    python scripts/03_extract_text.py --company XRO # Process one company's docs
    python scripts/03_extract_text.py --reprocess   # Reprocess failed documents
"""

import sys
import sqlite3
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH
from src.scraper.text_extractor import extract_document_text


def get_documents_to_process(limit=None, company_ticker=None, reprocess=False, skip_existing=True):
    """
    Get list of documents to process from database.

    Args:
        limit: Maximum number of documents to process
        company_ticker: Process only this company's documents
        reprocess: Reprocess failed documents
        skip_existing: Skip documents that already have text

    Returns:
        List of (doc_id, company_id, ticker, title, url) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    conditions = []
    params = []

    if company_ticker:
        conditions.append("c.ticker = ?")
        params.append(company_ticker.upper())

    if skip_existing and not reprocess:
        conditions.append("(d.extraction_status = 'pending' OR d.extraction_status IS NULL)")
    elif reprocess:
        conditions.append("d.extraction_status IN ('failed', 'partial')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT d.id, d.company_id, c.ticker, d.title, d.listcorp_news_url
        FROM documents d
        JOIN companies c ON d.company_id = c.id
        WHERE {where_clause}
        ORDER BY c.ticker, d.financial_year DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query, params)
    documents = cursor.fetchall()
    conn.close()

    return documents


def update_document(doc_id, result):
    """
    Update document in database with extraction results.

    Args:
        doc_id: Document ID
        result: Dict from extract_document_text()
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE documents
        SET text_content = ?,
            extraction_status = ?,
            extraction_method = ?,
            char_count = ?,
            table_count = ?
        WHERE id = ?
    """, (
        result.get('text_content'),
        result.get('extraction_status'),
        result.get('extraction_method'),
        result.get('char_count', 0),
        result.get('table_count', 0),
        doc_id
    ))

    conn.commit()
    conn.close()


def main():
    """Main function to extract text from documents."""
    parser = argparse.ArgumentParser(description='Extract text from ESG documents')
    parser.add_argument('--limit', type=int, help='Process only N documents')
    parser.add_argument('--company', type=str, help='Process only this company ticker')
    parser.add_argument('--reprocess', action='store_true',
                        help='Reprocess failed/partial documents')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip documents with existing text (default: True)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')

    args = parser.parse_args()

    print("=" * 80)
    print("ESG Intelligence - Extract Document Text with Docling")
    print("=" * 80)
    print()

    # Get documents to process
    documents = get_documents_to_process(
        limit=args.limit,
        company_ticker=args.company,
        reprocess=args.reprocess,
        skip_existing=args.skip_existing
    )

    if not documents:
        print("No documents to process!")
        if args.company:
            print(f"Company '{args.company}' not found or all documents already processed.")
        else:
            print("All documents have been processed. Use --reprocess to retry failed ones.")
        return

    total = len(documents)
    print(f"Processing {total} documents...")
    print()
    print("NOTE: First run will download Docling AI models (~1-2GB).")
    print("      This is a one-time setup and may take a few minutes.")
    print()

    # Track statistics
    success_count = 0
    partial_count = 0
    failed_count = 0
    total_chars = 0
    total_tables = 0

    # Process each document
    for i, (doc_id, company_id, ticker, title, url) in enumerate(documents, 1):
        print(f"[{i}/{total}] {ticker:6} - {title[:50]}")

        try:
            # Extract text
            result = extract_document_text(url, prefer_docling=True)

            # Update database
            update_document(doc_id, result)

            # Display results
            status = result['extraction_status']
            method = result['extraction_method']
            chars = result.get('char_count', 0)
            tables = result.get('table_count', 0)

            if status == 'success':
                success_count += 1
                total_chars += chars
                total_tables += tables
                print(f"         ✓ {chars:,} chars, {tables} tables ({method})")
            elif status == 'partial':
                partial_count += 1
                total_chars += chars
                print(f"         ⚠ {chars:,} chars ({method}) - {result.get('error', 'partial')}")
            else:
                failed_count += 1
                print(f"         ✗ Failed ({method}) - {result.get('error', 'unknown error')}")

            if args.verbose and result.get('text_content'):
                preview = result['text_content'][:200].replace('\n', ' ')
                print(f"         Preview: {preview}...")

        except Exception as e:
            failed_count += 1
            print(f"         ✗ Exception: {e}")
            # Mark as failed in database
            update_document(doc_id, {
                'text_content': None,
                'extraction_status': 'failed',
                'extraction_method': 'exception',
                'char_count': 0,
                'table_count': 0,
                'error': str(e)
            })

    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Documents processed:       {total}")
    print(f"Successful extractions:    {success_count}")
    print(f"Partial extractions:       {partial_count}")
    print(f"Failed extractions:        {failed_count}")
    print(f"Total characters extracted: {total_chars:,}")
    print(f"Total tables found:        {total_tables}")
    print()

    if success_count > 0:
        avg_chars = total_chars / success_count
        print(f"Average chars per document: {avg_chars:,.0f}")
        print()
        print("✓ Text extraction completed!")
        print()
        print("Next steps:")
        print("  1. Check extraction status:")
        print("     sqlite3 data/esg_intel.db \"SELECT extraction_status, COUNT(*) FROM documents GROUP BY extraction_status;\"")
        print()
        print("  2. View sample extracted text:")
        print("     sqlite3 data/esg_intel.db \"SELECT ticker, title, char_count, table_count FROM documents d JOIN companies c ON d.company_id = c.id WHERE extraction_status = 'success' LIMIT 5;\"")
        print()
        print("  3. Move to Milestone 4: AI-powered ESG data extraction")
        print("     python scripts/04_analyze_with_ai.py --dry-run --limit 5")
    else:
        print("⚠ No successful extractions. Check the errors above.")
        print()
        print("Troubleshooting:")
        print("  1. Verify Docling is installed: python -c \"from docling.document_converter import DocumentConverter\"")
        print("  2. Test with a single document: python scripts/03_extract_text.py --limit 1 --verbose")
        print("  3. Try the test script: python src/scraper/text_extractor.py")


if __name__ == "__main__":
    main()
