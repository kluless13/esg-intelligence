"""
Update company website domains by extracting them from ListCorp 'Company Resources' links.

This is smarter than guessing domains because:
1. ListCorp has direct links to Corporate Governance / Investor Relations pages
2. These links give us the ACTUAL company domain (not consumer sites)
3. Handles .com vs .com.au automatically
4. Handles rebranded companies (e.g., fortescue.com not fortescuemetals.com)

Usage:
    python scripts/00_update_domains_from_listcorp.py --ticker WOW     # Single company
    python scripts/00_update_domains_from_listcorp.py --limit 50       # Top 50 companies
    python scripts/00_update_domains_from_listcorp.py --update-empty   # Only companies without domain
"""

import sys
import sqlite3
import argparse
import time
import re
from pathlib import Path
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DB_PATH

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def get_listcorp_slug_from_url(listcorp_url: str) -> str:
    """Extract slug from ListCorp URL like https://www.listcorp.com/asx/cba/commonwealth-bank"""
    if not listcorp_url:
        return None
    # Parse: /asx/{ticker}/{slug}
    parts = listcorp_url.rstrip('/').split('/')
    if len(parts) >= 2:
        return parts[-1]  # Last part is the slug
    return None


def extract_domain_from_listcorp(ticker: str, listcorp_url: str = None) -> dict:
    """
    Visit ListCorp page and extract company domain from Corporate Governance / Investor Relations links.

    Returns:
        dict with 'domain', 'portal_urls', 'source' keys
    """
    result = {
        'domain': None,
        'portal_urls': [],
        'source': None
    }

    # Build ListCorp URL
    if listcorp_url:
        url = listcorp_url
    else:
        # Fallback to constructing URL
        url = f"https://www.listcorp.com/asx/{ticker.lower()}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set a reasonable user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Priority order for finding company domain:
        # 1. Corporate Governance link (best for ESG)
        # 2. Investor Relations link
        # 3. Website link
        # 4. Any external link in Company Resources

        priority_keywords = [
            ('corporate governance', 'governance'),
            ('investor relations', 'investors'),
            ('sustainability', 'esg'),
            ('website', 'company website'),
            ('reports', 'annual report'),
        ]

        # Look for Company Resources links
        resource_selectors = [
            '.CompanyPage2CompanyPageResourceLinks__list a',
            'a.lcGreyLink.CompanyPage2CompanyPageResourceLinks__anchor',
            '.company-resources a',
        ]

        anchors = []
        for selector in resource_selectors:
            anchors.extend(soup.select(selector))

        # If no specific selectors found, look for all links
        if not anchors:
            anchors = soup.find_all('a', href=True)

        found_urls = {}

        for anchor in anchors:
            href = anchor.get('href', '')
            text = anchor.get_text(strip=True).lower()

            # Skip ListCorp internal links
            if 'listcorp.com' in href:
                continue

            # Skip non-http links
            if not href.startswith('http'):
                continue

            # Categorize by keyword match
            for priority, keywords in enumerate(priority_keywords):
                if any(kw in text for kw in keywords):
                    if priority not in found_urls:
                        found_urls[priority] = []
                    found_urls[priority].append({
                        'url': href,
                        'text': text,
                        'priority': priority
                    })
                    break

        # Get the best URL (lowest priority number = highest priority)
        best_url = None
        for priority in sorted(found_urls.keys()):
            if found_urls[priority]:
                best_url = found_urls[priority][0]
                break

        if best_url:
            # Extract domain from URL
            parsed = urlparse(best_url['url'])
            domain = parsed.netloc.replace('www.', '')

            result['domain'] = domain
            result['portal_urls'] = [best_url['url']]
            result['source'] = best_url['text']

            # Also collect all portal URLs for later use
            all_portals = []
            for urls in found_urls.values():
                for u in urls:
                    all_portals.append(u['url'])
            result['portal_urls'] = list(dict.fromkeys(all_portals))

    except Exception as e:
        print(f"  ✗ Error fetching {url}: {e}")

    return result


def get_companies(limit=None, ticker=None, update_empty=False):
    """Get companies from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    conditions = []

    if ticker:
        conditions.append(f"ticker = '{ticker.upper()}'")

    if update_empty:
        conditions.append("(website IS NULL OR website = '')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Order by listcorp_url presence (companies with URLs first)
    query = f"""
        SELECT id, ticker, name, listcorp_url, website
        FROM companies
        WHERE {where_clause}
        ORDER BY
            CASE WHEN listcorp_url IS NOT NULL THEN 0 ELSE 1 END,
            ticker
    """

    if limit and not ticker:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    companies = cursor.fetchall()
    conn.close()

    return companies


def update_company_website(company_id: int, domain: str, portal_urls: list = None):
    """Update company website in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE companies
        SET website = ?
        WHERE id = ?
    """, (domain, company_id))

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Update company domains from ListCorp')
    parser.add_argument('--ticker', type=str, help='Process single company')
    parser.add_argument('--limit', type=int, help='Process N companies')
    parser.add_argument('--update-empty', action='store_true',
                        help='Only update companies without a domain')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be updated without saving')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    print("=" * 70)
    print("ESG Intelligence - Domain Updater from ListCorp")
    print("=" * 70)
    print()

    companies = get_companies(
        limit=args.limit,
        ticker=args.ticker,
        update_empty=args.update_empty
    )

    if not companies:
        print("No companies to process!")
        return

    total = len(companies)
    print(f"Processing {total} companies...")
    print()

    updated = 0
    failed = 0
    skipped = 0

    for i, (company_id, ticker, name, listcorp_url, current_website) in enumerate(companies, 1):
        print(f"[{i}/{total}] {ticker} - {name}")

        if args.verbose:
            print(f"  Current domain: {current_website or '(none)'}")
            print(f"  ListCorp URL: {listcorp_url or '(none)'}")

        # Extract domain from ListCorp
        result = extract_domain_from_listcorp(ticker, listcorp_url)

        if result['domain']:
            new_domain = result['domain']
            source = result['source']

            # Check if domain changed
            if current_website == new_domain:
                print(f"  → No change ({new_domain})")
                skipped += 1
            else:
                print(f"  ✓ Found: {new_domain} (from '{source}')")

                if current_website:
                    print(f"    (was: {current_website})")

                if not args.dry_run:
                    update_company_website(company_id, new_domain, result['portal_urls'])
                    updated += 1
                else:
                    print(f"    [DRY RUN - not saved]")
                    updated += 1
        else:
            print(f"  ✗ Could not find domain")
            failed += 1

        # Rate limiting
        time.sleep(1)

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Companies processed:  {total}")
    print(f"Domains updated:      {updated}")
    print(f"No change needed:     {skipped}")
    print(f"Failed to find:       {failed}")

    if args.dry_run:
        print()
        print("This was a DRY RUN. Run without --dry-run to save changes.")


if __name__ == "__main__":
    main()
