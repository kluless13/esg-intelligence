#!/usr/bin/env python3
"""
Verify all URLs in report_links.json are accessible.

This script checks each URL and reports which ones are broken.
"""

import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORT_LINKS_FILE = DATA_DIR / "report_links.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}


def check_url(url: str, timeout: int = 10) -> dict:
    """Check if a URL is accessible."""
    result = {
        'url': url,
        'status': 'unknown',
        'status_code': None,
        'error': None
    }

    try:
        response = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        result['status_code'] = response.status_code

        if response.status_code == 200:
            result['status'] = 'ok'
        elif response.status_code == 404:
            result['status'] = 'not_found'
        elif response.status_code in [301, 302, 303, 307, 308]:
            result['status'] = 'redirect'
        else:
            result['status'] = 'error'

    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Timeout'
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['error'] = str(e)[:100]

    return result


def main():
    # Load report links
    if not REPORT_LINKS_FILE.exists():
        print(f"❌ Report links file not found: {REPORT_LINKS_FILE}")
        return 1

    with open(REPORT_LINKS_FILE) as f:
        data = json.load(f)

    companies = data.get('companies', {})

    print(f"\n{'='*80}")
    print(f"URL Verification Report")
    print(f"{'='*80}\n")

    total_urls = 0
    ok_urls = 0
    broken_urls = 0
    timeout_urls = 0

    broken_list = []

    for ticker, company in companies.items():
        company_name = company.get('company_name', ticker)
        reports = company.get('reports', [])

        print(f"\n📊 {ticker} - {company_name}")

        for report in reports:
            url = report.get('url', '')
            file_type = report.get('type', 'pdf')
            year = report.get('year', 'unknown')
            title = report.get('title', 'Unknown')

            # Skip web-only reports
            if file_type == 'web':
                print(f"  ⏭️  Skipping web report: {title}")
                continue

            total_urls += 1
            print(f"  🔍 Checking: {title} ({year})...", end=' ', flush=True)

            result = check_url(url)

            if result['status'] == 'ok':
                print(f"✅ OK")
                ok_urls += 1
            elif result['status'] == 'not_found':
                print(f"❌ 404 NOT FOUND")
                broken_urls += 1
                broken_list.append({
                    'ticker': ticker,
                    'title': title,
                    'year': year,
                    'url': url,
                    'status_code': 404
                })
            elif result['status'] == 'timeout':
                print(f"⏱️  TIMEOUT")
                timeout_urls += 1
            else:
                print(f"⚠️  {result['status_code'] or 'ERROR'}")
                broken_urls += 1
                broken_list.append({
                    'ticker': ticker,
                    'title': title,
                    'year': year,
                    'url': url,
                    'status_code': result['status_code'],
                    'error': result.get('error')
                })

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total URLs checked:  {total_urls}")
    print(f"OK (200):            {ok_urls}")
    print(f"Broken:              {broken_urls}")
    print(f"Timeouts:            {timeout_urls}")
    print(f"{'='*80}\n")

    if broken_list:
        print(f"\n{'='*80}")
        print(f"BROKEN URLS ({len(broken_list)})")
        print(f"{'='*80}\n")

        for item in broken_list:
            print(f"❌ {item['ticker']} - {item['title']} ({item['year']})")
            print(f"   Status: {item['status_code']}")
            print(f"   URL: {item['url']}")
            if item.get('error'):
                print(f"   Error: {item['error']}")
            print()

    return 0 if broken_urls == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
