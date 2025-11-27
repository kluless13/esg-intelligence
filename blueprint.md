# ESG Intelligence Platform: AI-IDE Master Specification v2

> **Purpose**: This document is designed to be fed into AI coding environments (Cursor, Claude Code, Windsurf, etc.) to guide development of an ESG document scraping and analysis platform. It contains explicit instructions for AI assistants, clear milestones, and recovery strategies.

---

## PROJECT IDENTITY

**Project Name**: ESG Intel  
**Repository**: `esg-intel`  
**Owner**: klu13  
**Goal**: Extract ESG/sustainability data from ListCorp.com for ASX companies, analyze with AI, and display in a dashboard to identify high-priority renewable energy sales prospects.

---

## CRITICAL DISCOVERY (v2 Update)

### The Simple Path We Missed Before

**Key insight from klu13**: ListCorp doesn't just list companies - it **aggregates ESG documents directly in their news section**. When a company releases a sustainability report to the ASX, ListCorp captures it and **embeds the full text on their news page**.

**Example URLs discovered**:
- `https://www.listcorp.com/asx/xro/xero-limited/news/fy25-sustainability-report-3189699.html`
- `https://www.listcorp.com/asx/vau/vault-minerals-limited/news/red-5-sustainability-report-2945700.html`

**What this means**:
1. We DON'T need to chase individual company websites (each designed differently)
2. We DON'T need complex PDF downloading for most cases
3. The full report text is often embedded directly in the HTML
4. ListCorp has a consistent URL structure we can scrape

### The New Simplified Architecture

```
OLD APPROACH (failed):
ListCorp company page → Corporate Governance link → Company website (all different!) → Find ESG page → Download PDF → Parse PDF

NEW APPROACH (this spec):
ListCorp company list → Search news pages for "sustainability" OR "esg" → Extract embedded text directly from HTML → (PDF download only if text not embedded) → Analyze with AI
```

---

## CRITICAL CONTEXT FOR AI ASSISTANTS

### What Failed Before (from klu13's previous attempt)

The previous `esgWIKI` project had these issues:
1. **Tried to follow "Corporate Governance" links** - led to thousands of differently-designed company websites
2. **Required headful browser automation** - slow, fragile, couldn't run headless
3. **Scripts were company-specific** - hardcoded for NAB, couldn't generalize
4. **No unified data storage** - JSON files everywhere

### What's Different Now

1. **Stay within ListCorp** - don't chase company websites
2. **Text is in the HTML** - often no PDF parsing needed
3. **Consistent URL patterns** - reliable scraping
4. **Multi-year coverage** - get 3-4 years of reports to show progress

---

## AI ASSISTANT INSTRUCTIONS

### How to Use This Document

When klu13 asks you to work on this project:

1. **Always check which milestone they're on** - ask if unclear
2. **Never skip ahead** - complete each milestone fully before moving on
3. **Test before declaring done** - provide test commands for every piece of code
4. **Explain what you're doing** - klu13 is learning, add comments liberally
5. **When something breaks**, use the fallback strategies documented below

### Communication Style

- Use simple, direct language
- Explain WHY not just WHAT
- Provide copy-paste ready commands
- Include expected output examples
- When there are multiple ways to do something, pick ONE and explain why

---

## TECHNOLOGY STACK (LOCKED IN)

Do not deviate from this stack without explicit approval:

| Component | Technology | Why |
|-----------|------------|-----|
| Language | Python 3.11+ | klu13 knows some Python |
| Database | SQLite | Zero config, single file, SQL queryable |
| Web Scraping | `requests` + `BeautifulSoup4` | Simple, works for ListCorp |
| Browser Fallback | `playwright` | Only if JS rendering needed |
| PDF Extraction | `pymupdf` (fitz) | For PDFs when text not in HTML |
| AI Extraction | Claude API (Anthropic) | klu13 has access |
| Dashboard | Streamlit | One file, Python only, no JS needed |

### Required Python Packages

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pymupdf>=1.24.0
playwright>=1.40.0
anthropic>=0.18.0
streamlit>=1.32.0
pandas>=2.0.0
python-dotenv>=1.0.0
```

---

## EXISTING DATA ASSET

klu13 already has a CSV file with all ASX companies from their previous attempt:
**Source**: `https://github.com/kluless13/esgWIKI/blob/main/crawler/tests/companies-list.csv`

This CSV should be used as the starting point - no need to re-scrape the company list.

Expected columns (verify and adapt):
- `ticker` - ASX ticker symbol (e.g., "BHP", "XRO")
- `company_name` - Full company name
- `listcorp_url` - URL to ListCorp company page

---

## PROJECT STRUCTURE

```
esg-intel/
├── .env                      # API keys (never commit)
├── .env.example              # Template for .env
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
│
├── config/
│   └── settings.py           # All configuration in one place
│
├── data/
│   ├── companies.csv         # Master company list (from klu13's existing CSV)
│   ├── esg_intel.db          # SQLite database (gitignored)
│   └── pdfs/                 # Downloaded PDFs (only when needed)
│       └── {ticker}/
│
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── listcorp_news.py  # Find ESG docs in ListCorp news
│   │   └── text_extractor.py # Extract text from HTML or PDF
│   │
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── llm_extractor.py  # Claude API integration
│   │   └── scorer.py         # Prospect scoring algorithm
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── schema.py         # SQLite schema definitions
│   │   └── queries.py        # Database operations
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py        # Common utilities
│
├── scripts/
│   ├── 01_import_companies.py    # Import existing CSV
│   ├── 02_find_esg_docs.py       # Find ESG docs on ListCorp
│   ├── 03_extract_text.py        # Extract text from docs
│   ├── 04_analyze_with_ai.py     # AI extraction
│   ├── 05_score_prospects.py     # Calculate scores
│   └── run_pipeline.py           # Run everything
│
├── app/
│   └── dashboard.py          # Streamlit dashboard
│
└── tests/
    └── test_scraper.py
```

---

## DATABASE SCHEMA

```sql
-- Companies table: All ASX companies (imported from CSV)
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    sector TEXT,
    listcorp_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ESG Documents found on ListCorp
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT,                   -- 'sustainability_report', 'annual_report', 'climate_disclosure'
    financial_year TEXT,                  -- 'FY2024', 'FY2023', etc.
    publication_date DATE,
    listcorp_news_url TEXT NOT NULL,      -- The ListCorp news page URL
    pdf_url TEXT,                         -- Direct PDF link if available
    has_embedded_text INTEGER DEFAULT 0,  -- 1 if text is in HTML, 0 if need PDF
    text_content TEXT,                    -- Extracted text (full or summary)
    extraction_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, listcorp_news_url)
);

-- AI-extracted ESG data
CREATE TABLE esg_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    document_id INTEGER,
    data_year INTEGER,                    -- Year this data applies to
    
    -- Emissions Data
    scope1_emissions REAL,                -- tonnes CO2e
    scope2_emissions REAL,                -- Market-based preferred
    scope3_emissions REAL,
    total_emissions REAL,
    emissions_baseline_year INTEGER,
    
    -- Targets
    net_zero_target_year INTEGER,
    emissions_reduction_target_pct REAL,  -- e.g., 50 for 50%
    emissions_reduction_target_year INTEGER,
    
    -- Renewable Energy
    renewable_energy_pct_current REAL,
    renewable_energy_target_pct REAL,
    renewable_energy_target_year INTEGER,
    energy_consumption_mwh REAL,
    
    -- Commitments & Frameworks
    sbti_status TEXT,                     -- 'committed', 'validated', 'targets_set', 'none'
    re100_member INTEGER,
    tcfd_aligned INTEGER,
    climate_active_certified INTEGER,
    
    -- PPAs and Procurement
    has_ppa INTEGER,
    ppa_details TEXT,
    renewable_procurement_mentioned INTEGER,
    
    -- Metadata
    confidence_score REAL,
    extraction_notes TEXT,
    raw_llm_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Calculated prospect scores
CREATE TABLE prospect_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL UNIQUE,
    
    -- Component Scores (0-100)
    renewable_gap_score REAL,
    timeline_urgency_score REAL,
    energy_volume_score REAL,
    procurement_intent_score REAL,
    company_size_score REAL,
    esg_maturity_score REAL,
    data_quality_score REAL,              -- How complete is our data
    
    -- Final Score
    total_score REAL,
    priority_tier TEXT,                   -- 'hot', 'warm', 'cool', 'cold'
    
    -- Context
    key_opportunities TEXT,
    years_of_data INTEGER,                -- How many years of reports we have
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Indexes
CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_documents_company ON documents(company_id);
CREATE INDEX idx_documents_fy ON documents(financial_year);
CREATE INDEX idx_esg_data_company ON esg_data(company_id);
CREATE INDEX idx_prospect_scores_total ON prospect_scores(total_score DESC);
```

---

## LISTCORP URL PATTERNS

Understanding these patterns is critical for scraping:

```
Company page:
https://www.listcorp.com/asx/{ticker}/{company-slug}

News/Announcements page:
https://www.listcorp.com/asx/{ticker}/{company-slug}/news

Individual news item (contains document):
https://www.listcorp.com/asx/{ticker}/{company-slug}/news/{document-title-slug}-{numeric-id}.html

Examples:
https://www.listcorp.com/asx/xro/xero-limited/news/fy25-sustainability-report-3189699.html
https://www.listcorp.com/asx/vau/vault-minerals-limited/news/red-5-sustainability-report-2945700.html
https://www.listcorp.com/asx/bhp/bhp-group-limited/news/annual-report-2024-3123456.html
```

### Search Strategy for Finding ESG Documents

For each company, search their news page for documents containing these keywords in the title:

**High Priority (definitely ESG)**:
- "sustainability report"
- "esg report"
- "climate report"
- "environmental report"

**Medium Priority (often contains ESG section)**:
- "annual report"
- "annual review"

**Also Capture**:
- "tcfd"
- "emissions"
- "net zero"
- "carbon"
- "renewable"

### Multi-Year Coverage

For each company, try to get reports from:
- FY2024 (or most recent)
- FY2023
- FY2022
- FY2021 (if available)

This allows tracking progress over time, which is valuable for sales intelligence.

---

## MILESTONE 1: PROJECT SETUP & COMPANY IMPORT

### Goal
Set up project structure and import existing company CSV.

### Success Criteria
- [ ] Project structure created
- [ ] Database initialized with schema
- [ ] Companies imported from klu13's existing CSV
- [ ] Can query: `SELECT COUNT(*) FROM companies`

### AI Instructions for Milestone 1

```
TASK: Set up project and import companies from existing CSV.

STEP 1: Create project structure
- Create all directories as shown in PROJECT STRUCTURE
- Create requirements.txt with packages listed above
- Create .env.example with: ANTHROPIC_API_KEY=your_key_here
- Create .gitignore

STEP 2: Create config/settings.py
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "esg_intel.db"
PDF_DIR = DATA_DIR / "pdfs"
COMPANIES_CSV = DATA_DIR / "companies.csv"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

# API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Scraping
REQUEST_DELAY = 2  # seconds between requests
LISTCORP_BASE = "https://www.listcorp.com"

# Target years for reports
TARGET_YEARS = ["FY2024", "FY2025", "FY2023", "FY2022", "FY2021"]
```

STEP 3: Create src/database/schema.py
- Function: init_database() - creates all tables
- Use the exact SQL schema provided above

STEP 4: Create scripts/01_import_companies.py
- Download klu13's CSV from GitHub (or use local copy)
- Parse CSV and insert into companies table
- Handle duplicates gracefully
- Print summary

IMPORTANT: First check what columns are actually in klu13's CSV file.
If columns differ from expected, adapt the import logic.

TEST COMMAND:
python scripts/01_import_companies.py

EXPECTED OUTPUT:
Initializing database...
Importing companies from CSV...
Imported 2,228 companies
Sample: BHP - BHP Group Limited
Done!
```

---

## MILESTONE 2: FIND ESG DOCUMENTS ON LISTCORP

### Goal
For each company, search their ListCorp news page for ESG-related documents.

### Success Criteria
- [ ] ESG documents found and stored in `documents` table
- [ ] Multiple years of reports captured where available
- [ ] Can query: `SELECT COUNT(*) FROM documents`

### AI Instructions for Milestone 2

```
TASK: Find ESG documents for each company on ListCorp.

STEP 1: Create src/scraper/listcorp_news.py

Function: find_esg_documents(ticker: str, company_slug: str) -> List[Dict]

APPROACH:
1. Construct news page URL: f"https://www.listcorp.com/asx/{ticker}/{company_slug}/news"
2. Fetch the page with requests
3. Parse with BeautifulSoup
4. Find all news item links
5. Filter for ESG-related keywords in title
6. Extract: title, URL, publication date, financial year

KEYWORD MATCHING (case-insensitive):
```python
HIGH_PRIORITY_KEYWORDS = [
    "sustainability report",
    "sustainability-report",
    "esg report",
    "climate report",
    "environmental report",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "annual report",
    "annual-report",
]

ADDITIONAL_KEYWORDS = [
    "tcfd",
    "emissions",
    "net zero",
    "net-zero",
    "carbon",
    "renewable",
]
```

RETURN FORMAT:
```python
[
    {
        "title": "FY25 Sustainability Report",
        "listcorp_news_url": "https://www.listcorp.com/asx/xro/.../fy25-sustainability-report-3189699.html",
        "document_type": "sustainability_report",
        "financial_year": "FY2025",  # Extract from title
        "publication_date": "2025-05-15"  # If available
    },
    ...
]
```

FINANCIAL YEAR EXTRACTION:
- Look for patterns: "FY25", "FY2025", "2025", "2024"
- Map: "FY25" -> "FY2025", "2024" -> "FY2024"

STEP 2: Create scripts/02_find_esg_docs.py
- Loop through all companies in database
- Call find_esg_documents for each
- Insert into documents table
- Respect rate limiting (2 second delay)
- Handle errors gracefully (log and continue)
- Print progress: [X/2228] {ticker} - Found {N} documents

FLAGS:
--limit N     : Process only first N companies
--ticker XRO  : Process single company
--skip-existing : Skip companies that already have documents

TEST COMMANDS:
python scripts/02_find_esg_docs.py --ticker XRO
python scripts/02_find_esg_docs.py --limit 10

EXPECTED OUTPUT:
[1/10] XRO - Xero Limited - Found 4 documents
  - FY25 Sustainability Report (FY2025)
  - FY24 Sustainability Report (FY2024)
  - FY23 Sustainability Report (FY2023)
  - Annual Report 2024 (FY2024)
[2/10] BHP - BHP Group Limited - Found 6 documents
...
Done! Total documents found: 38
```

### Fallback Strategies

**If news page structure changes:**
- Look for alternative CSS selectors
- Try finding any links containing ".html" in the news section

**If rate limited:**
- Increase delay to 5 seconds
- Add random jitter (1-3 seconds)

**If company slug doesn't match:**
- Extract slug from listcorp_url in CSV if available
- Or scrape it from the company page

---

## MILESTONE 3: EXTRACT TEXT FROM DOCUMENTS

### Goal
Extract the full text from each document (preferring HTML-embedded text, falling back to PDF).

### Success Criteria
- [ ] Text extracted for all documents
- [ ] `documents.text_content` populated
- [ ] `documents.has_embedded_text` set correctly

### AI Instructions for Milestone 3

```
TASK: Extract text from ListCorp document pages.

KEY INSIGHT: ListCorp often embeds the FULL report text in the HTML page.
Check this first before trying to download PDFs.

STEP 1: Create src/scraper/text_extractor.py

Function: extract_document_text(listcorp_news_url: str) -> Dict

APPROACH:
1. Fetch the ListCorp news page
2. Parse with BeautifulSoup
3. Look for the main content area (usually in a specific div/article)
4. Extract all text content
5. Clean up whitespace and formatting
6. Check if text length is substantial (>1000 chars = embedded report)

```python
def extract_document_text(url: str) -> Dict:
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Find main content - adjust selectors based on actual HTML
    # ListCorp typically has the document text in a main content div
    content = soup.find('div', class_='announcement-content')  # Adjust selector
    
    if content:
        text = content.get_text(separator='\n', strip=True)
        
        # Check if this is a full embedded report or just a summary
        if len(text) > 5000:  # Substantial content
            return {
                "has_embedded_text": True,
                "text_content": text,
                "pdf_url": None,
                "extraction_status": "extracted"
            }
    
    # If no embedded text, look for PDF link
    pdf_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
    if pdf_link:
        return {
            "has_embedded_text": False,
            "text_content": None,
            "pdf_url": pdf_link['href'],
            "extraction_status": "needs_pdf"
        }
    
    return {
        "has_embedded_text": False,
        "text_content": None,
        "pdf_url": None,
        "extraction_status": "failed"
    }
```

STEP 2: PDF Extraction Fallback

Function: extract_pdf_text(pdf_url: str, ticker: str) -> str

Only call this if has_embedded_text is False and pdf_url exists.

```python
import fitz  # pymupdf

def extract_pdf_text(pdf_url: str, ticker: str) -> str:
    # Download PDF
    response = requests.get(pdf_url)
    pdf_path = PDF_DIR / ticker / f"{hash(pdf_url)}.pdf"
    pdf_path.parent.mkdir(exist_ok=True)
    pdf_path.write_bytes(response.content)
    
    # Extract text
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    return text
```

STEP 3: Create scripts/03_extract_text.py
- Query documents where extraction_status = 'pending'
- Call extract_document_text for each
- If needs PDF, call extract_pdf_text
- Update documents table with results
- Handle errors gracefully

FLAGS:
--limit N         : Process only N documents
--reprocess       : Reprocess all, including already extracted

TEST COMMANDS:
python scripts/03_extract_text.py --limit 5

EXPECTED OUTPUT:
[1/5] XRO - FY25 Sustainability Report
  - Source: HTML embedded (23,456 chars)
  - Status: extracted
[2/5] BHP - Sustainability Report 2024
  - Source: PDF downloaded (45,678 chars)
  - Status: extracted
...
Done! Extracted: 5, Failed: 0
```

---

## MILESTONE 4: AI-POWERED DATA EXTRACTION

### Goal
Use Claude API to extract structured ESG data from document text.

### Success Criteria
- [ ] ESG data extracted for all processed documents
- [ ] `esg_data` table populated with structured metrics
- [ ] Multiple years of data per company where available

### AI Instructions for Milestone 4

```
TASK: Create Claude API integration for ESG data extraction.

STEP 1: Create src/analyzer/llm_extractor.py

SYSTEM PROMPT:
"""
You are an ESG data extraction specialist analyzing Australian company sustainability reports.
Extract specific metrics and commitments. Be precise - only extract data explicitly stated.
If data is not found, use null. Pay attention to the financial year context.
"""

EXTRACTION PROMPT:
"""
Company: {company_name}
Financial Year: {financial_year}
Document Type: {document_type}

Extract ESG metrics from this sustainability/annual report text.
Return ONLY a valid JSON object with these fields:

{
    "data_year": <int, the financial year this data is for, e.g. 2024>,
    
    "scope1_emissions": <number in tonnes CO2e or null>,
    "scope2_emissions": <number in tonnes CO2e, market-based preferred, or null>,
    "scope3_emissions": <number in tonnes CO2e or null>,
    "total_emissions": <number or null>,
    "emissions_baseline_year": <int or null>,
    
    "net_zero_target_year": <int or null>,
    "emissions_reduction_target_pct": <number 0-100 or null>,
    "emissions_reduction_target_year": <int or null>,
    
    "renewable_energy_pct_current": <number 0-100 or null>,
    "renewable_energy_target_pct": <number 0-100 or null>,
    "renewable_energy_target_year": <int or null>,
    "energy_consumption_mwh": <number or null>,
    
    "sbti_status": <"committed"|"validated"|"targets_set"|"none"|null>,
    "re100_member": <true|false|null>,
    "tcfd_aligned": <true|false|null>,
    "climate_active_certified": <true|false|null>,
    
    "has_ppa": <true|false|null>,
    "ppa_details": <string description or null>,
    "renewable_procurement_mentioned": <true|false|null>,
    
    "confidence_score": <0.0-1.0, how confident you are in this extraction>,
    "extraction_notes": <string with any caveats or important context>
}

Document text (may be truncated):
{document_text}
"""

STEP 2: Handle Long Documents

Documents may exceed Claude's context. Strategy:
1. If text < 100,000 chars, send full text
2. If text > 100,000 chars, send:
   - First 50,000 chars (usually has summary and key metrics)
   - Search for "emissions", "renewable", "target" sections and include those
   - Last 10,000 chars (often has data tables)

STEP 3: Create scripts/04_analyze_with_ai.py
- Query documents with text_content that haven't been analyzed
- Group by company (analyze all documents for a company together)
- Call Claude API for each document
- Insert results into esg_data table
- Store raw LLM response for debugging

FLAGS:
--limit N        : Process N companies
--dry-run        : Show what would be processed, estimate cost
--company XRO    : Process single company

COST ESTIMATION:
- Estimate ~$0.03 per document (input + output tokens)
- Print estimated cost before processing

TEST COMMANDS:
python scripts/04_analyze_with_ai.py --dry-run --limit 5
python scripts/04_analyze_with_ai.py --company XRO

EXPECTED OUTPUT (dry-run):
Would process 5 companies, 18 documents
Estimated tokens: ~500,000
Estimated cost: ~$0.75
Run without --dry-run to proceed.

EXPECTED OUTPUT (actual):
[1/5] XRO - Xero Limited
  Document: FY25 Sustainability Report
  - Scope 1+2: 171 tCO2e
  - RE Target: 60% reduction by 2034
  - SBTi: Submitted for validation
  - Confidence: 0.92
  
  Document: FY24 Sustainability Report
  - Scope 1+2: 619 tCO2e
  - RE Current: Not specified
  - Confidence: 0.85
...
Done! Processed: 5 companies, 18 documents
```

---

## MILESTONE 5: PROSPECT SCORING

### Goal
Calculate prospect scores to prioritize companies for renewable energy sales.

### Success Criteria
- [ ] All companies with ESG data have prospect scores
- [ ] Scores reflect sales opportunity for renewable energy
- [ ] Top prospects identifiable via query

### AI Instructions for Milestone 5

```
TASK: Implement prospect scoring algorithm.

SCORING WEIGHTS (total = 100):
- renewable_gap_score: 25% - Gap between current and target RE%
- timeline_urgency_score: 20% - How soon are targets due
- energy_volume_score: 20% - Total energy consumption
- procurement_intent_score: 15% - PPA mentions, procurement language
- esg_maturity_score: 10% - SBTi, RE100, reporting quality
- data_quality_score: 10% - How complete is our data

SCORING LOGIC:

renewable_gap_score:
- Use most recent year's data
- gap = target_pct - current_pct
- If gap > 80: 100, 60-80: 80, 40-60: 60, 20-40: 40, 0-20: 20, achieved: 0
- No data: 40 (neutral-ish, we don't know)

timeline_urgency_score:
- years_until = target_year - 2025
- <= 2 years: 100, 3-4: 80, 5-7: 60, 8-10: 40, >10: 20
- No target: 30

energy_volume_score:
- Normalize across all companies with data
- Top 10%: 100, 10-25%: 80, 25-50%: 60, 50-75%: 40, Bottom 25%: 20
- No data: 50

procurement_intent_score:
- has_ppa AND recent: 100
- renewable_procurement_mentioned: 60
- No mentions: 20

esg_maturity_score:
- SBTi validated + RE100: 100
- SBTi committed OR RE100: 75
- TCFD aligned: 50
- Basic reporting: 25

data_quality_score:
- 3+ years of reports: 100
- 2 years: 70
- 1 year: 40
- No reports found: 0

PRIORITY TIERS:
- total >= 75: 'hot'
- total >= 55: 'warm'  
- total >= 35: 'cool'
- total < 35: 'cold'

Generate key_opportunities text summarizing why this is a good/bad prospect.

TEST COMMAND:
python scripts/05_score_prospects.py

EXPECTED OUTPUT:
Calculating prospect scores...
Processed 150 companies

TOP 10 PROSPECTS:
1. FMG (92) - HOT - 15% RE current, 100% target by 2030
2. WOW (88) - HOT - Active PPA seeker, aggressive timeline
...
```

---

## MILESTONE 6: DASHBOARD

### Goal
Create a Streamlit dashboard to browse and filter prospects.

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ESG Intelligence Dashboard                          [Export CSV]   │
├─────────────────────────────────────────────────────────────────────┤
│  FILTERS                                                            │
│  Priority: [All ▼]  Sector: [All ▼]  Min Score: [___]  Search: [__]│
├─────────────────────────────────────────────────────────────────────┤
│  PROSPECTS (45 companies)                                           │
│  ┌──────┬──────────────────┬────────────┬────────┬────────────────┐│
│  │Score │ Company          │ RE Gap     │ Target │ Years of Data  ││
│  ├──────┼──────────────────┼────────────┼────────┼────────────────┤│
│  │ 92   │ FMG              │ 85%        │ 2030   │ 4 years        ││
│  │ 88   │ Woolworths       │ 60%        │ 2025   │ 3 years        ││
│  │ ...  │ ...              │ ...        │ ...    │ ...            ││
│  └──────┴──────────────────┴────────────┴────────┴────────────────┘│
├─────────────────────────────────────────────────────────────────────┤
│  SELECTED: FMG - Fortescue Metals Group                             │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ EMISSIONS (Scope 1+2)         │ RENEWABLE ENERGY                ││
│  │ FY24: 15.2M tCO2e            │ Current: 15%                    ││
│  │ FY23: 14.8M tCO2e            │ Target: 100% by 2030            ││
│  │ Baseline: 2020               │ Gap: 85%                        ││
│  │                              │                                  ││
│  │ COMMITMENTS                   │ OPPORTUNITY                     ││
│  │ ✓ SBTi Validated             │ HUGE renewable gap              ││
│  │ ✓ TCFD Aligned               │ Aggressive 2030 timeline        ││
│  │ ✗ RE100 (not member)         │ Large energy consumer           ││
│  │                              │ Active in PPA market            ││
│  │                                                                 ││
│  │ PROGRESS OVER TIME                                              ││
│  │ [Chart showing emissions/RE% trend over 4 years]                ││
│  │                                                                 ││
│  │ SOURCE DOCUMENTS:                                               ││
│  │ • FY24 Sustainability Report [View on ListCorp]                 ││
│  │ • FY23 Sustainability Report [View on ListCorp]                 ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Filterable prospect list** - sort by score, filter by tier/sector
2. **Company detail view** - all extracted ESG data
3. **Progress tracking** - show change over multiple years
4. **Source links** - link back to ListCorp documents
5. **CSV export** - download filtered list for CRM import

---

## COMMON ERRORS AND FIXES

### Error: "No module named 'src'"
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts/01_import_companies.py
```

### Error: ListCorp returns 403 Forbidden
```python
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}
response = requests.get(url, headers=HEADERS)
```

### Error: Company slug doesn't match expected pattern
```python
# Extract slug from the listcorp_url in CSV if available
# Or construct from company name:
import re
slug = re.sub(r'[^a-z0-9]+', '-', company_name.lower()).strip('-')
```

### Error: Claude API rate limit
```python
import time
from anthropic import RateLimitError

def call_claude_with_retry(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.messages.create(...)
        except RateLimitError:
            wait = 2 ** attempt
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
    raise Exception("Max retries exceeded")
```

---

## QUICK REFERENCE COMMANDS

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pipeline
python scripts/01_import_companies.py
python scripts/02_find_esg_docs.py --limit 50
python scripts/03_extract_text.py --limit 50
python scripts/04_analyze_with_ai.py --dry-run --limit 10
python scripts/04_analyze_with_ai.py --limit 10
python scripts/05_score_prospects.py

# Dashboard
streamlit run app/dashboard.py

# Database queries
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM companies;"
sqlite3 data/esg_intel.db "SELECT COUNT(*) FROM documents;"
sqlite3 data/esg_intel.db "SELECT * FROM prospect_scores ORDER BY total_score DESC LIMIT 10;"
```

---

## DEFINITION OF DONE

The project is complete when:

1. ✅ Companies imported from existing CSV (2,000+)
2. ✅ ESG documents found for 500+ companies
3. ✅ Text extracted from 80%+ of documents found
4. ✅ AI analysis completed for 100+ companies
5. ✅ Prospect scores calculated
6. ✅ Dashboard displays sortable, filterable prospect list
7. ✅ Can see company progress over multiple years
8. ✅ Can export top prospects to CSV

---

*Document Version: 2.0*  
*Updated: November 2025*  
*Key Change: ListCorp-centric approach - extract text directly from HTML where possible*