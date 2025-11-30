"""
Search engine-based document discovery using DuckDuckGo.
Finds sustainability documents (PDF, Excel, CSV, ODS) for recent years.
"""
from duckduckgo_search import DDGS
from urllib.parse import urlparse
import time


QUERY_TEMPLATES = [
    '"{company_name}" sustainability report {year} filetype:pdf',
    '"{company_name}" ESG report {year}',
    '"{company_name}" sustainability databook {year} filetype:xlsx',
    '"{company_name}" sustainability databook {year} filetype:xls',
    '"{company_name}" GRI index {year} filetype:xlsx',
    '"{company_name}" climate disclosure {year} filetype:pdf',
    '"{company_name}" emissions {year} filetype:pdf',
]

DOC_EXT = ['.pdf', '.xlsx', '.xls', '.xlsm', '.csv', '.ods']


def search_duckduckgo(query: str, max_results: int = 5) -> list:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                'url': r['href'],
                'title': r.get('title') or r['href'],
                'snippet': r.get('body', ''),
                'source': 'duckduckgo'
            })
    return results


def deduplicate_urls(results: list) -> list:
    seen = set()
    unique = []
    for r in results:
        u = r['url'].rstrip('/')
        if u not in seen:
            seen.add(u)
            unique.append(r)
    return unique


def score_relevance(results: list, company_name: str, ticker: str) -> list:
    scored = []
    cname = company_name.lower()
    t = ticker.lower()
    for r in results:
        score = 0.0
        url = r['url'].lower()
        title = (r.get('title') or '').lower()
        domain = urlparse(url).netloc.lower()

        if t in url or cname.split(' ')[0] in url:
            score += 0.3
        if any(k in title for k in ['sustainability', 'esg', 'climate', 'gri', 'emissions', 'report', 'databook']):
            score += 0.3
        if any(ext in url for ext in DOC_EXT):
            score += 0.2
        if t in domain or cname.replace(' ', '') in domain:
            score += 0.2

        r['relevance_score'] = max(0.0, min(1.0, score))
        scored.append(r)
    return sorted(scored, key=lambda x: x['relevance_score'], reverse=True)


def filter_valid_documents(results: list, min_relevance: float = 0.4) -> list:
    valid = []
    for r in results:
        if r.get('relevance_score', 0) < min_relevance:
            continue
        url = r['url'].lower()
        if any(ext in url for ext in DOC_EXT):
            valid.append(r)
        elif any(k in url for k in ['sustainability', 'esg', 'climate', 'environment']):
            valid.append(r)
    return valid


def search_for_sustainability_reports(
    company_name: str,
    ticker: str,
    years: list,
    max_results_per_query: int = 5
) -> list:
    results = []
    for year in years:
        for tpl in QUERY_TEMPLATES:
            q = tpl.format(company_name=company_name, ticker=ticker, year=year)
            try:
                results.extend(search_duckduckgo(q, max_results=max_results_per_query))
                time.sleep(0.7)
            except Exception:
                continue
    unique = deduplicate_urls(results)
    scored = score_relevance(unique, company_name, ticker)
    return scored


