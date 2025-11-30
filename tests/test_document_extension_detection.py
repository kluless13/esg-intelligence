import types
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


def test_multi_format_detection(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/files/report-2024.pdf">FY24 Sustainability Report</a>
        <a href="/files/data-2024.xlsx">Databook</a>
        <a href="/files/archive-2022.xls">Archive</a>
        <a href="/files/energy.csv">Energy CSV</a>
        <a href="/files/other.ods">ODS Sheet</a>
        <a href="/download?file=climate_appendix.pdf">Download Appendix</a>
      </body>
    </html>
    """

    monkeypatch.setattr(cw, "sync_playwright", lambda: FakePlaywright(html))

    reports = cw.extract_report_links("https://example.com/sustainability", base_domain="example.com")
    urls = {r['url']: r['type'] for r in reports}

    assert "https://example.com/files/report-2024.pdf" in urls and urls["https://example.com/files/report-2024.pdf"] == "pdf"
    assert "https://example.com/files/data-2024.xlsx" in urls and urls["https://example.com/files/data-2024.xlsx"] == "excel"
    assert "https://example.com/files/archive-2022.xls" in urls and urls["https://example.com/files/archive-2022.xls"] == "excel"
    assert "https://example.com/files/energy.csv" in urls and urls["https://example.com/files/energy.csv"] == "csv"
    assert "https://example.com/files/other.ods" in urls and urls["https://example.com/files/other.ods"] == "other"
    assert "https://example.com/download?file=climate_appendix.pdf" in urls and urls["https://example.com/download?file=climate_appendix.pdf"] == "pdf"


