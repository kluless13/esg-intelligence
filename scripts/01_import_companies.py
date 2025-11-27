"""
Import companies from CSV file into the database.

This script reads the companies CSV file (from klu13's existing esgWIKI project)
and imports all ASX companies into the companies table.
"""
import sys
import csv
import sqlite3
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH, COMPANIES_CSV
from src.database.schema import init_database


def extract_ticker(code):
    """
    Extract ticker from code column (e.g., 'ASX:CBA' -> 'CBA')
    """
    if ':' in code:
        return code.split(':')[1].strip()
    return code.strip()


def clean_company_name(company_str):
    """
    Clean company name by removing the ticker in parentheses
    e.g., 'Commonwealth Bank (ASX:CBA)' -> 'Commonwealth Bank'
    """
    if '(' in company_str:
        return company_str.split('(')[0].strip()
    return company_str.strip()


def import_companies():
    """
    Import companies from CSV into the database.
    Handles duplicates gracefully by skipping them.
    """
    print("=" * 60)
    print("ESG Intelligence - Company Import")
    print("=" * 60)
    print()

    # Initialize database (creates tables if they don't exist)
    print("Step 1: Initializing database...")
    init_database()
    print()

    # Check if CSV file exists
    if not COMPANIES_CSV.exists():
        print(f"❌ Error: CSV file not found at {COMPANIES_CSV}")
        print("Please ensure the companies CSV file is in the data/ directory")
        return

    print(f"Step 2: Reading CSV from {COMPANIES_CSV}...")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Read CSV and import companies
    imported = 0
    skipped = 0
    errors = 0

    with open(COMPANIES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Extract data from CSV columns
                code = row['Code']
                ticker = extract_ticker(code)
                name = clean_company_name(row['Company'])
                listcorp_url = row['Link']
                sector = row['Sector']

                # Insert into database (ignore if already exists)
                try:
                    cursor.execute("""
                        INSERT INTO companies (ticker, name, sector, listcorp_url)
                        VALUES (?, ?, ?, ?)
                    """, (ticker, name, sector, listcorp_url))
                    imported += 1

                except sqlite3.IntegrityError:
                    # Duplicate ticker - skip it
                    skipped += 1

            except Exception as e:
                errors += 1
                print(f"⚠ Error processing row: {e}")
                continue

    # Commit changes
    conn.commit()

    print()
    print("=" * 60)
    print("Import Summary")
    print("=" * 60)
    print(f"✓ Successfully imported: {imported} companies")
    if skipped > 0:
        print(f"⊘ Skipped (duplicates):  {skipped} companies")
    if errors > 0:
        print(f"✗ Errors:                {errors} rows")
    print()

    # Show some sample companies
    print("Sample of imported companies:")
    print("-" * 60)
    cursor.execute("""
        SELECT ticker, name, sector
        FROM companies
        ORDER BY ticker
        LIMIT 5
    """)
    for ticker, name, sector in cursor.fetchall():
        print(f"  {ticker:6} - {name:40} [{sector}]")

    print()

    # Show total count
    cursor.execute("SELECT COUNT(*) FROM companies")
    total = cursor.fetchone()[0]
    print(f"Total companies in database: {total}")
    print()

    conn.close()

    print("✓ Import complete!")
    print()


if __name__ == "__main__":
    import_companies()
