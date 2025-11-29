# ESG Intelligence Platform

AI-powered system to discover, extract, and analyze ESG/sustainability data from public companies worldwide. Identifies high-priority renewable energy sales prospects using Claude AI.

## Project Status

### ✅ Milestone 1: Project Setup & Company Import - COMPLETE

- [x] Project structure created
- [x] Database initialized with schema
- [x] 2,239 ASX companies imported from CSV
- [x] Database queries working

### ✅ Milestone 2: Find ESG Documents - COMPLETE

- [x] ListCorp scraper with Playwright + stealth mode
- [x] ESG document detection (sustainability reports, annual reports)
- [x] Documents saved to database

### ✅ Milestone 3: Extract Text from Documents - COMPLETE

- [x] Docling integration (IBM's AI-powered extraction)
- [x] 97.9% table accuracy on sustainability reports!
- [x] Fallback to BeautifulSoup/PyMuPDF
- [x] 27 documents successfully extracted (96.4% success rate)
- [x] Average document length: ~25k characters

### ✅ Milestone 4: AI-Powered ESG Data Extraction - COMPLETE

- [x] Claude API integration for structured data extraction
- [x] 27 documents analyzed from 6 companies
- [x] Extracted emissions, targets, renewable energy, commitments
- [x] Total cost: ~$0.78 for all documents
- [x] Found meaningful ESG data (XRO: net-zero by 2050, SBTi targets set)

### 📋 Next Steps

- **Milestone 5**: Prospect scoring algorithm
- **Milestone 6**: Streamlit dashboard

---

## 🚨 Critical Limitation & Improved Data Sourcing Strategy

### Current Limitation

**The current approach (scraping ListCorp news pages) has major limitations:**

❌ **Only finds ~25% of sustainability reports**
- Most companies publish sustainability reports on their own websites, NOT as stock exchange announcements
- ListCorp is ASX-only (can't scale to NASDAQ, NYSE, LSE, etc.)
- Many ESG reports are standalone PDFs, not embedded in news announcements

**Evidence from our data:**
- 6 companies scraped → Only 2 have meaningful ESG data (33%)
- XRO mentions "Climate Appendix on website" - not in ListCorp
- Small companies (biotech/pharma) don't file sustainability reports to ASX

### ✅ Improved Strategy: Search Engine Discovery

**New architecture for global scalability:**

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Get Company List (Exchange-Agnostic)           │
├─────────────────────────────────────────────────────────┤
│ • ASX: ListCorp company list (existing)                │
│ • NASDAQ/NYSE: SEC Edgar API, Yahoo Finance            │
│ • LSE: London Stock Exchange API                       │
│ • Any exchange: Wikipedia lists, OpenCorporates        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Search Engine Discovery (NEW!)                 │
├─────────────────────────────────────────────────────────┤
│ For each company, run targeted searches:               │
│                                                         │
│ Google/Bing queries:                                   │
│ • "sustainability report [company] 2024 filetype:pdf"  │
│ • "[company] ESG report 2024"                          │
│ • "[company] climate disclosure TCFD"                  │
│ • "[company] annual report 2024 environment"           │
│ • "site:[company-domain] sustainability"               │
│                                                         │
│ Parse search results → Extract PDF/HTML URLs           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Document Download & Extraction                 │
├─────────────────────────────────────────────────────────┤
│ • Download PDF/HTML documents                          │
│ • Extract text with Docling (WORKING GREAT! ✓)        │
│ • Store in documents table                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: AI Analysis & Scoring                          │
├─────────────────────────────────────────────────────────┤
│ • Claude extracts ESG metrics (WORKING GREAT! ✓)      │
│ • Calculate prospect scores                            │
│ • Generate insights                                    │
└─────────────────────────────────────────────────────────┘
```

### Implementation Plan

#### Phase 1: Search Engine Integration (Priority)

Create `scripts/02b_find_via_search.py`:

```python
"""
Find sustainability reports using search engines.
Much more effective than relying on stock exchange announcements.
"""

def search_for_reports(company_name, ticker, year=2024):
    """
    Use Google/Bing to find sustainability reports.

    Search queries:
    1. "sustainability report {company_name} {year} filetype:pdf"
    2. "{company_name} ESG report {year}"
    3. "{ticker} climate disclosure TCFD {year}"
    4. "{company_name} annual report {year} environment"
    5. "site:{company_domain} sustainability OR ESG"

    Returns:
        List of (url, title, source) tuples
    """
    pass

# Libraries to use:
# - googlesearch-python (simple Google search)
# - SerpAPI (professional, paid, more reliable)
# - Bing Search API (Microsoft, paid)
# - DuckDuckGo (free, no API key needed)
```

**Advantages:**
✅ Works for ANY stock exchange globally
✅ Finds reports on company websites (where they usually are)
✅ Can target specific document types (PDF, HTML)
✅ More comprehensive coverage

**Challenges:**
⚠️ Rate limits (need to throttle requests)
⚠️ Some search APIs cost money (SerpAPI ~$50/month)
⚠️ Need to filter out irrelevant results

#### Phase 2: Multi-Exchange Company Lists

Update `scripts/01_import_companies.py` to support multiple exchanges:

```python
def get_nasdaq_companies():
    """Get NASDAQ company list from SEC Edgar or nasdaq.com"""
    pass

def get_nyse_companies():
    """Get NYSE company list"""
    pass

def get_lse_companies():
    """Get London Stock Exchange companies"""
    pass

# Database schema update:
# Add 'exchange' column to companies table
# ALTER TABLE companies ADD COLUMN exchange TEXT DEFAULT 'ASX';
```

#### Phase 3: Company Website Discovery

Many companies have predictable URL patterns:

```python
def guess_company_domain(company_name, ticker):
    """
    Try to find company's official website.

    Common patterns:
    - {ticker.lower()}.com
    - {company-name-slugified}.com
    - www.{ticker}.com.au (ASX)

    Verification:
    - Check if domain exists (DNS lookup)
    - Verify it's the right company (look for ticker/name on page)
    """
    pass
```

Then search directly on their site:
```
site:xero.com sustainability report
site:bhp.com climate disclosure
```

### Recommended Tools & APIs

| Tool | Cost | Purpose | Notes |
|------|------|---------|-------|
| **SerpAPI** | $50/mo | Google search API | Most reliable, handles captchas |
| **DuckDuckGo** | Free | Search without API key | Good for prototyping |
| **googlesearch-python** | Free | Unofficial Google scraping | May get blocked |
| **Bing Search API** | Pay-per-use | Microsoft's search | Good alternative to Google |
| **SEC Edgar API** | Free | US company filings | NASDAQ/NYSE companies |
| **OpenCorporates API** | Free tier | Global company data | Company domain lookup |

### Search Query Templates

For best results, use these search patterns:

```python
SEARCH_QUERIES = {
    "sustainability_pdf": '"{company}" sustainability report {year} filetype:pdf',
    "esg_report": '"{company}" ESG report {year}',
    "climate_disclosure": '"{ticker}" climate disclosure TCFD {year}',
    "annual_report_env": '"{company}" annual report {year} environment emissions',
    "company_site": 'site:{domain} (sustainability OR ESG OR climate OR "net zero")',
    "cdp_disclosure": '"{company}" CDP climate change {year}',
    "gri_report": '"{company}" GRI sustainability {year}',
}

# Year variations (try multiple years if current year not found)
YEARS_TO_TRY = [2024, 2023, 2022, 2021]
```

### Modified Pipeline Flow

**OLD (ListCorp only):**
```
Companies → ListCorp news → Extract text → Analyze
          ↓
      Limited to ASX, low success rate
```

**NEW (Search-based):**
```
Companies → Search engines → Download docs → Extract text → Analyze
          ↓                 ↓
      Any exchange    High success rate (find reports wherever they are)
```

### Success Metrics Target

With search-based discovery, we should achieve:

| Metric | Current (ListCorp) | Target (Search) |
|--------|-------------------|-----------------|
| Document discovery rate | 25-30% | **80-90%** |
| Companies with ESG data | 2 out of 6 (33%) | **70%+** |
| Supported exchanges | ASX only | **Global** |
| Documents per company | 1-5 | **5-10** (multi-year) |

---

## 🤖 Claude Code Prompts

Copy-paste these prompts to Claude Code to continue development.

### Install New Dependencies

```
Install the new requirements including Docling. Run:
pip install -r requirements.txt

Then verify Docling is installed:
python -c "from docling.document_converter import DocumentConverter; print('Docling OK')"
```

### Run Milestone 3: Extract Text (Test)

```
Run the text extraction script on 5 documents to test:
python scripts/03_extract_text.py --limit 5

The first run will download Docling's AI models (~1-2GB). This is normal and only happens once.

Show me the results and any errors.
```

### Run Milestone 3: Extract Text (Full)

```
Run text extraction on all documents that haven't been processed yet:
python scripts/03_extract_text.py --skip-existing

This may take a while. Show me progress and the final summary.
```

### Check Extraction Status

```
Show me the extraction status of documents in the database:
sqlite3 data/esg_intel.db "SELECT extraction_status, COUNT(*), SUM(char_count) as total_chars FROM documents GROUP BY extraction_status;"

Also show me 5 example extracted documents:
sqlite3 data/esg_intel.db "SELECT c.ticker, d.title, d.char_count, d.table_count, d.extraction_method FROM documents d JOIN companies c ON d.company_id = c.id WHERE d.extraction_status = 'success' LIMIT 5;"
```

### Find More ESG Documents

```
Find ESG documents for more companies (run this in background if needed):
python scripts/02_find_esg_docs.py --limit 200 --skip-existing

Show me how many documents we have now:
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM documents;"
```

### Build Milestone 4: AI Data Extraction

```
I'm ready for Milestone 4. Create the AI-powered ESG data extraction.

Please create:
1. src/analyzer/llm_extractor.py - Claude API integration to extract structured ESG data
2. scripts/04_analyze_with_ai.py - Script to run extraction

The extractor should:
- Take document text and extract: emissions (scope 1,2,3), renewable energy %, targets, SBTi status, PPA mentions
- Return structured JSON matching the esg_data table schema
- Include a --dry-run flag to estimate API costs before running
- Handle long documents by chunking or summarizing

Use the extraction prompt from blueprint.md as a starting point.

Test with: python scripts/04_analyze_with_ai.py --dry-run --limit 5
```

### Build Milestone 5: Prospect Scoring

```
I'm ready for Milestone 5. Create the prospect scoring algorithm.

Please create:
1. src/analyzer/scorer.py - Scoring algorithm
2. scripts/05_score_prospects.py - Script to calculate scores

Scoring weights (from blueprint.md):
- renewable_gap_score: 25% - Gap between current and target RE%
- timeline_urgency_score: 20% - How soon are targets due
- energy_volume_score: 20% - Total energy consumption
- procurement_intent_score: 15% - PPA mentions
- esg_maturity_score: 10% - SBTi, RE100, TCFD status
- data_quality_score: 10% - How complete is our data

Priority tiers: hot (75+), warm (55-74), cool (35-54), cold (<35)

Test with: python scripts/05_score_prospects.py
```

### Build Milestone 6: Dashboard

```
I'm ready for Milestone 6. Create the Streamlit dashboard.

Please create app/dashboard.py with:
1. Filterable prospect list (by priority tier, sector, score)
2. Company detail view showing all ESG data
3. Progress charts (emissions/RE% over multiple years)
4. Source document links back to ListCorp
5. CSV export button for filtered results

Use the dashboard layout from blueprint.md as a guide.

Test with: streamlit run app/dashboard.py
```

### Debug: Docling Not Working

```
Docling extraction is failing. Help me debug:

1. Check if Docling is installed: pip show docling
2. Try a simple test:
python -c "
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert('https://www.listcorp.com/asx/xro/xero-limited/news/fy25-sustainability-report-3189699.html')
print(f'Extracted {len(result.document.export_to_markdown())} chars')
"

3. If that fails, show me the full error traceback
```

### Debug: No Documents Found

```
The document finder isn't finding ESG documents. Help me debug:

1. Test with a known company:
python scripts/02_find_esg_docs.py --ticker XRO -v

2. Check what URLs we're hitting and if we're getting blocked
3. Show me the HTML structure of the ListCorp page to verify our selectors
```

### View Current Database Stats

```
Give me a full status report on the database:

1. Total companies: sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM companies;"
2. Total documents: sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM documents;"
3. Documents by type: sqlite3 data/esg_intel.db "SELECT document_type, COUNT(*) FROM documents GROUP BY document_type;"
4. Extraction status: sqlite3 data/esg_intel.db "SELECT extraction_status, COUNT(*) FROM documents GROUP BY extraction_status;"
5. ESG data extracted: sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM esg_data;"
6. Prospect scores: sqlite3 data/esg_intel.db "SELECT priority_tier, COUNT(*) FROM prospect_scores GROUP BY priority_tier;"
```

---

## Quick Start

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run Pipeline

```bash
# Milestone 1: Import companies (already done)
python scripts/01_import_companies.py

# Milestone 2: Find ESG documents
python scripts/02_find_esg_docs.py --limit 100

# Milestone 3: Extract text with Docling
python scripts/03_extract_text.py --limit 10

# Milestone 4: AI analysis (coming soon)
python scripts/04_analyze_with_ai.py --dry-run

# Milestone 5: Score prospects (coming soon)
python scripts/05_score_prospects.py

# Milestone 6: Dashboard (coming soon)
streamlit run app/dashboard.py
```

### Verify Progress

```bash
# Check companies
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM companies;"

# Check documents found
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM documents;"

# Check extraction status
sqlite3 data/esg_intel.db "SELECT extraction_status, COUNT(*) FROM documents GROUP BY extraction_status;"

# View sample extracted text
sqlite3 data/esg_intel.db "SELECT ticker, title, char_count FROM documents d JOIN companies c ON d.company_id = c.id WHERE extraction_status = 'success' LIMIT 5;"
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
│   ├── scraper/
│   │   ├── listcorp_news.py  # Find ESG docs on ListCorp
│   │   └── text_extractor.py # Extract text with Docling
│   └── analyzer/             # (Milestone 4+)
│       ├── llm_extractor.py  # Claude API integration
│       └── scorer.py         # Prospect scoring
├── scripts/
│   ├── 01_import_companies.py
│   ├── 02_find_esg_docs.py
│   ├── 03_extract_text.py
│   ├── 04_analyze_with_ai.py # (Milestone 4)
│   └── 05_score_prospects.py # (Milestone 5)
└── app/
    └── dashboard.py          # (Milestone 6)
```

## Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Language | Python 3.11+ | Simple, widely used |
| Database | SQLite | Zero config, single file |
| Web Scraping | Playwright + stealth | Handles JS-rendered pages |
| **Document Extraction** | **Docling** (IBM) | **97.9% table accuracy on sustainability reports!** |
| PDF Fallback | PyMuPDF | Backup if Docling fails |
| AI Analysis | Claude API | Milestone 4 |
| Dashboard | Streamlit | Milestone 6 |

### Why Docling?

Docling is IBM's open-source document processing library, specifically benchmarked on sustainability reports:

- **97.9% accuracy** on complex table extraction
- AI-powered layout analysis preserves reading order
- Built-in OCR for scanned documents
- Handles PDF, DOCX, XLSX, HTML
- Outputs clean Markdown perfect for LLM analysis

**Note**: First run downloads AI models (~1-2GB). This is a one-time setup.

## Database Schema

The database has 4 main tables:

1. **companies** - All ASX companies (2,239 imported)
2. **documents** - ESG documents found on ListCorp (with extracted text)
3. **esg_data** - AI-extracted ESG metrics (Milestone 4)
4. **prospect_scores** - Calculated sales prospect scores (Milestone 5)

## Resources

- Full specification: `blueprint.md`
- Source CSV: `data/companies.csv`
- Database: `data/esg_intel.db`

## Notes

- The CSV file came from the previous esgWIKI project
- Focus is on staying within ListCorp (not scraping individual company websites)
- Multi-year coverage (FY2021-2025) to track progress over time
- Docling provides much better table extraction than PyMuPDF alone
