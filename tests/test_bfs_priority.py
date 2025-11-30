import src.scraper.company_website as cw


class FakePage:
    def __init__(self, html_map):
        self.html_map = html_map
        self._url = ""

    def goto(self, url, wait_until='domcontentloaded', timeout=15000):
        self._url = url

    def wait_for_load_state(self, *_args, **_kwargs):
        return None

    def content(self):
        return self.html_map.get(self._url, "")


class FakeBrowser:
    def __init__(self, html_map):
        self.html_map = html_map
    def new_page(self):
        return FakePage(self.html_map)
    def close(self):
        return None


class FakeChromium:
    def __init__(self, html_map):
        self.html_map = html_map
    def launch(self, headless=True):
        return FakeBrowser(self.html_map)


class FakePlaywright:
    def __init__(self, html_map):
        self.chromium = FakeChromium(html_map)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_bfs_same_domain_and_limits(monkeypatch):
    domain = "example.com"
    seeds = [f"https://{domain}/corporate-governance"]

    # governance page links to same-domain ESG pages and an external page
    html_map = {
        f"https://{domain}/corporate-governance": """
            <html><body>
              <a href="/sustainability">Sustainability</a>
              <a href="/investors/reports">Investors Reports</a>
              <a href="https://external.com/ignore">External</a>
            </body></html>
        """,
        f"https://{domain}/sustainability": """
            <html><body>
              <a href="/sustainability/reports">Reports</a>
            </body></html>
        """,
        f"https://{domain}/investors/reports": """
            <html><body>
              <a href="/investors/reports/fy24">FY24</a>
            </body></html>
        """,
        f"https://{domain}/sustainability/reports": "<html></html>",
        f"https://{domain}/investors/reports/fy24": "<html></html>",
    }

    monkeypatch.setattr(cw, "sync_playwright", lambda: FakePlaywright(html_map))
    visited = cw.discover_urls_bfs(domain, seeds, max_pages=4)
    # Should stay same-domain and respect max_pages
    assert all(u.startswith(f"https://{domain}") for u in visited)
    assert len(visited) <= 4


