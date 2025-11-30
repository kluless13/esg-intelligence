# Current Issues - ESG Intelligence Website Crawler

**Date:** 2025-11-29

## 🎯 Overview

The website crawler (Milestone 2b) has been partially implemented with mixed results. Some companies work well, others fail completely. This document tracks what works, what doesn't, and what needs to be fixed.

---

## ✅ What Works

### Successful Companies

**1. Xero (XRO) - xero.com**
- ✅ Sitemap discovery: **19,053 URLs** found
- ✅ ESG filtering: **772 relevant URLs**
- ✅ Reports found: **8 documents**
- ✅ Saved to database: **3 reports** (from website source)
- Sample reports:
  - "Read the Xero Sustainability Report 2025 (PDF)"
  - "Continuous Disclosure Policy"
  - Cross-domain PDFs supported (brandfolder.xero.com)

**2. BHP - bhp.com**
- ✅ Sitemap discovery: **13,931 URLs** found (English + Spanish)
- ✅ ESG filtering: **1,772 relevant URLs**
- ⚠️ Reports found: **0 documents** (ISSUE - see below)
- **This proves sitemap fix works!** - Previously completely blocked (403 errors)
- ultimate-sitemap-parser successfully handles this complex site

**3. AMP - amp.com.au**
- ✅ Sitemap discovery: **1,394 URLs** found
- ✅ ESG filtering: **21 relevant URLs**
- ✅ Reports found: **100 documents**
- ✅ Saved to database: **99 reports**
- Sample reports include annual reports from 2013-2024, remuneration disclosures

### What Technology Works

**Sitemap Discovery (ultimate-sitemap-parser):**
- ✅ Automatic robots.txt parsing
- ✅ Gzipped sitemap support (.xml.gz)
- ✅ Nested sitemap indexes (unlimited depth)
- ✅ Proper User-Agent headers (prevents 403 blocks)
- ✅ Handles 10,000+ URLs efficiently
- ✅ Multi-language sites (BHP: English + Spanish)

**Database Integration:**
- ✅ Deduplication working
- ✅ Source tracking (listcorp vs website)
- ✅ Financial year extraction from titles
- ✅ Document type categorization

---

## ❌ What Doesn't Work

### Failed Companies

**1. ANZ - anz.com**
- ⚠️ Sitemap discovery: **Only 3 URLs** found
- ❌ ESG filtering: **0 relevant URLs**
- ❌ Reports found: **0 documents**
- **ROOT CAUSE:** ANZ's sitemap.xml only contains 3 pages (homepage variants)
- **KNOWN FACT:** ANZ has ESG content in footer and /shareholder sections
- **ISSUE:** Sitemap is incomplete - need fallback to crawling

**Sitemap content (anz.com/sitemap.xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url><loc>https://anz.com</loc></url>
  <url><loc>https://anz.com/personal</loc></url>
  <url><loc>https://anz.com/business</loc></url>
</urlset>
```

**2. BHP - bhp.com**
- ✅ Sitemap works (13,931 URLs, 1,772 ESG URLs)
- ❌ **0 reports extracted** despite 1,772 ESG pages checked
- **ROOT CAUSE:** PDF extraction filter too restrictive or different URL patterns

---

## 🔧 Critical Issues

### Issue 1: Incomplete Sitemaps (ANZ Problem)

**Problem:**
- Many companies have minimal sitemaps that don't list all pages
- ANZ sitemap only has 3 URLs, but we know they have ESG content
- Crawler relies 100% on sitemap - no fallback

**Current Behavior:**
```
STEP B: Discovering URLs on website...
  ✓ Found 3 URLs from sitemaps
STEP C: Filtering for ESG-related URLs...
  ✓ Filtered to 0 ESG-related URLs
⚠ No ESG-related URLs found for anz.com
```

**Solution Needed:**
- When sitemap returns < 10 URLs, fallback to `crawl_common_paths()`
- Currently `crawl_common_paths()` exists but is **NEVER CALLED** as fallback
- Need to implement: "If sitemap finds < 10 URLs OR 0 ESG URLs, try crawling"

**Code Location:** `src/scraper/company_website.py:366-371`
```python
# Current code:
urls = discover_urls_from_sitemap(domain)
if not urls:
    logger.info("No sitemap found, crawling common paths...")
    urls = crawl_common_paths(domain)

# ISSUE: This only runs if sitemap returns ZERO urls
# ANZ returns 3 URLs, so fallback never triggers!
```

**Fix Required:**
```python
urls = discover_urls_from_sitemap(domain)
esg_urls = filter_esg_urls(urls)

# Fallback if sitemap insufficient
if len(urls) < 10 or len(esg_urls) == 0:
    logger.info("Sitemap insufficient, crawling common paths...")
    crawl_urls = crawl_common_paths(domain)
    urls.extend(crawl_urls)
    esg_urls = filter_esg_urls(urls)
```

### Issue 2: PDF Extraction Fails on BHP

**Problem:**
- BHP has 1,772 ESG-related URLs
- Script checked all 50 top URLs (configurable limit)
- Found **0 reports**
- This suggests PDF extraction logic is missing reports

**Possible Causes:**
1. **PDF links use different patterns:**
   - Maybe PDFs are behind "Download" buttons with JavaScript
   - Maybe PDFs are in iframes
   - Maybe PDFs use query parameters: `/download?file=report.pdf`

2. **Filter too restrictive:**
   - Current filter requires ESG keywords in **both** URL **and** title
   - BHP might use generic filenames: `/documents/2024-annual-report.pdf`

3. **Playwright timing issues:**
   - Page might not be fully loaded
   - Dynamic content not rendered

**Code Location:** `src/scraper/company_website.py:265-334` (`extract_report_links()`)

**Current Filter:**
```python
# Only saves if ESG keyword in title OR URL
if any(keyword in title_lower or keyword in url_lower for keyword in [
    'sustainability', 'esg', 'climate', 'annual', 'report', ...
]):
```

**Investigation Needed:**
- Manually check BHP ESG pages to see PDF link patterns
- Add debug logging to show what links are found vs filtered out
- Check if we need to click "Download" buttons

### Issue 3: Excel File Collection Not Implemented

**Problem:**
- Code checks for `.xlsx` files in URLs
- But many companies use `.xls` (older Excel format)
- Also missing: `.csv`, `.xlsm` (Excel with macros)

**Current Code:**
```python
if full_url.lower().endswith('.pdf') or full_url.lower().endswith('.xlsx') or '.pdf' in full_url.lower():
```

**Missing Formats:**
- `.xls` - Old Excel format (common in archived reports)
- `.csv` - CSV data files
- `.xlsm` - Excel with macros
- `.ods` - OpenDocument Spreadsheet

**Fix Required:**
```python
# Check for all document formats
doc_extensions = ['.pdf', '.xlsx', '.xls', '.xlsm', '.csv', '.ods']
is_document = any(ext in full_url.lower() for ext in doc_extensions)

if is_document:
    # Determine type
    if '.pdf' in full_url.lower():
        doc_type = 'pdf'
    elif any(ext in full_url.lower() for ext in ['.xlsx', '.xls', '.xlsm']):
        doc_type = 'excel'
    elif '.csv' in full_url.lower():
        doc_type = 'csv'
    else:
        doc_type = 'other'
```

### Issue 4: Source URL Storage Bug (Fixed but Document)

**Problem:** (FIXED on 2025-11-29)
- Multiple PDFs from same source page caused UNIQUE constraint violation
- Database schema has: `UNIQUE(company_id, listcorp_news_url)`
- When 10 PDFs came from same page, 2nd+ failed to insert

**Fix Applied:**
- Now using report URL as unique identifier instead of source page
- Stores PDF URL in `listcorp_news_url` column (even though it's from website)
- This is a workaround - ideally we'd redesign the schema

**Better Solution (Future):**
- Add `website_source_page` column to documents table
- Keep `listcorp_news_url` for ListCorp only
- Use `pdf_url` as primary unique identifier for website-sourced docs

---

## 📊 Test Results Summary

| Company | Sitemap URLs | ESG URLs | Reports Found | Reports Saved | Status |
|---------|-------------|----------|---------------|---------------|--------|
| XRO (Xero) | 19,053 | 772 | 8 | 3 | ✅ Working |
| AMP | 1,394 | 21 | 100 | 99 | ✅ Working |
| BHP | 13,931 | 1,772 | 0 | 0 | ⚠️ Sitemap OK, PDF extraction fails |
| ANZ | 3 | 0 | 0 | 0 | ❌ Sitemap incomplete |
| CBA | (processing) | - | - | - | 🔄 Testing |

**Success Rate:** 2/4 companies working (50%)

---

## 🔍 Investigation Needed

### 1. ANZ Manual Check
**Task:** Manually visit ANZ website to confirm ESG content exists
- Check: https://anz.com/shareholders
- Check: https://anz.com/about-us/esg
- Check: https://anz.com/sustainability
- Document actual URLs where reports are located

### 2. BHP Manual Check
**Task:** Visit BHP ESG pages to see PDF link patterns
- Pick 5 URLs from the 1,772 ESG URLs found
- Inspect HTML to see how PDFs are linked
- Check if PDFs are behind JavaScript or download buttons
- Document findings

### 3. Common Path Crawler Test
**Task:** Test if `crawl_common_paths()` actually finds ANZ content
```bash
python -c "
from src.scraper.company_website import crawl_common_paths
urls = crawl_common_paths('anz.com')
print(f'Found {len(urls)} URLs')
for url in urls[:10]:
    print(f'  - {url}')
"
```

---

## 🎯 Priority Fixes

### High Priority

1. **Fix ANZ-style sites with incomplete sitemaps**
   - Implement sitemap insufficiency detection
   - Auto-fallback to crawl_common_paths()
   - Test on ANZ

2. **Fix BHP PDF extraction**
   - Add debug logging to extract_report_links()
   - Manually inspect BHP ESG pages
   - Adjust filter or add JavaScript handling

3. **Add Excel file support**
   - Support .xls, .xlsm, .csv formats
   - Update filter logic
   - Test on companies that publish Excel databooks

### Medium Priority

4. **Improve common paths list**
   - Add more common ESG URL patterns
   - Check other ASX200 companies to find patterns
   - Current list might be missing /shareholders, /investor-centre

5. **Better error reporting**
   - Log which PDFs were found but filtered out
   - Show sample URLs that failed filter
   - Help debug why BHP found 0 reports

### Low Priority

6. **Schema redesign**
   - Separate website source tracking from ListCorp
   - Add proper foreign keys and constraints
   - Migration script for existing data

---

## 📝 Next Steps

1. **Immediate:** Debug ANZ sitemap issue
   - Run crawl_common_paths() manually
   - Check if ANZ actually has ESG content on their site
   - Fix fallback logic

2. **Today:** Fix BHP PDF extraction
   - Add verbose logging to see what's being filtered
   - Manually check 3-5 BHP ESG pages
   - Adjust extraction logic

3. **This Week:** Process all 10 companies
   - Fix issues found above
   - Run crawler on all 10 major companies
   - Document success rate and patterns

4. **Before scale-up:** Ensure 80%+ success rate
   - Don't process 2,000 companies until these issues fixed
   - Test on 20-30 companies first
   - Achieve 80%+ discovery rate

---

## 🔗 Related Files

- **Main implementation:** `src/scraper/company_website.py`
- **Crawler script:** `scripts/02b_find_via_website.py`
- **Status doc:** `MILESTONE_2B_STATUS.md`
- **Database:** `data/esg_intel.db`

---

## 💡 Questions to Answer

1. Should we crawl **ALL** pages if sitemap insufficient, or just common paths?
2. What's the acceptable timeout for crawling? (ANZ might have 1000s of pages)
3. Should we add JavaScript rendering for all sites, or only when needed?
4. Do we need to handle authentication/login for investor-only sections?
5. Should we download PDFs locally or just store URLs?
