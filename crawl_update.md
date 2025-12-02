# ESG Document Crawler - Simplified Strategy

## Core Insight

The ListCorp company page has a "Company Resources" section with links like:

- Investor Relations → Company's investor page
- Corporate Governance → Company's governance/ESG section
- Directors → Board info

The "Corporate Governance" link takes us DIRECTLY to the company's ESG-related section on their actual website.

Example HTML from ListCorp page:

```html
<li class="CompanyPage2CompanyPageResourceLinks__item">
  <a href="https://vaultminerals.com/about/corporate-governance" target="_blank" rel="noopener" class="lcGreyLink CompanyPage2CompanyPageResourceLinks__anchor">
    Corporate Governance
  </a>
</li>
```

## Simplified Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Read from CSV                                       │
├─────────────────────────────────────────────────────────────┤
│ Input: data/companies.csv                                   │
│ Get: ticker, company_name, listcorp_url                     │
│ Example: CBA, Commonwealth Bank, https://listcorp.com/...   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Visit ListCorp page, extract Company Resources      │
├─────────────────────────────────────────────────────────────┤
│ Use Playwright to load ListCorp company page                │
│ Find: CompanyPage2CompanyPageResourceLinks__anchor links    │
│ Extract URLs for:                                           │
│   - Corporate Governance (PRIMARY - usually has ESG links)  │
│   - Investor Relations (SECONDARY - has annual reports)     │
│ Save company website domain to DB                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Crawl from Corporate Governance URL                 │
├─────────────────────────────────────────────────────────────┤
│ Starting point: Corporate Governance URL (e.g.,             │
│   https://vaultminerals.com/about/corporate-governance)     │
│                                                             │
│ Strategy (in order):                                        │
│ 1. Try sitemap.xml from domain root                         │
│ 2. If sitemap insufficient, BFS crawl from governance page  │
│ 3. Follow links to /sustainability, /esg, /environment      │
│ 4. Look for PDF and Excel links on each page                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Collect Documents                                   │
├─────────────────────────────────────────────────────────────┤
│ Target file types:                                          │
│ - PDF: Annual reports, sustainability reports, TCFD         │
│ - Excel (.xlsx, .xls): ESG databooks, emissions data        │
│ - CSV: Performance metrics                                  │
│                                                             │
│ Filter by:                                                  │
│ - Keywords: sustainability, esg, climate, emissions, etc.   │
│ - Year: Recent 3 years (2023, 2024, 2025)                   │
│                                                             │
│ Save to database with:                                      │
│ - company_id, document_url, title, document_type            │
│ - source_page (where we found it)                           │
│ - file_type (pdf/excel/csv)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Why This Is Better

| Old Approach | New Approach |
|--------------|--------------|
| Guess company URL from ticker | Get exact URL from ListCorp |
| Start from homepage | Start from governance/ESG section |
| Crawl entire site | Focused crawl from relevant section |
| Miss many companies | High success rate |

## Key Implementation Notes

1. ListCorp selector for Company Resources:

```python
# CSS selector
"a.CompanyPage2CompanyPageResourceLinks__anchor"

# Or find by text
"Corporate Governance" -> href attribute
"Investor Relations" -> href attribute
```

2. Priority order for starting URLs:
   - Corporate Governance (best for ESG)
   - Investor Relations (good for annual reports)
   - Sustainability (if listed)

3. Document priorities:
   - ESG Databooks (Excel) → Raw metrics we need
   - Sustainability Reports (PDF) → Commitments
   - Annual Reports (PDF) → Context

## Files to Modify

1. `src/scraper/company_website.py` - Add ListCorp extraction step
2. `scripts/02b_find_via_website.py` - Update to use new flow
3. `src/database/schema.py` - Ensure document_url field exists

## Usage

```bash
# Single company
python scripts/02b_find_via_website.py --ticker VAU

# Batch (top 50 by market cap)
python scripts/02b_find_via_website.py --limit 50

# All companies
python scripts/02b_find_via_website.py
```


