import logging
import src.scraper.company_website as cw


class FakePage:
    def __init__(self, html_map):
        self.html_map = html_map
        self._url = ""
        self._content = ""

    def goto(self, url, wait_until='domcontentloaded', timeout=20000):
        self._url = url
        self._content = self.html_map.get(url, "")

    def wait_for_load_state(self, *_args, **_kwargs):
        return None

    def content(self):
        return self._content

    def query_selector_all(self, selector):
        # Simulate presence of a search input on homepage
        # Support comma-separated selector list
        selectable = ('input[type="search"]', 'input[name="q"]', 'input[name="s"]', 'input[name="search"]')
        if any(s in selector for s in selectable):
            # Treat root homepage with or without trailing slash as having a search input
            if self._url.endswith("/") or self._url.count('/') <= 2:
                return [self]
            return []
        return []

    # Input element methods
    def fill(self, *_args, **_kwargs):
        return None

    def type(self, *_args, **_kwargs):
        return None

    def press(self, *_args, **_kwargs):
        # After pressing Enter, simulate results page
        results_url = self._url.rstrip('/') + "/search?q=test"
        self.goto(results_url)

    @property
    def url(self):
        return self._url


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


def test_inspect_fallback_collects_esg_urls(monkeypatch):
    # Homepage contains a header link to /sustainability
    # Search results contain some additional links
    domain = "example.com"
    html_map = {
        f"https://{domain}": """
            <html>
              <body>
                <header>
                  <a href="/about">About</a>
                  <a href="/sustainability">Sustainability</a>
                </header>
                <input type="search" />
              </body>
            </html>
        """,
        f"https://{domain}/search?q=test": """
            <html>
              <body>
                <a href="/investors">Investors</a>
                <a href="/governance/board">Board</a>
              </body>
            </html>
        """
    }

    monkeypatch.setattr(cw, "sync_playwright", lambda: FakePlaywright(html_map))

    urls = cw.inspect_site_for_esg_urls(domain, queries=['sustainability', 'esg'], max_results=30)
    # Should include sustainability and at least one additional ESG-like URL
    assert any("/sustainability" in u for u in urls)
    assert len(urls) >= 2


