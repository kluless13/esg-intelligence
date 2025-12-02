# URL Verification Report - Energy Intelligence

## Date: December 2, 2025
## Status: ❌ FAILED - Only 57% of URLs are accessible

## Summary

**CRITICAL ISSUE:** Verified all URLs in `data/report_links.json` and found that **43% of URLs are broken or inaccessible**.

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Working (200 OK) | 32 | 57% |
| ❌ Broken (404/403) | 16 | 29% |
| ⏱️ Timeout | 8 | 14% |
| **Total URLs** | **56** | **100%** |

---

## Verification Results by Company

| Company | Ticker | Working | Broken | Success Rate | Status |
|---------|--------|---------|--------|--------------|--------|
| NAB | NAB | 7/7 | 0 | 100% | ✅ **PERFECT** |
| Macquarie | MQG | 5/5 | 0 | 100% | ✅ **PERFECT** |
| Wesfarmers | WES | 4/4 | 0 | 100% | ✅ **PERFECT** |
| Commonwealth Bank | CBA | 6/7 | 1 | 86% | ⚠️ **GOOD** |
| CSL | CSL | 2/3 | 1 | 67% | ⚠️ **ACCEPTABLE** |
| Goodman Group | GMG | 2/3 | 1 | 67% | ⚠️ **ACCEPTABLE** |
| Fortescue | FMG | 3/7 | 4 | 43% | ❌ **POOR** |
| Westpac | WBC | 2/6 | 3 | 33% | ❌ **POOR** |
| ANZ | ANZ | 0/6 | 6 | 0% | ❌ **FAILED** |
| BHP Group | BHP | 0/8 | 8 | 0% | ❌ **FAILED** |

### Detailed Breakdown

#### ✅ CBA - Commonwealth Bank (6/7 working, 86%)
- ✅ 2025 Half Year Sustainability Metrics (xlsx)
- ✅ 2024 Sustainability Metrics (xlsx)
- ✅ 2023 Sustainability Metrics (xlsx)
- ❌ 2022 Sustainability Metrics (xlsx) - **404**
- ✅ 2024 Climate Report (pdf)
- ✅ 2024 Sustainability Reporting (pdf)
- ✅ 2023 Sustainability Reporting (pdf)

#### ❌ BHP - BHP Group (0/8 working, 0%)
**ALL URLS TIMEOUT** - HTTP/2 stream errors on all files
- ⏱️ All 4 ESG Databooks (xlsx) - 2022-2025
- ⏱️ All 4 Annual/Climate Reports (pdf)

#### ✅ NAB - National Australia Bank (7/7 working, 100%)
**PERFECT - ALL URLS WORK**
- ✅ All 3 Sustainability Data Packs (xlsx) - 2023-2025
- ✅ All 4 Reports (pdf)

#### ⚠️ CSL - CSL Limited (2/3 working, 67%)
- ✅ 2024 Annual Report (pdf)
- ✅ 2023 Annual Report (pdf)
- ❌ 2022 Annual Report (pdf) - **404**

#### ❌ WBC - Westpac (2/6 working, 33%)
- ❌ 2025 Sustainability Datasheet (xlsx) - **404**
- ❌ 2024 Sustainability Datasheet (xlsx) - **404**
- ✅ 2023 Sustainability Datasheet (xlsx)
- ❌ 2022 Sustainability Datasheet (xlsx) - **404**
- ✅ 2024 Climate Report (pdf)
- ✅ 2023 Climate Report (pdf)

#### ❌ ANZ - ANZ Group (0/6 working, 0%)
**ALL URLS BLOCKED** - 403 Forbidden on all files
- ❌ 2024 ESG Data Pack (xlsx) - **403**
- ❌ 2023 ESG Data Pack (xlsx) - **403**
- ❌ All 4 PDFs - **403**

#### ✅ MQG - Macquarie (5/5 working, 100%)
**PERFECT - ALL URLS WORK**
- ✅ All 5 reports accessible

#### ✅ WES - Wesfarmers (4/4 working, 100%)
**PERFECT - ALL URLS WORK**
- ✅ All 4 annual reports accessible

#### ⚠️ GMG - Goodman Group (2/3 working, 67%)
- ✅ 2024 Annual Report (pdf)
- ✅ 2023 Annual Report (pdf)
- ❌ 2023 Sustainability Report (pdf) - **403**

#### ❌ FMG - Fortescue (3/7 working, 43%)
- ❌ FY25 ESG Databook (xlsx) - **403**
- ❌ FY24 ESG Databook (xlsx) - **403**
- ❌ FY25 Climate Plan (pdf) - **403**
- ✅ FY24 Sustainability Report (pdf)
- ✅ FY24 Annual Report (pdf)
- ❌ FY23 Annual Report (pdf) - **403**
- ✅ FY22 Climate Report (pdf)

---

## Root Cause Analysis

### Why URLs Failed

1. **404 Errors (10 URLs) - Files moved/deleted:**
   - Companies reorganized their websites
   - Old reports were archived or removed
   - URL patterns changed between years
   - Examples: CBA 2022, WBC 2024/2025/2022, CSL 2022

2. **403 Errors (14 URLs) - Access restricted:**
   - Files require session cookies or authentication
   - Geographic restrictions possible
   - Anti-scraping protection
   - Examples: All ANZ files, FMG databooks, GMG 2023

3. **Timeouts (8 URLs) - Server issues:**
   - BHP's entire domain has HTTP/2 configuration issues
   - Possible CDN or firewall blocking automated requests
   - All 8 BHP URLs timeout consistently

### What Went Wrong

The initial URL collection process **did not include HTTP verification**. URLs were:
- Found through manual website navigation
- Copied from browser address bars
- Assumed to be publicly accessible
- **Never tested programmatically** with HTTP HEAD/GET requests

This is a critical quality control failure that undermines the entire data collection process.

---

## What We Can Download Today

**Immediately accessible:** 32 files (57% of dataset)

**By company (ranked by accessibility):**
1. ✅ NAB: 7 files (100% coverage) - **PERFECT**
2. ✅ MQG: 5 files (100% coverage) - **PERFECT**
3. ✅ WES: 4 files (100% coverage) - **PERFECT**
4. ⚠️ CBA: 6 files (86% coverage) - **GOOD**
5. ⚠️ CSL: 2 files (67% coverage) - **ACCEPTABLE**
6. ⚠️ GMG: 2 files (67% coverage) - **ACCEPTABLE**
7. ❌ FMG: 3 files (43% coverage) - **LIMITED**
8. ❌ WBC: 2 files (33% coverage) - **VERY LIMITED**
9. ❌ ANZ: 0 files (0% coverage) - **NO ACCESS**
10. ❌ BHP: 0 files (0% coverage) - **NO ACCESS**

**Critical gap:** Missing all ANZ and BHP data, which are major ASX companies (#2 and #6 by market cap).

---

## File Types & Download Behavior

| Type | Extension | Behavior | Handling |
|------|-----------|----------|----------|
| Excel | `.xlsx` | Auto-downloads | Save directly |
| PDF | `.pdf` | Opens in browser OR downloads | Request with `Accept: application/pdf` header |
| Web | `.html` | Opens page | Needs Playwright scraping |

---

## Immediate Actions Required

### 1. Download Working URLs (Priority 1)
Use `scripts/download_reports_simple.py` to download the 32 accessible files:
```bash
python scripts/download_reports_simple.py --skip-existing
```

### 2. Fix Broken URLs (Priority 2)

**BHP (8 URLs, all timeout):**
- Visit https://www.bhp.com/investors/annual-reporting directly in browser
- Manually find correct URLs for 2022-2025 reports
- Test that they work with simple HTTP requests
- Update report_links.json

**ANZ (6 URLs, all 403):**
- Check if ANZ requires authentication for reports
- Try accessing through investor relations portal
- May need to use Playwright with cookies/session
- Alternative: Find reports on ASX announcements platform

**Westpac (3 URLs, 404):**
- Find correct URLs for 2024, 2025, 2022 datasheets
- Check URL pattern changes
- Update report_links.json

**FMG (4 URLs, 403):**
- Visit https://www.fortescue.com/en/sustainability
- Check if databooks moved to different location
- Update URLs in report_links.json

### 3. Process Improvements

**Implement URL verification in workflow:**
```python
# Always verify before adding to dataset
def verify_url(url):
    response = requests.head(url, timeout=10)
    return response.status_code == 200

# Add verification timestamp to report_links.json
{
    "url": "https://...",
    "verified_at": "2025-12-02",
    "status": "ok"
}
```

**Set up monitoring:**
- Re-verify URLs monthly
- Alert when URLs break
- Track URL changes over time

---

## Conclusion

**The URL verification has failed** - only 57% of URLs are accessible. This is a significant quality control issue that occurred because URLs were not programmatically verified during the initial collection phase.

### Current State:
- ✅ **Can download:** 32 files from 7 companies (NAB, MQG, WES, CBA, CSL, GMG, FMG)
- ❌ **Cannot download:** 24 files from 5 companies (BHP, ANZ, WBC, FMG, others)
- ⏳ **Action required:** Find correct URLs for broken links or remove them from dataset

### Lessons Learned:
1. **Always verify URLs programmatically** before adding to dataset
2. **Test with actual HTTP requests**, not just browser navigation
3. **Include verification timestamp** in metadata
4. **Re-verify periodically** as URLs can break over time

### Next Steps:
1. Download the 32 working files immediately
2. Manually fix the 24 broken URLs
3. Re-run verification
4. Proceed with data extraction only after all URLs are confirmed working
