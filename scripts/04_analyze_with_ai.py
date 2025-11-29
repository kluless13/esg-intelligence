"""
AI-powered ESG data extraction using Claude API.

This script processes documents with extracted text and uses Claude to extract
structured ESG metrics (emissions, renewable energy targets, commitments, etc.)

Usage:
    python scripts/04_analyze_with_ai.py --dry-run --limit 5  # Preview and cost estimate
    python scripts/04_analyze_with_ai.py --company XRO        # Process one company
    python scripts/04_analyze_with_ai.py --limit 10           # Process 10 companies
    python scripts/04_analyze_with_ai.py                      # Process all
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH
from src.analyzer.llm_extractor import extract_esg_data, estimate_cost


def get_documents_to_analyze(limit=None, company_ticker=None):
    """
    Get documents with extracted text that haven't been analyzed yet.

    Args:
        limit: Maximum number of companies to process
        company_ticker: Process only this company

    Returns:
        List of (doc_id, company_id, company_name, ticker, title, financial_year,
                 document_type, text_content, char_count) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    conditions = [
        "d.extraction_status = 'success'",
        "d.text_content IS NOT NULL",
        "d.text_content != ''",
        # Only process docs that haven't been analyzed yet
        """NOT EXISTS (
            SELECT 1 FROM esg_data e
            WHERE e.document_id = d.id
        )"""
    ]

    if company_ticker:
        conditions.append(f"c.ticker = '{company_ticker.upper()}'")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            d.id,
            d.company_id,
            c.name,
            c.ticker,
            d.title,
            d.financial_year,
            d.document_type,
            d.text_content,
            d.char_count
        FROM documents d
        JOIN companies c ON d.company_id = c.id
        WHERE {where_clause}
        ORDER BY c.ticker, d.financial_year DESC
    """

    if limit:
        # Get first N companies, then get all their documents
        company_query = f"""
            SELECT DISTINCT company_id
            FROM documents d
            JOIN companies c ON d.company_id = c.id
            WHERE {where_clause}
            LIMIT {limit}
        """
        cursor.execute(company_query)
        company_ids = [row[0] for row in cursor.fetchall()]

        if not company_ids:
            conn.close()
            return []

        company_ids_str = ','.join(str(cid) for cid in company_ids)
        query = f"""
            SELECT
                d.id,
                d.company_id,
                c.name,
                c.ticker,
                d.title,
                d.financial_year,
                d.document_type,
                d.text_content,
                d.char_count
            FROM documents d
            JOIN companies c ON d.company_id = c.id
            WHERE {where_clause}
              AND d.company_id IN ({company_ids_str})
            ORDER BY c.ticker, d.financial_year DESC
        """

    cursor.execute(query)
    documents = cursor.fetchall()
    conn.close()

    return documents


def insert_esg_data(doc_id: int, company_id: int, extracted_data: dict, raw_response: str):
    """
    Insert extracted ESG data into database.

    Args:
        doc_id: Document ID
        company_id: Company ID
        extracted_data: Extracted ESG metrics dict
        raw_response: Raw LLM response for debugging
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Convert boolean values to integers for SQLite
    def to_int(val):
        if val is None:
            return None
        if isinstance(val, bool):
            return 1 if val else 0
        return val

    cursor.execute("""
        INSERT INTO esg_data (
            company_id,
            document_id,
            data_year,
            scope1_emissions,
            scope2_emissions,
            scope3_emissions,
            total_emissions,
            emissions_baseline_year,
            net_zero_target_year,
            emissions_reduction_target_pct,
            emissions_reduction_target_year,
            renewable_energy_pct_current,
            renewable_energy_target_pct,
            renewable_energy_target_year,
            energy_consumption_mwh,
            sbti_status,
            re100_member,
            tcfd_aligned,
            climate_active_certified,
            has_ppa,
            ppa_details,
            renewable_procurement_mentioned,
            confidence_score,
            extraction_notes,
            raw_llm_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        doc_id,
        extracted_data.get('data_year'),
        extracted_data.get('scope1_emissions'),
        extracted_data.get('scope2_emissions'),
        extracted_data.get('scope3_emissions'),
        extracted_data.get('total_emissions'),
        extracted_data.get('emissions_baseline_year'),
        extracted_data.get('net_zero_target_year'),
        extracted_data.get('emissions_reduction_target_pct'),
        extracted_data.get('emissions_reduction_target_year'),
        extracted_data.get('renewable_energy_pct_current'),
        extracted_data.get('renewable_energy_target_pct'),
        extracted_data.get('renewable_energy_target_year'),
        extracted_data.get('energy_consumption_mwh'),
        extracted_data.get('sbti_status'),
        to_int(extracted_data.get('re100_member')),
        to_int(extracted_data.get('tcfd_aligned')),
        to_int(extracted_data.get('climate_active_certified')),
        to_int(extracted_data.get('has_ppa')),
        extracted_data.get('ppa_details'),
        to_int(extracted_data.get('renewable_procurement_mentioned')),
        extracted_data.get('confidence_score'),
        extracted_data.get('extraction_notes'),
        raw_response
    ))

    conn.commit()
    conn.close()


def format_metric(value, unit=""):
    """Format a metric value for display."""
    if value is None:
        return "Not found"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        if unit:
            return f"{value:,}{unit}"
        return f"{value:,}"
    return str(value)


def main():
    """Main function to analyze documents with AI."""
    parser = argparse.ArgumentParser(description='Extract ESG data using Claude AI')
    parser.add_argument('--limit', type=int, help='Process only N companies')
    parser.add_argument('--company', type=str, help='Process only this company ticker')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be processed and estimate cost')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed extraction results')

    args = parser.parse_args()

    print("=" * 80)
    print("ESG Intelligence - AI-Powered Data Extraction")
    print("=" * 80)
    print()

    # Get documents to analyze
    documents = get_documents_to_analyze(
        limit=args.limit,
        company_ticker=args.company
    )

    if not documents:
        print("No documents to process!")
        if args.company:
            print(f"Company '{args.company}' has no unanalyzed documents with extracted text.")
        else:
            print("All documents have been analyzed or have no extracted text.")
        return

    # Count unique companies
    unique_companies = len(set(doc[1] for doc in documents))
    total_docs = len(documents)
    avg_chars = sum(doc[8] for doc in documents) / total_docs if total_docs > 0 else 0

    print(f"Found {total_docs} document(s) from {unique_companies} company/companies")
    print()

    # Estimate cost
    cost_estimate = estimate_cost(total_docs, int(avg_chars))

    print("Cost Estimate:")
    print(f"  Estimated input tokens:  {cost_estimate['estimated_input_tokens']:,}")
    print(f"  Estimated output tokens: {cost_estimate['estimated_output_tokens']:,}")
    print(f"  Estimated total tokens:  {cost_estimate['estimated_total_tokens']:,}")
    print(f"  Estimated cost:          ${cost_estimate['estimated_cost_usd']:.3f}")
    print()

    if args.dry_run:
        print("DRY RUN - Documents that would be processed:")
        print()
        current_company = None
        for doc in documents:
            ticker = doc[3]
            company_name = doc[2]
            title = doc[4]
            fy = doc[5] or "Unknown FY"
            char_count = doc[8]

            if ticker != current_company:
                print(f"\n{ticker} - {company_name}")
                current_company = ticker

            print(f"  • {title[:60]}")
            print(f"    FY: {fy}, {char_count:,} chars")
        print()
        print("Run without --dry-run to process these documents.")
        return

    # Process documents
    print(f"Processing {total_docs} documents...")
    print()

    success_count = 0
    failed_count = 0
    total_tokens = {"input": 0, "output": 0}

    current_company = None
    doc_num = 0

    for doc in documents:
        doc_id, company_id, company_name, ticker, title, fy, doc_type, text_content, char_count = doc
        doc_num += 1

        # Print company header
        if ticker != current_company:
            if current_company is not None:
                print()
            print(f"[{ticker}] {company_name}")
            current_company = ticker

        print(f"  [{doc_num}/{total_docs}] {title[:50]}")
        print(f"       FY: {fy or 'Unknown'}, {char_count:,} chars")

        # Extract ESG data
        result = extract_esg_data(
            company_name=company_name,
            financial_year=fy or "Unknown",
            document_type=doc_type or "report",
            document_text=text_content
        )

        if not result['success']:
            failed_count += 1
            print(f"       ✗ Failed: {result['error']}")
            continue

        # Insert into database
        try:
            insert_esg_data(
                doc_id=doc_id,
                company_id=company_id,
                extracted_data=result['extracted_data'],
                raw_response=result['raw_response']
            )

            success_count += 1
            total_tokens['input'] += result['tokens_used']['input']
            total_tokens['output'] += result['tokens_used']['output']

            # Display key metrics
            data = result['extracted_data']
            print(f"       ✓ Extracted (confidence: {data.get('confidence_score', 0):.2f})")

            # Show interesting findings
            findings = []
            if data.get('scope1_emissions') or data.get('scope2_emissions'):
                s1 = data.get('scope1_emissions') or 0
                s2 = data.get('scope2_emissions') or 0
                findings.append(f"Scope 1+2: {s1+s2:,.0f} tCO2e")

            if data.get('net_zero_target_year'):
                findings.append(f"Net zero: {data['net_zero_target_year']}")

            if data.get('renewable_energy_pct_current'):
                findings.append(f"RE: {data['renewable_energy_pct_current']:.0f}%")

            if data.get('renewable_energy_target_pct'):
                target_pct = data['renewable_energy_target_pct']
                target_year = data.get('renewable_energy_target_year', '?')
                findings.append(f"RE target: {target_pct:.0f}% by {target_year}")

            if data.get('sbti_status') and data['sbti_status'] != 'none':
                findings.append(f"SBTi: {data['sbti_status']}")

            if data.get('has_ppa'):
                findings.append("Has PPA")

            if findings:
                print(f"         {', '.join(findings)}")

            if args.verbose and data.get('extraction_notes'):
                print(f"         Notes: {data['extraction_notes']}")

        except Exception as e:
            failed_count += 1
            print(f"       ✗ Database error: {e}")

    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Documents processed:       {total_docs}")
    print(f"Successful extractions:    {success_count}")
    print(f"Failed extractions:        {failed_count}")
    print(f"Total tokens used:         {total_tokens['input'] + total_tokens['output']:,}")
    print(f"  - Input tokens:          {total_tokens['input']:,}")
    print(f"  - Output tokens:         {total_tokens['output']:,}")

    if total_tokens['input'] > 0:
        actual_cost = (total_tokens['input'] / 1_000_000 * 3.0) + \
                      (total_tokens['output'] / 1_000_000 * 15.0)
        print(f"Actual cost:               ${actual_cost:.3f}")
    print()

    if success_count > 0:
        print("✓ ESG data extraction completed!")
        print()
        print("Next steps:")
        print("  1. View extracted data:")
        print("     sqlite3 data/esg_intel.db \"SELECT * FROM esg_data LIMIT 5;\"")
        print()
        print("  2. Check what data was found:")
        print("     sqlite3 data/esg_intel.db \"SELECT c.ticker, e.data_year, e.total_emissions, e.net_zero_target_year FROM esg_data e JOIN companies c ON e.company_id = c.id;\"")
        print()
        print("  3. Move to Milestone 5: Calculate prospect scores")
        print("     python scripts/05_calculate_scores.py")
    else:
        print("⚠ No successful extractions.")
        print()
        print("Troubleshooting:")
        print("  1. Check your .env file has a valid ANTHROPIC_API_KEY")
        print("  2. Verify API key at: https://console.anthropic.com/")
        print("  3. Check the error messages above")


if __name__ == "__main__":
    main()
