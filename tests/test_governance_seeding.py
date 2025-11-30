import src.scraper.company_website as cw


class FakePage:
    def __init__(self, html):
        self._html = html
    def goto(self, *_args, **_kwargs):
        return None
    def wait_for_load_state(self, *_args, **_kwargs):
        return None
    def content(self):
        return self._html


class FakeBrowser:
    def __init__(self, html):
        self.html = html
    def new_page(self):
        return FakePage(self.html)
    def close(self):
        return None


class FakeChromium:
    def __init__(self, html):
        self.html = html
    def launch(self, headless=True):
        return FakeBrowser(self.html)


class FakePlaywright:
    def __init__(self, html):
        self.chromium = FakeChromium(html)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_company_portals_from_listcorp(monkeypatch):
    html = """
    <html>
      <body>
        <div class="CompanyPage2CompanyPageResourceLinks__list">
          <a href="https://www.example.com/corporate-governance">Corporate Governance</a>
          <a href="https://www.example.com/investors">Investor Relations</a>
          <a href="/reports">Reports</a>
        </div>
      </body>
    </html>
    """
    monkeypatch.setattr(cw, "sync_playwright", lambda: FakePlaywright(html))
    portals = cw.get_company_portals_from_listcorp("EXA", "example-limited")
    assert any("corporate-governance" in p for p in portals)
    assert any("investors" in p for p in portals)
    assert any(p.endswith("/reports") for p in portals)


