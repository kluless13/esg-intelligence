"""
Database schema initialization for ESG Intelligence Platform
"""
import sqlite3
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import DB_PATH


def init_database():
    """
    Initialize the SQLite database with all required tables and indexes.
    Safe to run multiple times - won't drop existing data.
    """
    print(f"Initializing database at: {DB_PATH}")

    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Companies table: All ASX companies (imported from CSV)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            sector TEXT,
            listcorp_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ESG Documents found on ListCorp
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            document_type TEXT,
            financial_year TEXT,
            publication_date DATE,
            listcorp_news_url TEXT NOT NULL,
            pdf_url TEXT,
            has_embedded_text INTEGER DEFAULT 0,
            text_content TEXT,
            extraction_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            UNIQUE(company_id, listcorp_news_url)
        )
    """)

    # AI-extracted ESG data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS esg_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            document_id INTEGER,
            data_year INTEGER,

            scope1_emissions REAL,
            scope2_emissions REAL,
            scope3_emissions REAL,
            total_emissions REAL,
            emissions_baseline_year INTEGER,

            net_zero_target_year INTEGER,
            emissions_reduction_target_pct REAL,
            emissions_reduction_target_year INTEGER,

            renewable_energy_pct_current REAL,
            renewable_energy_target_pct REAL,
            renewable_energy_target_year INTEGER,
            energy_consumption_mwh REAL,

            sbti_status TEXT,
            re100_member INTEGER,
            tcfd_aligned INTEGER,
            climate_active_certified INTEGER,

            has_ppa INTEGER,
            ppa_details TEXT,
            renewable_procurement_mentioned INTEGER,

            confidence_score REAL,
            extraction_notes TEXT,
            raw_llm_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)

    # Calculated prospect scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prospect_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,

            renewable_gap_score REAL,
            timeline_urgency_score REAL,
            energy_volume_score REAL,
            procurement_intent_score REAL,
            company_size_score REAL,
            esg_maturity_score REAL,
            data_quality_score REAL,

            total_score REAL,
            priority_tier TEXT,

            key_opportunities TEXT,
            years_of_data INTEGER,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_company ON documents(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_fy ON documents(financial_year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_esg_data_company ON esg_data(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prospect_scores_total ON prospect_scores(total_score DESC)")

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print("✓ Database initialized successfully!")
    print(f"✓ Location: {DB_PATH}")
    return DB_PATH


if __name__ == "__main__":
    # Allow running this script directly to initialize the database
    init_database()
