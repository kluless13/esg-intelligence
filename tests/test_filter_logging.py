import logging
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
        self._html = html

    def new_page(self):
        return FakePage(self._html)

    def close(self):
        return None


class FakeChromium:
    def __init__(self, html):
        self._html = html

    def launch(self, headless=True):
        return FakeBrowser(self._html)


class FakePlaywright:
    def __init__(self, html):
        self.chromium = FakeChromium(html)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_filtered_out_logging(monkeypatch, caplog):
    # Links are documents but without ESG keywords in title or URL
    html = """
    <html>
      <body>
        <a href="/files/press-kit.pdf">Press Kit</a>
        <a href="/files/board-pack.xlsx">Board Pack</a>
      </body>
    </html>
    """
    monkeypatch.setattr(cw, "sync_playwright", lambda: FakePlaywright(html))

    caplog.set_level(logging.DEBUG)
    _ = cw.extract_report_links("https://example.com/ir", base_domain="example.com")

    assert any("Filtered-out examples" in rec.message for rec in caplog.records)


