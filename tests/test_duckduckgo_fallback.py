import src.scraper.search_engine as se


class FakeDDGS:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def text(self, query, max_results=5):
        # Return a mix of file types and plain pages
        return [
            {'href': 'https://example.com/reports/fy2024-sustainability.pdf', 'title': 'FY24 Sustainability Report'},
            {'href': 'https://example.com/data/fy2024-databook.xlsx', 'title': 'Databook 2024'},
            {'href': 'https://example.com/data/archive-2023.xls', 'title': 'Archive XLS'},
            {'href': 'https://example.com/data/emissions.csv', 'title': 'Emissions CSV'},
            {'href': 'https://example.com/sustainability/overview', 'title': 'Sustainability Overview'},
        ]


def test_duckduckgo_search_multi_format(monkeypatch):
    monkeypatch.setattr(se, "DDGS", lambda: FakeDDGS())

    results = se.search_for_sustainability_reports(
        company_name="Example Corp",
        ticker="EXA",
        years=[2024],
        max_results_per_query=5
    )
    # Should score and keep our entries
    assert len(results) >= 5

    filtered = se.filter_valid_documents(results, min_relevance=0.0)
    urls = [r['url'] for r in filtered]
    assert any(u.endswith('.pdf') for u in urls)
    assert any(u.endswith('.xlsx') for u in urls)
    assert any(u.endswith('.xls') for u in urls)
    assert any(u.endswith('.csv') for u in urls)
    assert any('/sustainability/' in u for u in urls)


