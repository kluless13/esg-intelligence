"""
ListCorp News Scraper - Find ESG documents on company news pages

This module searches ListCorp company news pages for ESG-related documents
like sustainability reports, annual reports, and climate disclosures.

NOTE: ListCorp uses JavaScript rendering, so we need Playwright with stealth mode.
"""
import re
import time
from typing import List, Dict, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Page
from playwright_stealth import stealth_sync
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import LISTCORP_BASE, REQUEST_DELAY


# Keywords for identifying ESG-related documents
HIGH_PRIORITY_KEYWORDS = [
    "sustainability report",
    "sustainability-report",
    "esg report",
    "esg-report",
    "climate report",
    "climate-report",
    "environmental report",
    "environmental-report",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "annual report",
    "annual-report",
    "annual review",
    "annual-review",
]

ADDITIONAL_KEYWORDS = [
    "tcfd",
    "emissions",
    "net zero",
    "net-zero",
    "carbon",
    "renewable",
]


def extract_financial_year(text: str) -> Optional[str]:
    """
    Extract financial year from text like 'FY25', 'FY2025', '2024', etc.
    Returns standardized format like 'FY2025', 'FY2024', etc.

    Args:
        text: Text to search for financial year

    Returns:
        Standardized financial year string or None
    """
    text_lower = text.lower()

    # Pattern 1: FY25, FY2025, FY24, etc.
    match = re.search(r'fy\s*(\d{2,4})', text_lower)
    if match:
        year = match.group(1)
        # Convert 2-digit to 4-digit year
        if len(year) == 2:
            year_int = int(year)
            # Assume 20-30 is 2020-2030, otherwise 1900s
            if 20 <= year_int <= 50:
                year = f"20{year}"
            else:
                year = f"19{year}"
        return f"FY{year}"

    # Pattern 2: Just a year like 2024, 2023
    match = re.search(r'\b(20\d{2})\b', text)
    if match:
        return f"FY{match.group(1)}"

    return None


def classify_document_type(title: str) -> str:
    """
    Classify document type based on title.

    Args:
        title: Document title

    Returns:
        Document type: 'sustainability_report', 'annual_report', etc.
    """
    title_lower = title.lower()

    if any(kw in title_lower for kw in ["sustainability report", "sustainability-report"]):
        return "sustainability_report"
    elif any(kw in title_lower for kw in ["esg report", "esg-report"]):
        return "esg_report"
    elif any(kw in title_lower for kw in ["climate report", "climate-report"]):
        return "climate_report"
    elif any(kw in title_lower for kw in ["environmental report", "environmental-report"]):
        return "environmental_report"
    elif any(kw in title_lower for kw in ["annual report", "annual-report"]):
        return "annual_report"
    elif "tcfd" in title_lower:
        return "tcfd_disclosure"
    else:
        return "other_esg"


def is_esg_related(title: str) -> bool:
    """
    Check if a document title is ESG-related based on keywords.

    Args:
        title: Document title to check

    Returns:
        True if ESG-related, False otherwise
    """
    title_lower = title.lower()

    # Check high priority keywords
    if any(kw in title_lower for kw in HIGH_PRIORITY_KEYWORDS):
        return True

    # Check medium priority keywords
    if any(kw in title_lower for kw in MEDIUM_PRIORITY_KEYWORDS):
        return True

    # Check additional keywords
    if any(kw in title_lower for kw in ADDITIONAL_KEYWORDS):
        return True

    return False


def find_esg_documents(ticker: str, company_slug: str, verbose: bool = False) -> List[Dict]:
    """
    Find ESG-related documents on a company's ListCorp page using Playwright.

    Args:
        ticker: ASX ticker symbol (e.g., 'XRO', 'BHP')
        company_slug: URL slug for company (e.g., 'xero-limited')
        verbose: Print debug information

    Returns:
        List of dictionaries containing document information:
        [
            {
                'title': 'FY25 Sustainability Report',
                'listcorp_news_url': 'https://www.listcorp.com/asx/xro/.../fy25-sustainability-report-3189699.html',
                'document_type': 'sustainability_report',
                'financial_year': 'FY2025',
                'publication_date': '2025-05-15'  # if available
            },
            ...
        ]
    """
    # We'll check both the Reports section and News section
    # Reports section has annual reports, News has various announcements
    base_url = f"{LISTCORP_BASE}/asx/{ticker.lower()}/{company_slug}"

    if verbose:
        print(f"  Fetching: {base_url}")

    documents = []

    try:
        with sync_playwright() as p:
            # Launch browser with stealth mode to avoid bot detection
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            stealth_sync(page)

            # First, try the Reports section (has annual reports)
            reports_url = f"{base_url}#reports"
            page.goto(reports_url, wait_until='networkidle')
            time.sleep(2)  # Give JS time to render

            # Find all links
            links = page.query_selector_all('a')

            for link in links:
                try:
                    href = link.get_attribute('href') or ''
                    title = link.inner_text().strip()

                    if not title or not href:
                        continue

                    # Check if ESG-related
                    if not is_esg_related(title):
                        continue

                    # Construct full URL if relative
                    if not href.startswith('http'):
                        full_url = LISTCORP_BASE + href
                    else:
                        full_url = href

                    # Skip anchor links and duplicates
                    if '#' in href and not '.html' in href:
                        continue

                    # Extract financial year
                    fy = extract_financial_year(title)

                    # Classify document type
                    doc_type = classify_document_type(title)

                    # Try to extract date (look for nearby text)
                    pub_date = None
                    try:
                        parent = link.locator('xpath=..')
                        parent_text = parent.inner_text() if parent else ''
                        date_match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2,4})', parent_text, re.I)
                        if date_match:
                            pub_date = date_match.group(0)
                    except:
                        pass

                    documents.append({
                        'title': title,
                        'listcorp_news_url': full_url,
                        'document_type': doc_type,
                        'financial_year': fy,
                        'publication_date': pub_date
                    })

                except Exception as e:
                    if verbose:
                        print(f"    Error processing link: {e}")
                    continue

            browser.close()

        # Remove duplicates (same URL)
        seen_urls = set()
        unique_docs = []
        for doc in documents:
            if doc['listcorp_news_url'] not in seen_urls:
                seen_urls.add(doc['listcorp_news_url'])
                unique_docs.append(doc)

        if verbose:
            print(f"    Found {len(unique_docs)} ESG-related documents")

        # Sleep to be polite to the server
        time.sleep(REQUEST_DELAY)

        return unique_docs

    except Exception as e:
        if verbose:
            print(f"    Error: {e}")
        return []


def extract_company_slug_from_url(listcorp_url: str) -> Optional[str]:
    """
    Extract company slug from a ListCorp URL.

    Args:
        listcorp_url: Full ListCorp URL like 'https://www.listcorp.com/asx/xro/xero-limited'

    Returns:
        Company slug like 'xero-limited' or None if not found
    """
    # Pattern: /asx/{ticker}/{company-slug}
    match = re.search(r'/asx/[^/]+/([^/]+)', listcorp_url)
    if match:
        return match.group(1)
    return None


if __name__ == "__main__":
    # Test the scraper with a known company
    print("Testing ListCorp News Scraper")
    print("=" * 60)

    # Test with Xero (we know they have sustainability reports)
    ticker = "XRO"
    slug = "xero-limited"

    print(f"\nTesting: {ticker} - {slug}")
    docs = find_esg_documents(ticker, slug, verbose=True)

    if docs:
        print(f"\nFound {len(docs)} documents:")
        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. {doc['title']}")
            print(f"   Type: {doc['document_type']}")
            print(f"   FY: {doc['financial_year']}")
            print(f"   URL: {doc['listcorp_news_url']}")
    else:
        print("\nNo documents found. This might mean:")
        print("1. The company has no ESG reports")
        print("2. The HTML structure doesn't match our selectors")
        print("3. The URL pattern is different")
