# Energy Intelligence - Iteration 2

## Goal
Find **raw energy/emissions metrics** and **target vs actual gaps** to identify companies that need to accelerate ESG investment.

### What We Care About
- Scope 1, 2, 3 emissions (actual numbers)
- Renewable energy % (current vs target)
- Net zero commitment year vs progress
- Investment pledged vs spent (e.g., "$500M pledged, $78M spent in 2025")
- Carbon offsets purchased

---

## The Simple Discovery Method ✅

Instead of complex crawlers, we just **Google it**:
- `"{company} sustainability report 2024"` → PDF reports
- `"{company} ESG databook 2024"` → Excel metrics
- `"{company} annual report 2024"` → Context

This is 10x simpler than sitemap crawling.

---

## Current Status

### ✅ Step 1: Report Links Collected
File: `data/report_links.json`

**Top 10 ASX Companies by Market Cap:**

| # | Ticker | Company | Excel Files | PDF Files | Years |
|---|--------|---------|-------------|-----------|-------|
| 1 | CBA | Commonwealth Bank | 4 xlsx | 3 pdf | 2022-2025 |
| 2 | BHP | BHP Group | 4 xlsx | 4 pdf | 2022-2025 |
| 3 | NAB | National Australia Bank | 3 xlsx | 4 pdf | 2023-2025 |
| 4 | CSL | CSL Limited | 0 | 3 pdf | 2022-2024 |
| 5 | WBC | Westpac Banking | 4 xlsx | 2 pdf | 2022-2025 |
| 6 | ANZ | ANZ Group | 2 xlsx | 4 pdf | 2023-2024 |
| 7 | MQG | Macquarie Group | 0 | 5 pdf | 2023-2025 |
| 8 | WES | Wesfarmers | 0 (web) | 4 pdf | 2022-2024 |
| 9 | GMG | Goodman Group | 0 | 4 pdf | 2023-2024 |
| 10 | FMG | Fortescue | 2 xlsx | 5 pdf | 2022-2025 |

**Totals: 19 Excel databooks + 38 PDF reports = 57 files**

### ❌ Step 2: URL Verification FAILED
**CRITICAL ISSUE:** URLs were NOT properly verified before being added to report_links.json.

**Verification Results (2025-12-02):**
- ✅ **32 URLs work** (57%)
- ❌ **16 URLs broken** (29%) - 404 Not Found or 403 Forbidden
- ⏱️ **8 URLs timeout** (14%) - All BHP URLs have server issues

**Broken URLs by Company:**
- **CBA:** 1/7 broken (2022 databook - 404)
- **BHP:** 8/8 timeout (all URLs have HTTP/2 stream errors)
- **NAB:** 0/7 broken ✅
- **CSL:** 1/3 broken (2022 annual report - 404)
- **WBC:** 3/6 broken (2025, 2024, 2022 databooks - 404)
- **ANZ:** 6/6 broken (all URLs return 403 Forbidden)
- **MQG:** 0/5 broken ✅
- **WES:** 0/4 broken ✅
- **GMG:** 1/3 broken (2023 sustainability report - 403)
- **FMG:** 4/7 broken (databooks and some PDFs - 403)

**Root Cause:** Initial URL collection did not include actual HTTP verification step. URLs were assumed to be valid based on website navigation, but many were moved, restricted, or never existed at those paths.

**Action Required:** Need to find correct URLs for broken links or remove them from dataset.

### ✅ Step 3: Download Scripts Created
File: `scripts/download_reports.py`

```bash
# Preview what will be downloaded
python scripts/download_reports.py --dry-run

# Download all files
python scripts/download_reports.py

# Download single company
python scripts/download_reports.py --ticker BHP

# Download only Excel files
python scripts/download_reports.py --type xlsx

# Skip already downloaded
python scripts/download_reports.py --skip-existing
```

---

## Pipeline Steps

### Step 4: Extract Data from Excel (NEXT)
```bash
python scripts/extract_excel_metrics.py
```
- Read xlsx files with pandas
- Extract sheets: Emissions, Energy, Targets
- Store raw metrics in `esg_metrics` table

### Step 5: Extract Data from PDFs
```bash
python scripts/extract_pdf_metrics.py
```
- Use Docling for table extraction
- Use Claude AI for unstructured text
- Focus on: commitments, targets, spending

### Step 6: Generate Gap Analysis
```bash
python scripts/analyze_gaps.py
```
- Calculate: target vs actual
- Rank companies by ESG investment opportunity
- Output: prioritized list for sales

---

## Database Schema

```sql
-- Existing tables
companies (id, ticker, name, sector, market_cap)
documents (id, company_id, title, url, type, year, local_path, downloaded_at)

-- New: raw extracted metrics
CREATE TABLE esg_metrics (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    document_id INTEGER,
    fiscal_year INTEGER,
    
    -- Emissions (tCO2e)
    scope_1_emissions REAL,
    scope_2_emissions REAL,
    scope_3_emissions REAL,
    
    -- Energy
    total_energy_gj REAL,
    renewable_energy_pct REAL,
    renewable_energy_target_pct REAL,
    renewable_target_year INTEGER,
    
    -- Net Zero
    net_zero_target_year INTEGER,
    emissions_reduction_target_pct REAL,
    
    -- Investment
    sustainability_investment_pledged REAL,
    sustainability_investment_spent REAL,
    
    -- Certifications
    sbti_status TEXT,  -- 'committed', 'targets_set', 'validated'
    re100_member BOOLEAN,
    
    -- Metadata
    data_source TEXT,  -- 'excel_databook' or 'pdf_extraction'
    extraction_confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

---

## Simple SOP

```
1. Claude searches for report links → saved to report_links.json ✅
2. Script downloads files → data/excel/ and data/pdfs/ ⏳
3. Script extracts Excel metrics → esg_metrics table ⏳
4. AI extracts PDF metrics → esg_metrics table ⏳
5. Script analyzes gaps → ranked company list ⏳
```

---

## Priority Excel Files (Process First)

These contain the raw structured metrics we need:

| Company | File | Key Sheets |
|---------|------|------------|
| BHP | esgstandardsanddatabook2024.xlsx | GHG Emissions, Energy, Targets |
| CBA | 2024-Sustainability-Performance-Metrics.xlsx | Environment, Emissions |
| NAB | 2024-sustainability-data-pack.xlsx | Climate, Environment |
| WBC | 2024-sustainability-index-and-datasheet.xlsx | Environment |
| ANZ | 2024-esg-data-and-frameworks-pack.xlsx | Climate Data |
| FMG | fy24-esg-databook.xlsx | Emissions, Energy |

---

## Key Metrics Mapping

What we extract from each company:

| Metric | CBA Column | BHP Column | NAB Column |
|--------|------------|------------|------------|
| Scope 1 | Scope 1 emissions | GHG Scope 1 | Scope 1 GHG |
| Scope 2 | Scope 2 emissions | GHG Scope 2 | Scope 2 GHG |
| Scope 3 | Scope 3 emissions | GHG Scope 3 | Scope 3 GHG |
| Renewable % | Renewable energy % | Renewable electricity % | Renewable % |
| Net Zero | Net zero target | Net zero year | Net zero year |

---

## Next Actions

1. **Run download script** to get all files locally
2. **Create Excel parser** for each company's format
3. **Store metrics** in database
4. **Calculate gaps** (target - actual)
5. **Generate report** for sales prioritization
