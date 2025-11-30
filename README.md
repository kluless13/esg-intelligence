# ESG Intelligence Platform

AI-powered system to discover, extract, and analyze ESG/sustainability data from ASX companies. Identifies high-priority renewable energy sales prospects using Claude AI.

## Project Status

| Milestone | Status | Description |
|-----------|--------|-------------|
| 1. Setup & Import | ✅ COMPLETE | 2,239 ASX companies imported |
| 2a. ListCorp Scraper | ✅ COMPLETE | Find docs via ASX announcements |
| 2b. Website Crawler | ✅ **COMPLETE** | Find docs on company websites (sitemap fix 2025-11-29) |
| 3. Text Extraction | ✅ COMPLETE | Docling integration (97.9% table accuracy) |
| 4. AI Analysis | ✅ COMPLETE | Claude extracts ESG metrics |
| 5. Prospect Scoring | 🔄 **NEXT** | Calculate sales priority scores |
| 6. Dashboard | 📋 TODO | Streamlit visualization |

---

## 🚨 The Problem & Solution

### Current Limitation

The ListCorp scraper (Milestone 2a) only finds **~25% of sustainability reports** because:
- Most companies publish reports on their **own websites**, not ASX announcements
- Many ESG reports are standalone PDFs on investor relations pages
- Small companies don't file sustainability reports to ASX at all

### Solution: Website Crawler (Milestone 2b)

Crawl company websites directly using a 4-step approach:

```
┌─────────────────────────────────────────────────────────────┐
│ Step A: Get Company Website URL                             │
├─────────────────────────────────────────────────────────────┤
│ • We already have 2,239 companies in database (from CSV)    │
│ • Discover website via:                                     │
│   1. Try common patterns: {ticker}.com, {ticker}.com.au    │
│   2. Google search: "{company name}" official website       │
│ • Store in database (new 'website' column in companies)     │
│ • Example: XRO → xero.com, BHP → bhp.com                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step B: Discover All URLs on Company Website                │
├─────────────────────────────────────────────────────────────┤
│ • Check robots.txt → find sitemap.xml                       │
│ • Parse sitemap.xml → get all page URLs                     │
│ • If no sitemap, crawl key sections:                        │
│   /investors, /sustainability, /about, /esg, /governance   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step C: Filter for ESG/Sustainability URLs                  │
├─────────────────────────────────────────────────────────────┤
│ Keywords in URL path or page title:                         │
│ • sustainability, esg, climate, environment, carbon         │
│ • annual-report, investor, governance, tcfd, emissions      │
│ • net-zero, renewable, energy, ghg, scope-1, scope-2       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step D: Extract Report Links from Filtered Pages            │
├─────────────────────────────────────────────────────────────┤
│ • Visit each filtered URL                                   │
│ • Find PDF/XLSX download links on page                      │
│ • Filter for report keywords in link text/filename          │
│ • Save to documents table with source='website'            │
└─────────────────────────────────────────────────────────────┘
```

### Expected Improvement

| Metric | ListCorp Only | + Website Crawler |
|--------|---------------|-------------------|
| Document discovery rate | 25-30% | **80-90%** |
| Companies with ESG data | 33% | **70%+** |
| Documents per company | 1-5 | **5-15** (multi-year) |

### Real Examples Found

**Xero (XRO) - xero.com:**
- ✅ **19,053 URLs** discovered from sitemap (all country sites)
- ✅ **772 ESG-related URLs** filtered
- ✅ **8 reports** extracted including:
  - "Xero Sustainability Report 2025 (PDF)"
  - "Continuous Disclosure Policy"
  - Cross-domain support: brandfolder.xero.com

**BHP - bhp.com:**
- ✅ **13,931 URLs** discovered from sitemap (English + Spanish)
- ✅ Previously blocked (403 errors) - **now working** with ultimate-sitemap-parser
- ✅ Supports nested sitemaps and .gz compression

---

## ✅ Milestone 2b Hardening Updates (Nov 2025)

What we added to improve discovery and robustness:

- Sitemap insufficiency fallback
  - If sitemap yields <10 URLs or 0 ESG URLs, auto-fallback to crawling common paths and on-site inspection.
- On-site inspection (browser-assisted)
  - Scans header/nav/footer and tries on-site search inputs for "sustainability" and "esg".
- Governance/Investor seeding from ListCorp
  - Reads “Company Resources” on the ListCorp company page (e.g., Corporate Governance, Investor Relations, Reports).
  - Uses these portals as seeds and runs a bounded same‑domain BFS.
  - Cross‑TLD aware (e.g., `anz.com` and `anz.com.au` treated as same brand).
- Bounded BFS (balanced)
  - BFS from governance/investor/sustainability hubs; prioritizes paths with sustainability/esg/report/investor/governance/climate/environment/tcfd/data/download/documents/publications.
  - Caps pages visited; stops early when enough docs are found.
- Multi‑format document detection
  - Accepts `.pdf`, `.xlsx`, `.xls`, `.xlsm`, `.csv`, `.ods` and query‑style downloads (`?file=…`, `?document=…`).
  - More lenient on link text within pre-filtered ESG pages to avoid missing generically named files (e.g., “Databook”).
- Headful browser fallback (final safety net)
  - Optional, launches Chromium (visible) to auto‑scroll/expand lists and harvest links from governance/investor hubs for hard sites.
- Schema normalization and de‑duplication
  - Added `document_url` and `website_source_page` with a unique index on `(company_id, document_url, source)`.
  - Inserts now use `document_url` for uniqueness; `website_source_page` preserves provenance.
- Logging and diagnostics
  - Logs which portals were discovered, BFS stats, and filtered‑out link samples.

New CLI flags (scripts/02b_find_via_website.py):

- `--fallback-inspect` Enable on-site inspect (nav/footer/search) fallback
- `--site-search-queries "sustainability,esg"` Override on-site search queries
- `--bfs-max-pages 100` Cap pages during governance/investor BFS
- `--target-docs 10` Stop early when enough documents found
- `--headful-fallback` Enable headful browser fallback to harvest links
- `--headful-max-pages 60` Cap pages in headful fallback
- `--headful-max-minutes 3` Time budget for headful fallback
- `--seed-override <URL>` Add a known sustainability hub URL to seed discovery

Examples:

```bash
# Run single company with balanced discovery (no DDG)
python scripts/02b_find_via_website.py --ticker XRO --fallback-inspect --bfs-max-pages 120 --max-esg-pages 20 -vv

# Hard site: enable headful fallback and add a known seed
python scripts/02b_find_via_website.py --ticker ANZ \
  --fallback-inspect --bfs-max-pages 120 --max-esg-pages 20 \
  --headful-fallback \
  --seed-override "https://www.anz.com.au/about-us/esg/environmental-sustainability/" -vv

# Another company (e.g., CSL) with the balanced stack
python scripts/02b_find_via_website.py --ticker CSL --fallback-inspect --bfs-max-pages 120 --max-esg-pages 20 -vv
```

Recent result highlights:

- XRO (xero.com): 19,053 sitemap URLs → 772 ESG URLs → multiple reports incl. Sustainability Report 2025.
- CSL (csl.com): 1,066 sitemap URLs → 66 ESG URLs → 48 documents saved (annual reports, modern slavery, tax transparency, WGEA, CR reports, assurance statements).
- BHP (bhp.com): sitemap discovery strong; some sites require deeper extraction on ESG pages (use inspect/BFS/headful as needed).

## 🤖 Claude Code Prompts

Copy-paste these prompts to continue development.

---

### 🔥 BUILD: Website Crawler (Milestone 2b) - PRIORITY

```
I need to build a website crawler to find ESG reports on company websites. This is MORE EFFECTIVE than scraping ListCorp announcements.

The 4-step approach:

STEP A - Get company website URL:
- We already have 2,239 companies in the database from CSV - NO NEED to scrape ListCorp!
- Discover website by trying common URL patterns:
  1. {ticker.lower()}.com (e.g., "xro" → xro.com - doesn't exist, but "bhp" → bhp.com works)
  2. {ticker.lower()}.com.au (common for ASX companies)
  3. Google search "{company name}" official website (fallback)
- Verify URL is valid (returns 200, contains company name/ticker)
- Add 'website' column to companies table if it doesn't exist
- Store the domain (e.g., "xero.com", "bhp.com")

STEP B - Discover all URLs on the website:
- First check {domain}/robots.txt for sitemap location
- Parse sitemap.xml to get all URLs
- If no sitemap, crawl these common paths:
  /investors, /sustainability, /about, /esg, /governance,
  /corporate, /responsibility, /environment, /annual-reports

STEP C - Filter for ESG-related URLs:
- Filter URLs containing keywords: sustainability, esg, climate, 
  environment, carbon, emissions, tcfd, annual-report, governance,
  net-zero, renewable, ghg, scope

STEP D - Extract report links from those pages:
- Visit each filtered URL
- Find all PDF and XLSX links on the page
- Filter for report-related filenames/link text
- Save to documents table with source='website' (vs source='listcorp')

Please create:
1. src/scraper/company_website.py - The crawler module with functions for each step
2. scripts/02b_find_via_website.py - Script to run the crawler

Database changes needed:
- ALTER TABLE companies ADD COLUMN website TEXT;
- ALTER TABLE documents ADD COLUMN source TEXT DEFAULT 'listcorp';

The script should support:
--ticker XRO        # Test with single company
--limit 10          # Process N companies
--skip-existing     # Skip companies that already have website docs
-v                  # Verbose output

Test with: python scripts/02b_find_via_website.py --ticker XRO -v

Use Playwright with stealth mode (like the existing ListCorp scraper).
```

---

### Check Current Database Stats

```
Give me a full status report on the database:

sqlite3 data/esg_intel.db "
SELECT '=== COMPANIES ===' as section;
SELECT COUNT(*) as total_companies FROM companies;
SELECT COUNT(*) as companies_with_website FROM companies WHERE website IS NOT NULL;

SELECT '=== DOCUMENTS ===' as section;
SELECT COUNT(*) as total_documents FROM documents;
SELECT source, COUNT(*) as count FROM documents GROUP BY source;
SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type;

SELECT '=== EXTRACTION ===' as section;
SELECT extraction_status, COUNT(*) as count FROM documents GROUP BY extraction_status;

SELECT '=== ESG DATA ===' as section;
SELECT COUNT(*) as total_esg_records FROM esg_data;
SELECT COUNT(DISTINCT company_id) as companies_with_esg_data FROM esg_data;
"
```

---

### Test Website Crawler on Single Company

```
Test the website crawler on Xero (XRO):

python scripts/02b_find_via_website.py --ticker XRO -v

Expected output:
- Find xero.com from ListCorp page
- Discover sitemap or crawl /investors, /sustainability
- Find URLs containing sustainability/esg keywords
- Extract PDF links from those pages
- Show found documents

Then check what was saved:
sqlite3 data/esg_intel.db "SELECT title, url, source FROM documents WHERE company_id = (SELECT id FROM companies WHERE ticker = 'XRO') ORDER BY source;"
```

---

### Run Website Crawler on Top 50 Companies

```
Run the website crawler on the top 50 ASX companies by market cap:

python scripts/02b_find_via_website.py --limit 50 --skip-existing

Show me:
1. How many companies were processed
2. How many new documents were found
3. Any errors encountered
4. Comparison: documents from ListCorp vs website crawler
```

---

### Extract Text from New Documents

```
Extract text from all newly found website documents:

python scripts/03_extract_text.py --source website --limit 20

This uses Docling for high-quality extraction. Show me the results.
```

---

### Run AI Analysis on New Documents

```
Run Claude AI analysis on the new website documents:

python scripts/04_analyze_with_ai.py --source website --dry-run

Show estimated cost first, then if reasonable:
python scripts/04_analyze_with_ai.py --source website --limit 10
```

---

### Compare ListCorp vs Website Results

```
Compare the quality of documents found via ListCorp vs Website crawler:

sqlite3 data/esg_intel.db "
SELECT 
    source,
    COUNT(*) as doc_count,
    AVG(char_count) as avg_chars,
    SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as successful,
    COUNT(DISTINCT company_id) as unique_companies
FROM documents 
GROUP BY source;
"

Also show me which companies have documents from BOTH sources:
sqlite3 data/esg_intel.db "
SELECT c.ticker, c.name,
    SUM(CASE WHEN d.source = 'listcorp' THEN 1 ELSE 0 END) as listcorp_docs,
    SUM(CASE WHEN d.source = 'website' THEN 1 ELSE 0 END) as website_docs
FROM companies c
JOIN documents d ON c.id = d.company_id
GROUP BY c.id
HAVING listcorp_docs > 0 AND website_docs > 0;
"
```

---

### Debug: Website Not Found

```
The crawler can't find a company's website. Debug for ticker ABC:

1. Check what ListCorp shows:
   - Visit https://www.listcorp.com/asx/abc manually
   - Look for "Website" link in company info

2. Check our database:
   sqlite3 data/esg_intel.db "SELECT ticker, name, website FROM companies WHERE ticker = 'ABC';"

3. Try to find website manually and update:
   sqlite3 data/esg_intel.db "UPDATE companies SET website = 'example.com' WHERE ticker = 'ABC';"
```

---

### Debug: No Documents Found on Website

```
The crawler found the website but no ESG documents. Debug:

1. Check if sitemap exists:
   curl -s https://example.com/robots.txt | grep -i sitemap
   curl -s https://example.com/sitemap.xml | head -50

2. Check common sustainability URLs manually:
   - https://example.com/sustainability
   - https://example.com/investors
   - https://example.com/esg
   - https://example.com/about/sustainability

3. Show me what URLs the crawler found and filtered
```

---

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

---

### Build Milestone 6: Dashboard

```
I'm ready for Milestone 6. Create the Streamlit dashboard.

Please create app/dashboard.py with:
1. Filterable prospect list (by priority tier, sector, score)
2. Company detail view showing all ESG data
3. Progress charts (emissions/RE% over multiple years)
4. Source document links (both ListCorp and company website)
5. CSV export button for filtered results

Test with: streamlit run app/dashboard.py
```

---

### Install Dependencies

```
Install all required packages:

pip install -r requirements.txt
playwright install chromium

Verify key packages:
python -c "from docling.document_converter import DocumentConverter; print('Docling OK')"
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
python -c "import anthropic; print('Anthropic OK')"
```

---

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # Add your ANTHROPIC_API_KEY

# Run pipeline
python scripts/01_import_companies.py          # Import companies
python scripts/02_find_esg_docs.py --limit 50  # ListCorp method
python scripts/02b_find_via_website.py --limit 50  # Website crawler (NEW)
python scripts/03_extract_text.py              # Extract with Docling
python scripts/04_analyze_with_ai.py           # AI analysis
python scripts/05_score_prospects.py           # Score prospects
streamlit run app/dashboard.py                 # View dashboard
```

## Project Structure

```
esg-intelligence/
├── config/settings.py
├── data/
│   ├── companies.csv         # 2,239 ASX companies
│   └── esg_intel.db          # SQLite database
├── src/
│   ├── database/schema.py
│   ├── scraper/
│   │   ├── listcorp_news.py      # Milestone 2a: ASX announcements
│   │   ├── company_website.py    # Milestone 2b: Website crawler (NEW)
│   │   └── text_extractor.py     # Milestone 3: Docling extraction
│   └── analyzer/
│       ├── llm_extractor.py      # Milestone 4: Claude AI
│       └── scorer.py             # Milestone 5: Prospect scoring
├── scripts/
│   ├── 01_import_companies.py
│   ├── 02_find_esg_docs.py       # ListCorp scraper
│   ├── 02b_find_via_website.py   # Website crawler (NEW)
│   ├── 03_extract_text.py
│   ├── 04_analyze_with_ai.py
│   └── 05_score_prospects.py
└── app/dashboard.py              # Milestone 6: Streamlit
```

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Language | Python 3.11+ | |
| Database | SQLite | Single file, zero config |
| Web Scraping | Playwright + stealth | Handles JS-rendered pages |
| Document Extraction | **Docling** (IBM) | 97.9% table accuracy! |
| AI Analysis | Claude API | Structured ESG extraction |
| Dashboard | Streamlit | Interactive visualization |

## Database Schema

```sql
-- Companies with website column
companies (
    id, ticker, name, sector, industry, market_cap,
    website TEXT  -- NEW: company domain (e.g., "xero.com")
)

-- Documents with source tracking
documents (
    id, company_id, title, url, document_type,
    source TEXT DEFAULT 'listcorp',  -- NEW: 'listcorp' or 'website'
    text_content, extraction_status, char_count, table_count
)

-- ESG data extracted by AI
esg_data (id, company_id, document_id, fiscal_year, ...)

-- Prospect scores
prospect_scores (id, company_id, total_score, priority_tier, ...)
```

## Resources

- Blueprint: `blueprint.md`
- Companies CSV: `data/companies.csv`
- Database: `data/esg_intel.db`
