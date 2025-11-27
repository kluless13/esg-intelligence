# ESG Intelligence Platform

Extract ESG/sustainability data from ListCorp.com for ASX companies, analyze with AI, and identify high-priority renewable energy sales prospects.

## Project Status

### ✅ Milestone 1: Project Setup & Company Import - COMPLETE

- [x] Project structure created
- [x] Database initialized with schema
- [x] 2,239 ASX companies imported from CSV
- [x] Database queries working

### 🔄 Next Steps

- **Milestone 2**: Find ESG documents on ListCorp news pages
- **Milestone 3**: Extract text from documents
- **Milestone 4**: AI-powered data extraction with Claude
- **Milestone 5**: Prospect scoring algorithm
- **Milestone 6**: Streamlit dashboard

## Quick Start

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run Milestone 1

```bash
# Import companies (already completed, but can re-run)
python scripts/01_import_companies.py
```

### Verify Database

```bash
# Check total companies
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM companies;"

# View sample companies
sqlite3 data/esg_intel.db "SELECT ticker, name, sector FROM companies LIMIT 10;"

# Find specific companies
sqlite3 data/esg_intel.db "SELECT * FROM companies WHERE ticker IN ('BHP', 'XRO', 'WOW');"
```

## Project Structure

```
esg-intelligence/
├── config/
│   └── settings.py           # Configuration settings
├── data/
│   ├── companies.csv         # Source CSV (2,239 ASX companies)
│   └── esg_intel.db          # SQLite database
├── src/
│   ├── database/
│   │   └── schema.py         # Database initialization
│   ├── scraper/              # (Milestone 2+)
│   ├── analyzer/             # (Milestone 4+)
│   └── utils/
├── scripts/
│   └── 01_import_companies.py
└── app/                      # (Milestone 6)
```

## Technology Stack

- **Language**: Python 3.11+
- **Database**: SQLite
- **Web Scraping**: requests + BeautifulSoup4
- **AI Analysis**: Claude API (Anthropic)
- **Dashboard**: Streamlit (coming in Milestone 6)

## Database Schema

The database has 4 main tables:

1. **companies** - All ASX companies (2,239 imported)
2. **documents** - ESG documents found on ListCorp
3. **esg_data** - AI-extracted ESG metrics
4. **prospect_scores** - Calculated sales prospect scores

See `blueprint.md` for complete schema details.

## Resources

- Full specification: `blueprint.md`
- Source CSV: `data/companies.csv`
- Database: `data/esg_intel.db`

## Notes

- The CSV file came from the previous esgWIKI project
- Focus is on staying within ListCorp (not scraping individual company websites)
- Multi-year coverage (FY2021-2025) to track progress over time
