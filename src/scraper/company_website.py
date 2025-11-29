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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ESG-related keywords for URL filtering
ESG_KEYWORDS = [
    'sustainability', 'esg', 'climate', 'environment', 'carbon',
    'emissions', 'tcfd', 'annual-report', 'governance', 'net-zero',
    'renewable', 'ghg', 'scope', 'responsibility', 'impact',
    'community', 'social', 'disclosure', 'gri', 'cdp'
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


def extract_report_links(url: str, base_domain: str = None) -> List[Dict[str, str]]:
    """
    Extract PDF/XLSX report links from a webpage.

    Args:
        url: URL of page to scrape
        base_domain: Base domain to check (e.g., "xero.com") - allows subdomains

    Returns:
        List of dicts with 'url', 'title', 'type' keys
    """
    reports = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=15000)

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            browser.close()

        # Extract base domain from URL if not provided
        if not base_domain:
            base_domain = urlparse(url).netloc.replace('www.', '')

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)

            # Check if it's a PDF or XLSX
            if full_url.lower().endswith('.pdf') or full_url.lower().endswith('.xlsx') or '.pdf' in full_url.lower():
                # Get link text as title
                title = link.get_text(strip=True)

                # If no text, try to get from href filename
                if not title or len(title) < 3:
                    filename = urlparse(full_url).path.split('/')[-1]
                    # Remove .pdf extension for cleaner title
                    title = filename.replace('.pdf', '').replace('.xlsx', '').replace('_', ' ').replace('-', ' ').title()

                # Determine document type
                doc_type = 'pdf' if '.pdf' in full_url.lower() else 'xlsx'

                # Check if URL or title contains report-related keywords
                title_lower = title.lower()
                url_lower = full_url.lower()

                # More lenient filtering - include if it has ESG keywords in title OR URL
                if any(keyword in title_lower or keyword in url_lower for keyword in [
                    'sustainability', 'esg', 'climate', 'annual', 'report',
                    'disclosure', 'tcfd', 'gri', 'cdp', 'databook', 'environment',
                    'carbon', 'emissions', 'renewable', 'energy'
                ]):
                    # Allow PDFs from subdomains (e.g., brandfolder.xero.com)
                    pdf_domain = urlparse(full_url).netloc.replace('www.', '')

                    if base_domain in pdf_domain or pdf_domain in base_domain:
                        reports.append({
                            'url': full_url,
                            'title': title,
                            'type': doc_type
                        })

    except Exception as e:
        logger.debug(f"  Error extracting links from {url}: {e}")

    return reports


def find_esg_reports(ticker: str, company_name: str, domain: str = None) -> List[Dict[str, str]]:
    """
    Complete workflow to find ESG reports on a company's website.

    Args:
        ticker: Company ticker (e.g., "XRO")
        company_name: Full company name (for slug generation)
        domain: Company domain (if already known), otherwise will fetch from ListCorp

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

    if not urls:
        logger.info("No sitemap found, crawling common paths...")
        urls = crawl_common_paths(domain)

    if not urls:
        logger.warning(f"⚠ Could not discover any URLs for {domain}")
        return []

    # Step C: Filter for ESG-related URLs
    logger.info("\nSTEP C: Filtering for ESG-related URLs...")
    esg_urls = filter_esg_urls(urls)

    if not esg_urls:
        logger.warning(f"⚠ No ESG-related URLs found for {domain}")
        return []

    # Step D: Extract report links
    logger.info("\nSTEP D: Extracting report links...")
    all_reports = []

    for esg_url in esg_urls[:50]:  # Limit to top 50 ESG pages to find more reports
        logger.debug(f"  Checking: {esg_url}")
        reports = extract_report_links(esg_url, base_domain=domain)

        for report in reports:
            report['source_page'] = esg_url
            all_reports.append(report)

        time.sleep(1)  # Be polite

    # Deduplicate by URL
    seen = set()
    unique_reports = []
    for report in all_reports:
        if report['url'] not in seen:
            seen.add(report['url'])
            unique_reports.append(report)

    logger.info(f"\n✓ Found {len(unique_reports)} unique reports!")

    return unique_reports
