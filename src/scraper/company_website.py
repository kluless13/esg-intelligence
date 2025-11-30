"""
Website crawler to find ESG documents on company websites.

This crawler systematically discovers sustainability reports by:
1. Getting company website URL from ListCorp
2. Discovering all URLs via sitemap or crawling key sections
3. Filtering for ESG-related URLs
4. Extracting report links (PDFs, XLSX) from those pages
"""

import re
import time
import logging
import requests
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ESG-related keywords for URL filtering
ESG_KEYWORDS = [
    'sustainability', 'esg', 'climate', 'environment', 'carbon',
    'emissions', 'tcfd', 'annual-report', 'governance', 'net-zero',
    'renewable', 'ghg', 'scope', 'responsibility', 'impact',
    'community', 'social', 'disclosure', 'gri', 'cdp',
    'investor', 'investors', 'reports', 'reporting'
]

# Common paths to check if no sitemap
COMMON_PATHS = [
    '/investors', '/sustainability', '/about', '/esg', '/governance',
    '/corporate', '/responsibility', '/environment', '/annual-reports',
    '/investor-relations', '/investors/reports', '/sustainability/reports',
    '/about/sustainability', '/about/esg', '/about/environment'
]


def get_company_website_from_listcorp(ticker: str, company_slug: str = None) -> Optional[str]:
    """
    Extract company website URL from their ListCorp page.

    Args:
        ticker: Company ticker (e.g., "XRO")
        company_slug: URL slug (e.g., "xero-limited"), auto-generated if None

    Returns:
        Website domain (e.g., "xero.com") or None if not found
    """
    if not company_slug:
        company_slug = f"{ticker.lower()}-limited"

    url = f"https://www.listcorp.com/asx/{ticker.lower()}/{company_slug}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)

            # Look for website link - ListCorp usually shows it in company info
            # Common patterns: "Website:", "Company Website:", or direct link
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Try multiple selectors
            website = None

            # Look for links with "Website" text nearby
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True).lower()
                href = link['href']

                # Skip ListCorp's own links
                if 'listcorp.com' in href:
                    continue

                # Look for external links
                if href.startswith('http') and ('website' in text or len(text) < 30):
                    website = href
                    break

            # If not found, look for meta tags or structured data
            if not website:
                # Check meta tags
                meta_url = soup.find('meta', property='og:url')
                if meta_url and meta_url.get('content'):
                    url_content = meta_url['content']
                    if 'listcorp.com' not in url_content:
                        website = url_content

            browser.close()

            if website:
                # Extract clean domain
                parsed = urlparse(website)
                domain = parsed.netloc or parsed.path
                # Remove www.
                domain = domain.replace('www.', '')
                logger.info(f"  ✓ Found website: {domain}")
                return domain

            logger.warning(f"  ⚠ No website found on ListCorp page")
            return None

    except Exception as e:
        logger.error(f"  ✗ Error fetching ListCorp page: {e}")
        return None


def get_company_portals_from_listcorp(ticker: str, company_slug: str) -> List[str]:
    """
    Extract key 'Company Resources' links from ListCorp company page:
    Corporate Governance, Investor Relations, Reports.
    Returns absolute URLs (often on the company domain).
    """
    portals: List[str] = []
    slug_variants = [company_slug]
    # If 'limited' was stripped earlier, also try variant including it
    if not company_slug.endswith('-limited'):
        slug_variants.append(f"{company_slug}-limited")
    for slug in slug_variants:
        url = f"https://www.listcorp.com/asx/{ticker.lower()}/{slug}"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                try:
                    page.wait_for_load_state('networkidle', timeout=3000)
                except Exception:
                    pass
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            found_any = False
            # Prefer specific resource list anchors if present; fallback to all anchors
            resource_anchors = soup.select('.CompanyPage2CompanyPageResourceLinks__list a, a.lcGreyLink.CompanyPage2CompanyPageResourceLinks__anchor')
            anchors = resource_anchors if resource_anchors else soup.find_all('a', href=True)
            for a in anchors:
                text = a.get_text(strip=True).lower()
                if any(k in text for k in [
                    'corporate governance', 'governance',
                    'investor relations', 'investors',
                    'reports', 'financial reports'
                ]):
                    href = a['href']
                    if href.startswith('http'):
                        portals.append(href)
                    else:
                        portals.append(urljoin(url, href))
                    found_any = True
            if found_any:
                break  # success with this slug
        except Exception as e:
            logger.debug(f"  Error extracting portals from ListCorp for {ticker} at {url}: {e}")
            continue
    portals = list(dict.fromkeys(portals))
    if portals:
        logger.info(f"  ✓ ListCorp portals for {ticker}: {portals}")
    else:
        logger.info(f"  ⚠ No Company Resources portals found on ListCorp for {ticker}")
    return portals


def discover_urls_bfs(domain: str, seeds: List[str], max_pages: int = 100, allowed_domains: Optional[Set[str]] = None) -> List[str]:
    """
    Bounded same-domain BFS crawl starting from seed URLs. Prioritize ESG-like paths.
    allowed_domains: optional set of additional apex domains to allow (e.g., 'anz.com.au')
    """
    visited: Set[str] = set()
    queue: List[str] = []
    discovered: List[str] = []

    def score(u: str) -> int:
        u_lower = u.lower()
        key_terms = ['sustainability', 'esg', 'report', 'reports', 'investor', 'investors',
                     'governance', 'climate', 'environment', 'tcfd', 'data', 'download',
                     'documents', 'publications']
        s = sum(1 for k in key_terms if k in u_lower)
        s += max(0, 5 - u_lower.count('/'))
        return -s  # for ascending sort

    # Normalize seeds to absolute
    norm_seeds = []
    for s in seeds:
        if s.startswith('http'):
            norm_seeds.append(s)
        else:
            norm_seeds.append(f"https://{domain}{s if s.startswith('/') else '/'+s}")
    queue.extend(sorted(list(dict.fromkeys(norm_seeds)), key=score))

    # Build allowed domains set (apex forms without www.)
    allowed: Set[str] = set()
    allowed.add(domain)
    if allowed_domains:
        for d in allowed_domains:
            allowed.add(d.replace('www.', ''))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        while queue and len(visited) < max_pages:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            try:
                page.goto(current, wait_until='domcontentloaded', timeout=15000)
                try:
                    page.wait_for_load_state('networkidle', timeout=2000)
                except Exception:
                    pass
                discovered.append(current)
                soup = BeautifulSoup(page.content(), 'html.parser')
                for a in soup.find_all('a', href=True):
                    full = urljoin(current, a['href'])
                    parsed = urlparse(full)
                    if not parsed.scheme or not parsed.netloc:
                        continue
                    link_domain = parsed.netloc.replace('www.', '')
                    # Allow if matches any allowed domain or its subdomain
                    if not any(link_domain == ad or link_domain.endswith('.' + ad) for ad in allowed):
                        continue
                    if full not in visited and full not in queue:
                        queue.append(full)
                queue = sorted(queue, key=score)
            except Exception:
                continue
        browser.close()

    return list(dict.fromkeys(discovered))


def collect_links_headful(
    domain: str,
    seeds: List[str],
    allowed_domains: Optional[Set[str]] = None,
    max_pages: int = 60,
    max_minutes: int = 3,
    headless: bool = False
) -> Dict[str, List[str]]:
    """
    Headful (or headless if requested) pass that visits seed pages, scrolls,
    expands common controls, and harvests:
      - page_urls: same-domain page links for later extraction
      - doc_urls: direct document links (pdf/xlsx/xls/xlsm/csv/ods or ?file=/ ?document=)
    """
    start = datetime.datetime.utcnow()
    visited: Set[str] = set()
    queue: List[str] = []
    page_urls: List[str] = []
    doc_urls: List[str] = []

    allowed: Set[str] = set()
    allowed.add(domain)
    if allowed_domains:
        for d in allowed_domains:
            allowed.add(d.replace('www.', ''))

    def time_exceeded() -> bool:
        return (datetime.datetime.utcnow() - start).total_seconds() > max_minutes * 60

    # Normalize seeds to absolute
    norm_seeds = []
    for s in seeds:
        if s.startswith('http'):
            norm_seeds.append(s)
        else:
            norm_seeds.append(f"https://{domain}{s if s.startswith('/') else '/'+s}")
    queue.extend(list(dict.fromkeys(norm_seeds)))

    doc_exts = ['.pdf', '.xlsx', '.xls', '.xlsm', '.csv', '.ods']
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            while queue and len(visited) < max_pages and not time_exceeded():
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                try:
                    page.goto(current, wait_until='domcontentloaded', timeout=25000)
                    try:
                        page.wait_for_load_state('networkidle', timeout=4000)
                    except Exception:
                        pass
                    # Try to expand common UI controls
                    for sel in ['text=Show more', 'text=Load more', 'text=See more', 'button:has-text("More")']:
                        try:
                            page.locator(sel).first.click(timeout=1000)
                        except Exception:
                            continue
                    # Scroll to load dynamic content
                    for _ in range(5):
                        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                        page.wait_for_timeout(600)

                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    page_urls.append(current)
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        full = urljoin(current, href)
                        parsed = urlparse(full)
                        if not parsed.scheme or not parsed.netloc:
                            continue
                        link_domain = parsed.netloc.replace('www.', '')
                        low = full.lower()
                        # Document links: allow cross-domain (CDN/asset hosts)
                        is_doc = any(ext in low for ext in doc_exts) or (('file=' in low or 'document=' in low) and any(ext in low for ext in doc_exts))
                        if is_doc:
                            doc_urls.append(full)
                            continue
                        # Page links: keep same-brand domains only
                        if any(link_domain == ad or link_domain.endswith('.' + ad) for ad in allowed):
                            if full not in visited and full not in queue:
                                queue.append(full)
                except Exception:
                    continue
            browser.close()
    except Exception as e:
        logger.debug(f"  Headful collect error: {e}")

    # Deduplicate
    return {
        'page_urls': list(dict.fromkeys(page_urls)),
        'doc_urls': list(dict.fromkeys(doc_urls)),
    }

def discover_urls_from_sitemap(domain: str, timeout: int = 30) -> List[str]:
    """
    Discover all URLs from website's sitemap using ultimate-sitemap-parser.

    Improvements over previous implementation:
    - Automatic robots.txt parsing (no manual regex)
    - Gzipped sitemap support (.xml.gz)
    - Nested sitemap indexes (unlimited depth)
    - Proper User-Agent headers (prevents 403 blocks)
    - Memory-efficient streaming

    Args:
        domain: Website domain (e.g., "xero.com")
        timeout: Timeout in seconds (default: 30)

    Returns:
        List of URLs found in sitemaps. Empty list on failure.
    """
    from usp.tree import sitemap_tree_for_homepage
    from usp.exceptions import SitemapException
    from usp.web_client.requests_client import RequestsWebClient

    urls = []
    homepage_url = f"https://{domain}"

    try:
        logger.info(f"  Discovering sitemaps for {homepage_url}...")

        # Create web client with proper configuration
        web_client = RequestsWebClient()
        web_client.set_timeout(timeout)

        # Create sitemap tree (handles robots.txt, nested sitemaps, .gz files)
        tree = sitemap_tree_for_homepage(homepage_url, web_client=web_client)

        # Extract all URLs (memory-efficient generator)
        for page in tree.all_pages():
            if page.url:
                urls.append(page.url)

        if urls:
            logger.info(f"  ✓ Found {len(urls)} URLs from sitemaps")
        else:
            logger.info(f"  ⚠ No sitemap found, will crawl common paths")

    except SitemapException as e:
        logger.debug(f"  Sitemap error for {domain}: {e}")
        logger.info(f"  ⚠ No valid sitemap found, will crawl common paths")
    except Exception as e:
        logger.debug(f"  Error fetching sitemaps for {domain}: {e}")
        logger.info(f"  ⚠ Could not access sitemaps, will crawl common paths")

    return urls


def crawl_common_paths(domain: str) -> List[str]:
    """
    Crawl common paths where ESG content is typically found.

    Args:
        domain: Website domain

    Returns:
        List of discovered URLs
    """
    urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for path in COMMON_PATHS:
            url = f"https://{domain}{path}"

            try:
                logger.debug(f"  Checking: {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=15000)

                # If page loads successfully (not 404), add it
                if page.url.startswith(f"https://{domain}"):
                    urls.append(page.url)

                    # Also extract links from this page
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')

                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(url, href)

                        # Only include URLs from same domain
                        if urlparse(full_url).netloc.replace('www.', '') == domain:
                            urls.append(full_url)

                time.sleep(1)  # Be polite

            except PlaywrightTimeout:
                logger.debug(f"  Timeout: {url}")
            except Exception as e:
                logger.debug(f"  Error: {url} - {e}")

        browser.close()

    # Deduplicate
    urls = list(set(urls))
    logger.info(f"  ✓ Found {len(urls)} URLs by crawling common paths")

    return urls


def _collect_links_from_selectors(page, base_url: str, selectors: List[str]) -> List[str]:
    """Collect absolute hrefs from given CSS selectors on the page."""
    content = page.content()
    soup = BeautifulSoup(content, 'html.parser')
    urls: List[str] = []
    for sel in selectors:
        for el in soup.select(sel):
            href = el.get('href')
            if not href:
                continue
            full_url = urljoin(base_url, href)
            urls.append(full_url)
    return urls


def inspect_site_for_esg_urls(domain: str, queries: List[str] = None, max_results: int = 30) -> List[str]:
    """
    Inspect the site using a browser to find ESG-related URLs by scanning
    navigation/footer links and (if available) on-site search.

    Args:
        domain: Website domain
        queries: On-site search queries to try (default: ['sustainability','esg'])
        max_results: Maximum number of URLs to return

    Returns:
        Deduplicated list of ESG-related URLs from inspection
    """
    if queries is None:
        queries = ['sustainability', 'esg']

    homepage = f"https://{domain}"
    discovered: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            logger.info("  Inspecting site navigation/footer for ESG links...")
            page.goto(homepage, wait_until='domcontentloaded', timeout=20000)
            try:
                page.wait_for_load_state('networkidle', timeout=4000)
            except Exception:
                pass

            # Collect from header/nav/footer/menu
            nav_selectors = [
                'header a[href]', 'nav a[href]', 'footer a[href]',
                'a[role="menuitem"][href]', 'a[href*="sustainability"]', 'a[href*="esg"]'
            ]
            discovered.extend(_collect_links_from_selectors(page, homepage, nav_selectors))

            # Try on-site search if there is a visible search input
            logger.info("  Trying on-site search for ESG queries...")
            search_inputs = page.query_selector_all('input[type="search"], input[name="q"], input[name="s"], input[name="search"]')
            if search_inputs:
                for q in queries:
                    try:
                        # Use the first input field
                        input_el = search_inputs[0]
                        input_el.fill("")
                        input_el.type(q, delay=20)
                        input_el.press("Enter")
                        # Wait briefly for results
                        page.wait_for_load_state('networkidle', timeout=5000)
                        # Collect result links
                        discovered.extend(_collect_links_from_selectors(page, page.url, ['a[href]']))
                        # Navigate back to homepage for next query
                        page.goto(homepage, wait_until='domcontentloaded', timeout=20000)
                    except Exception:
                        # Non-fatal
                        continue
            else:
                logger.debug("  No obvious on-site search input found.")

        except PlaywrightTimeout:
            logger.debug(f"  Timeout while inspecting {homepage}")
        except Exception as e:
            logger.debug(f"  Error during inspection for {domain}: {e}")
        finally:
            browser.close()

    # Keep same-domain only
    same_domain = []
    for u in discovered:
        parsed = urlparse(u)
        if not parsed.scheme or not parsed.netloc:
            continue
        if parsed.netloc.replace('www.', '') == domain:
            same_domain.append(u)

    # ESG filter
    esg_urls = filter_esg_urls(same_domain)
    # Deduplicate and limit
    esg_urls = list(dict.fromkeys(esg_urls))[:max_results]
    logger.info(f"  ✓ Inspection found {len(esg_urls)} ESG URLs")
    return esg_urls


def filter_esg_urls(urls: List[str]) -> List[str]:
    """
    Filter URLs to only include those likely related to ESG/sustainability.

    Args:
        urls: List of URLs to filter

    Returns:
        Filtered list of ESG-related URLs
    """
    esg_urls = []

    for url in urls:
        url_lower = url.lower()

        # Check if URL contains ESG keywords
        if any(keyword in url_lower for keyword in ESG_KEYWORDS):
            esg_urls.append(url)

    logger.info(f"  ✓ Filtered to {len(esg_urls)} ESG-related URLs")
    return esg_urls


def extract_report_links(url: str, base_domain: str = None, enable_js_downloads: bool = False) -> List[Dict[str, str]]:
    """
    Extract PDF/XLSX report links from a webpage.

    Args:
        url: URL of page to scrape
        base_domain: Base domain to check (e.g., "xero.com") - allows subdomains
        enable_js_downloads: When True, attempt simple JS-driven download discovery

    Returns:
        List of dicts with 'url', 'title', 'type' keys
    """
    reports = []
    filtered_out: List[Dict[str, str]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=15000)

            # Optional small wait for dynamic content
            try:
                page.wait_for_load_state('networkidle', timeout=3000)
            except Exception:
                pass

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Minimal JS-download discovery (optional)
            if enable_js_downloads:
                # Heuristic: look for anchors/buttons with download wording and hrefs with file params
                candidates = soup.find_all(['a', 'button'])
                for cand in candidates:
                    text = cand.get_text(strip=True).lower()
                    href = cand.get('href') or cand.get('data-href') or ''
                    if any(w in text for w in ['download', 'pdf', 'report']) and href:
                        # Normalize URL
                        js_url = urljoin(url, href)
                        # If query contains file=.pdf/.xlsx, treat accordingly
                        if ('file=' in js_url.lower() or 'document=' in js_url.lower()) and ('.pdf' in js_url.lower() or '.xlsx' in js_url.lower() or '.xls' in js_url.lower()):
                            reports.append({
                                'url': js_url,
                                'title': text.title() or 'Download',
                                'type': 'pdf' if '.pdf' in js_url.lower() else ('excel' if any(ext in js_url.lower() for ext in ['.xlsx', '.xls']) else 'other')
                            })

            browser.close()

        # Extract base domain from URL if not provided
        if not base_domain:
            base_domain = urlparse(url).netloc.replace('www.', '')

        # Find all links
        link_candidates = soup.find_all('a', href=True)
        logger.debug(f"  Found {len(link_candidates)} <a> elements on page: {url}")
        first_hrefs_preview = [l['href'] for l in link_candidates[:10]]
        if first_hrefs_preview:
            logger.debug(f"  First hrefs: {first_hrefs_preview}")

        doc_extensions = ['.pdf', '.xlsx', '.xls', '.xlsm', '.csv', '.ods']

        for link in link_candidates:
            href = link['href']
            full_url = urljoin(url, href)
            url_lower = full_url.lower()

            # Determine if link points to a document by extension or common query patterns
            has_doc_ext = any(ext in url_lower for ext in doc_extensions)
            is_query_doc = ('file=' in url_lower or 'document=' in url_lower) and any(ext in url_lower for ext in doc_extensions)
            is_document = has_doc_ext or is_query_doc

            if not is_document:
                filtered_out.append({'reason': 'not_document', 'href': href})
                continue

            # Get link text as title
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                filename = urlparse(full_url).path.split('/')[-1]
                title = filename.replace('_', ' ').replace('-', ' ').title()

            # Determine document type
            if '.pdf' in url_lower:
                doc_type = 'pdf'
            elif any(ext in url_lower for ext in ['.xlsx', '.xls', '.xlsm']):
                doc_type = 'excel'
            elif '.csv' in url_lower:
                doc_type = 'csv'
            else:
                doc_type = 'other'

            # Note: We already filtered pages to ESG-related URLs earlier.
            # Within those pages, include all documents regardless of ESG keywords to avoid missing valid files.
            # This captures cases like generic 'Archive' or 'Databook' filenames without explicit ESG words.

            # Allow documents from subdomains or known asset hosts if base_domain overlaps
            doc_domain = urlparse(full_url).netloc.replace('www.', '')
            if not (base_domain in doc_domain or doc_domain.endswith(base_domain) or base_domain.endswith(doc_domain)):
                filtered_out.append({'reason': 'cross_domain', 'href': href})
                continue

            reports.append({
                'url': full_url,
                'title': title,
                'type': doc_type
            })

    except Exception as e:
        logger.debug(f"  Error extracting links from {url}: {e}")

    # Always log a summary of filtered-out samples for debugging (even if zero)
    sample = filtered_out[:5]
    logger.debug(f"  Filtered-out examples ({len(filtered_out)}): {sample}")

    return reports


def find_esg_reports(
    ticker: str,
    company_name: str,
    domain: str = None,
    max_esg_pages: int = 15,
    enable_js_downloads: bool = False,
    fallback_inspect: bool = True,
    site_search_queries: Optional[List[str]] = None,
    fallback_search: bool = True,
    search_years: Optional[List[int]] = None
    ,
    headful_fallback: bool = False,
    headful_max_pages: int = 60,
    headful_max_minutes: int = 3,
    seed_override: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Complete workflow to find ESG reports on a company's website.

    Args:
        ticker: Company ticker (e.g., "XRO")
        company_name: Full company name (for slug generation)
        domain: Company domain (if already known), otherwise will fetch from ListCorp
        max_esg_pages: Maximum ESG pages to scan for documents
        enable_js_downloads: Whether to attempt simple JS-driven download discovery
        fallback_inspect: Whether to use on-site inspection fallback when sitemap insufficient
        site_search_queries: Queries for on-site search fallback
        fallback_search: Whether to use search engine fallback if site methods yield nothing
        search_years: Years to search for (latest first) in search fallback

    Returns:
        List of report dicts with 'url', 'title', 'type', 'source_page' keys
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Finding ESG reports for {ticker} - {company_name}")
    logger.info(f"{'='*60}")

    # Step A: Get website domain
    if not domain:
        logger.info("STEP A: Getting company website from ListCorp...")
        company_slug = company_name.lower().replace(' ', '-').replace('limited', '').replace('ltd', '').strip('-')
        domain = get_company_website_from_listcorp(ticker, company_slug)

        if not domain:
            logger.warning(f"⚠ Could not find website for {ticker}")
            return []

    logger.info(f"Website: {domain}")

    # Step B: Discover URLs
    logger.info("\nSTEP B: Discovering URLs on website...")
    urls = discover_urls_from_sitemap(domain)

    # Initial ESG filtering
    initial_esg_urls: List[str] = filter_esg_urls(urls) if urls else []

    esg_urls: List[str]
    # Fallback if sitemap insufficient (few URLs or no ESG URLs)
    if not urls or len(urls) < 10 or len(initial_esg_urls) == 0:
        logger.info("Sitemap insufficient, crawling common paths...")
        crawl_urls = crawl_common_paths(domain)
        urls = (urls or []) + crawl_urls
        # Re-filter after crawling
        esg_urls = filter_esg_urls(urls)

        # On-site inspection fallback
        if fallback_inspect and len(esg_urls) == 0:
            logger.info("Sitemap+crawl insufficient, inspecting site navigation/search...")
            inspected = inspect_site_for_esg_urls(domain, queries=site_search_queries or ['sustainability', 'esg'])
            esg_urls = list(dict.fromkeys(esg_urls + inspected))
    else:
        esg_urls = initial_esg_urls

    if not urls:
        logger.warning(f"⚠ Could not discover any URLs for {domain}")
        return []

    # Step C: Prioritize ESG URLs
    logger.info("\nSTEP C: Filtering for ESG-related URLs...")
    if not esg_urls:
        # Try governance/investor seeding from ListCorp and BFS before giving up
        logger.info("No ESG URLs yet. Trying ListCorp governance/investor seeding + BFS...")
        company_slug = company_name.lower().replace(' ', '-').replace('limited', '').replace('ltd', '').strip('-')
        portal_links = get_company_portals_from_listcorp(ticker, company_slug)
        if portal_links:
            # Build allowed domain set from portal links + current domain (handles .com ↔ .com.au variants)
            allowed_domains = {domain}
            for link in portal_links:
                parsed = urlparse(link)
                if parsed.netloc:
                    allowed_domains.add(parsed.netloc.replace('www.', ''))
            bfs_urls = discover_urls_bfs(domain, portal_links, max_pages=100, allowed_domains=allowed_domains)
            urls = list(dict.fromkeys(urls + bfs_urls))
            esg_urls = filter_esg_urls(urls)
        if not esg_urls:
            logger.warning(f"⚠ No ESG-related URLs found for {domain}")
            return []

    # Prioritize common ESG paths first
    priority_order = ['/sustainability', '/esg', '/investors', '/governance', '/reports']
    def esg_priority(u: str) -> int:
        for idx, p in enumerate(priority_order):
            if p in u.lower():
                return idx
        return len(priority_order)
    esg_urls = sorted(list(set(esg_urls)), key=esg_priority)

    # Step D: Extract report links
    logger.info("\nSTEP D: Extracting report links...")
    all_reports = []

    for esg_url in esg_urls[:max_esg_pages]:
        logger.debug(f"  Checking: {esg_url}")
        reports = extract_report_links(esg_url, base_domain=domain, enable_js_downloads=enable_js_downloads)

        for report in reports:
            report['source_page'] = esg_url
            all_reports.append(report)

        time.sleep(1)  # Be polite

    # If no reports were found, try a late governance seeding + BFS pass (cross-TLD aware)
    if len(all_reports) == 0:
        logger.info("No reports found from initial ESG URLs. Trying governance seeding + BFS as late fallback...")
        company_slug = company_name.lower().replace(' ', '-').replace('limited', '').replace('ltd', '').strip('-')
        portal_links = get_company_portals_from_listcorp(ticker, company_slug)
        if portal_links:
            allowed_domains = {domain}
            for link in portal_links:
                parsed = urlparse(link)
                if parsed.netloc:
                    allowed_domains.add(parsed.netloc.replace('www.', ''))
            bfs_urls = discover_urls_bfs(domain, portal_links, max_pages=100, allowed_domains=allowed_domains)
            # Re-run extraction on new ESG pages not already checked
            combined_urls = list(dict.fromkeys(urls + bfs_urls))
            new_esg = filter_esg_urls(combined_urls)
            already_checked = set(esg_urls[:max_esg_pages])
            rerun_urls = [u for u in new_esg if u not in already_checked][:max_esg_pages]
            if rerun_urls:
                logger.info(f"Re-running extraction on {len(rerun_urls)} governance-seeded ESG URLs...")
                for esg_url in rerun_urls:
                    reports = extract_report_links(esg_url, base_domain=domain, enable_js_downloads=enable_js_downloads)
                    for report in reports:
                        report['source_page'] = esg_url
                        all_reports.append(report)
                    time.sleep(1)

    # If still no reports, try headful fallback with governance seeds
    if len(all_reports) == 0 and headful_fallback:
        logger.info("\nSTEP E: Headful fallback – collecting links from governance/investor seeds...")
        company_slug = company_name.lower().replace(' ', '-').replace('limited', '').replace('ltd', '').strip('-')
        portal_links = get_company_portals_from_listcorp(ticker, company_slug)
        # Optional explicit seed override
        if seed_override:
            portal_links.append(seed_override)
        if portal_links:
            allowed_domains = {domain}
            for link in portal_links:
                parsed = urlparse(link)
                if parsed.netloc:
                    allowed_domains.add(parsed.netloc.replace('www.', ''))
            collected = collect_links_headful(
                domain=domain,
                seeds=portal_links,
                allowed_domains=allowed_domains,
                max_pages=headful_max_pages,
                max_minutes=headful_max_minutes,
                headless=False  # visible browser as requested
            )
            # First, try direct doc URLs
            for du in collected.get('doc_urls', []):
                low = du.lower()
                if '.pdf' in low:
                    dtype = 'pdf'
                elif any(ext in low for ext in ['.xlsx', '.xls', '.xlsm']):
                    dtype = 'excel'
                elif '.csv' in low:
                    dtype = 'csv'
                else:
                    dtype = 'other'
                all_reports.append({'url': du, 'title': du.split('/')[-1], 'type': dtype, 'source_page': None})
            # Then, re-run extraction on harvested page URLs
            for purl in collected.get('page_urls', [])[:max_esg_pages]:
                reps = extract_report_links(purl, base_domain=domain, enable_js_downloads=True)
                for r in reps:
                    r['source_page'] = purl
                    all_reports.append(r)

    # If still no reports and search fallback is enabled, try DuckDuckGo search
    if len(all_reports) == 0 and fallback_search:
        try:
            from src.scraper.search_engine import search_for_sustainability_reports, filter_valid_documents
            years = search_years or []
            if not years:
                # Default to last 5 years including current year
                from datetime import datetime
                current_year = datetime.utcnow().year
                years = [current_year - i for i in range(0, 5)]

            logger.info("\nSTEP E: Search fallback (DuckDuckGo) for ESG documents...")
            ddg_results = search_for_sustainability_reports(
                company_name=company_name,
                ticker=ticker,
                years=years,
                max_results_per_query=5
            )
            ddg_docs = filter_valid_documents(ddg_results, min_relevance=0.4)
            for d in ddg_docs:
                all_reports.append({
                    'url': d['url'],
                    'title': d.get('title') or d['url'],
                    'type': ('pdf' if d['url'].lower().endswith('.pdf') else
                             ('excel' if any(ext in d['url'].lower() for ext in ['.xlsx', '.xls', '.xlsm']) else
                              ('csv' if d['url'].lower().endswith('.csv') else 'other'))),
                    'source_page': d.get('source_page')
                })
        except Exception as e:
            logger.debug(f"  Search fallback error: {e}")

    # Deduplicate by URL
    seen = set()
    unique_reports = []
    for report in all_reports:
        if report['url'] not in seen:
            seen.add(report['url'])
            unique_reports.append(report)

    logger.info(f"\n✓ Found {len(unique_reports)} unique reports!")

    return unique_reports
