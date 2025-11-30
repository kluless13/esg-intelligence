import types
import builtins
import logging

import pytest

import src.scraper.company_website as cw


def test_sitemap_insufficiency_triggers_fallback(monkeypatch, caplog):
    """
    When sitemap returns <10 URLs or 0 ESG URLs, fallback to crawl_common_paths() is used.
    """
    # Stub: sitemap returns only 3 URLs (ANZ case)
    monkeypatch.setattr(cw, "discover_urls_from_sitemap", lambda domain: [
        f"https://{domain}",
        f"https://{domain}/personal",
        f"https://{domain}/business",
    ])

    # Stub: filter_esg_urls returns empty for the initial sitemap set
    def fake_filter_esg_urls(urls):
        # No ESG links in the initial sitemap set
        return [u for u in urls if any(k in u.lower() for k in ['/sustainability', '/esg'])]
    monkeypatch.setattr(cw, "filter_esg_urls", fake_filter_esg_urls)

    # Stub: crawl_common_paths finds sustainability pages
    monkeypatch.setattr(cw, "crawl_common_paths", lambda domain: [
        f"https://{domain}/sustainability",
        f"https://{domain}/about/sustainability",
    ])

    # Stub: avoid network by faking website discovery and extraction
    monkeypatch.setattr(cw, "get_company_website_from_listcorp", lambda ticker, company_slug=None: "anz.com")
    monkeypatch.setattr(cw, "extract_report_links", lambda url, base_domain=None, enable_js_downloads=False: [
        {'url': f"{url}/report.pdf", 'title': "Sustainability Report", 'type': 'pdf'}
    ])

    caplog.set_level(logging.INFO)
    reports = cw.find_esg_reports("ANZ", "ANZ Group Holdings", domain=None, max_esg_pages=5)

    # Assert fallback was used and at least one report found from crawled URLs
    assert any("Sitemap insufficient, crawling common paths..." in rec.message for rec in caplog.records)
    assert len(reports) > 0
    # Ensure reports carry source_page
    assert all('source_page' in r for r in reports)


