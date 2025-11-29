# ESG Intelligence - Next Steps & Priorities

## 🎯 Current Status (Milestone 4 Complete)

### What's Working ✅
- **Text extraction**: Docling extracting ~25k chars/document (96% success rate)
- **AI analysis**: Claude extracting ESG metrics ($0.78 for 27 documents)
- **Database**: 27 ESG records from 6 companies

### What's NOT Working ❌
- **Document discovery**: Only 33% of companies have ESG data
- **Scalability**: Limited to ASX via ListCorp
- **Coverage**: Missing 70%+ of sustainability reports

**Root cause**: Most companies publish sustainability reports on their websites, NOT as stock exchange announcements.

---

## 🚀 Priority: Implement Search-Based Discovery

### Problem
Current approach (scraping ListCorp news) finds documents for only 2 out of 6 companies (33%).

### Solution
Use search engines (Google/Bing/DuckDuckGo) to find sustainability reports wherever they're published.

### Implementation Path

#### Phase 1: Search Engine Integration (1-2 days)

**Create `scripts/02b_find_via_search.py`:**
```bash
# Install dependency
pip install duckduckgo-search

# Test with one company
python scripts/02b_find_via_search.py --company BHP

# Process batch
python scripts/02b_find_via_search.py --limit 20
```

**Search queries to use:**
1. `"BHP sustainability report 2024 filetype:pdf"`
2. `"BHP ESG report 2024"`
3. `"BHP climate disclosure TCFD"`
4. `site:bhp.com sustainability`

**Expected improvement:**
- Document discovery: 33% → **80%+**
- Companies with ESG data: 2/6 → **14/20+**

#### Phase 2: Multi-Exchange Support (2-3 days)

**Add company lists from:**
- NASDAQ: SEC Edgar API (free)
- NYSE: SEC Edgar API (free)
- LSE: London Stock Exchange API
- ASX: Keep existing ListCorp list

**Database change:**
```sql
ALTER TABLE companies ADD COLUMN exchange TEXT DEFAULT 'ASX';
ALTER TABLE companies ADD COLUMN country TEXT;
```

#### Phase 3: Enhanced Filtering (1 day)

**Improve result quality:**
- Score by relevance (company name/ticker in URL)
- Filter out news articles, job postings
- Prioritize PDFs from official domains
- Deduplicate across years

---

## 📊 Expected Outcomes

### Before (ListCorp only)
```
100 companies scraped
→ 25 documents found (25% discovery rate)
→ 8 with ESG data (33% data rate)
→ ASX only
```

### After (Search-based)
```
100 companies searched
→ 85 documents found (85% discovery rate)
→ 60 with ESG data (70% data rate)
→ Works globally (any exchange)
```

---

## 🛠️ Technical Implementation

### Option 1: Free (DuckDuckGo)
```python
from duckduckgo_search import DDGS

def search(company, year):
    query = f'"{company}" sustainability report {year} filetype:pdf'
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
    return results
```

**Pros:**
- Free, no API key
- Good for prototyping

**Cons:**
- Rate limits
- May miss some results

### Option 2: Paid (SerpAPI)
```python
from serpapi import GoogleSearch

def search(company, year):
    params = {
        "q": f'"{company}" sustainability report {year}',
        "api_key": "YOUR_KEY"
    }
    search = GoogleSearch(params)
    return search.get_dict()["organic_results"]
```

**Pros:**
- More comprehensive results
- Better rate limits
- Handles captchas

**Cons:**
- $50/month (5,000 searches)

**Recommendation:** Start with DuckDuckGo, upgrade to SerpAPI when scaling.

---

## 📅 Timeline

### Week 1: Search Integration
- [ ] Day 1-2: Build search engine module
- [ ] Day 3: Test on 20 ASX companies
- [ ] Day 4: Compare results vs ListCorp
- [ ] Day 5: Refine relevance scoring

### Week 2: Global Expansion
- [ ] Day 1-2: Add NASDAQ/NYSE company lists
- [ ] Day 3-4: Test on US companies
- [ ] Day 5: Database schema updates

### Week 3: Polish & Scale
- [ ] Day 1-2: Optimize for cost/performance
- [ ] Day 3-4: Run on 500+ companies
- [ ] Day 5: Milestone 5 (scoring)

---

## 💰 Cost Estimates

### Search API Costs

**Free Tier (DuckDuckGo):**
- 0 companies: $0
- Rate limited but adequate for testing

**Paid Tier (SerpAPI):**
- 100 companies × 7 queries each = 700 searches
- Cost: ~$7 (700/5000 × $50)
- 1,000 companies: ~$70/month

**Recommendation:** Use free tier for initial testing, upgrade if scaling beyond 100 companies/month.

### Total Pipeline Cost Per Company

| Stage | Tool | Cost per Company |
|-------|------|------------------|
| Search | DuckDuckGo/SerpAPI | $0 - $0.07 |
| Extract | Docling | $0 (local) |
| Analyze | Claude API | $0.03 - $0.15 |
| **Total** | | **$0.03 - $0.22** |

**At scale (1,000 companies):**
- Low estimate: $30
- High estimate: $220

---

## 🎯 Success Metrics

Track these KPIs to measure improvement:

| Metric | Current | Target |
|--------|---------|--------|
| Document discovery rate | 25-30% | **80%+** |
| Companies with ESG data | 33% | **70%+** |
| Supported exchanges | 1 (ASX) | **4+ (global)** |
| Docs per company | 1-5 | **5-10** |
| Cost per company analyzed | $0.78 | **$0.05-0.20** |

---

## 🔄 Recommended Action Plan

### This Week:
1. ✅ Document the limitation in README (DONE)
2. **Install duckduckgo-search:** `pip install duckduckgo-search`
3. **Build search module:** Create `src/scraper/search_engine.py`
4. **Test script:** Create `scripts/02b_find_via_search.py`
5. **Run test:** Process 10 companies and compare results

### Next Week:
1. If search works well, add NASDAQ companies
2. Run on 100 companies total
3. Measure improvement in document discovery
4. Move to Milestone 5 (scoring)

### Long Term:
1. Scale to 1,000+ companies globally
2. Build Streamlit dashboard (Milestone 6)
3. Set up automated weekly scans for new reports
4. Add email alerts for high-priority prospects

---

## 📚 Resources

### APIs & Libraries
- **DuckDuckGo Search**: https://pypi.org/project/duckduckgo-search/
- **SerpAPI**: https://serpapi.com/
- **SEC Edgar API**: https://www.sec.gov/edgar/sec-api-documentation
- **OpenCorporates**: https://opencorporates.com/

### Company Lists
- **NASDAQ**: https://www.nasdaq.com/market-activity/stocks/screener
- **NYSE**: https://www.nyse.com/listings_directory/stock
- **ASX**: data/companies.csv (existing)

### ESG Databases
- **CDP**: https://www.cdp.net/
- **GRI**: https://database.globalreporting.org/
- **TCFD**: https://www.fsb-tcfd.org/

---

## Questions?

Run this to check current status:
```bash
sqlite3 data/esg_intel.db "
SELECT
    COUNT(DISTINCT company_id) as companies,
    COUNT(*) as total_docs,
    SUM(CASE WHEN net_zero_target_year IS NOT NULL
             OR renewable_energy_target_pct IS NOT NULL
        THEN 1 ELSE 0 END) as docs_with_targets
FROM esg_data;
"
```

Current result: 6 companies, 27 docs, 2 with targets (7.4% useful rate)

**Target after search implementation:** 20 companies, 100 docs, 70 with targets (70% useful rate)
