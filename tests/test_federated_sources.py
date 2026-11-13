import pytest
from app.infrastructure import sources


def test_diverse_sources_and_partial_outages(monkeypatch):
    def web(_):
        return [
            {
                "title": "Official docs",
                "url": "https://docs.example.org/guide",
                "text": "Official documentation explains retrieval systems and provides traceable evidence.",
            },
            {
                "title": "Unsafe",
                "url": "javascript:alert(1)",
                "text": "This unsafe result contains sufficient text but must never become a clickable link.",
            },
        ]

    def paper(_):
        return [
            {
                "title": "Research paper",
                "url": "https://doi.org/10.1/example",
                "doi": "10.1/example",
                "text": "A published research abstract describes an experiment on evidence grounding in retrieval.",
            }
        ]

    def unavailable(_):
        raise ValueError("unavailable")

    monkeypatch.setattr(sources, "web", web)
    monkeypatch.setattr(sources, "crossref", paper)
    monkeypatch.setattr(sources, "europepmc", paper)
    monkeypatch.setattr(sources, "arxiv", unavailable)
    monkeypatch.setattr(sources, "wikipedia", unavailable)
    rows, coverage = sources.search_with_coverage("retrieval")
    assert [r["provider"] for r in rows] == ["Web search", "Crossref"]
    assert [r["id"] for r in rows] == ["S1", "S2"]
    assert len(coverage) == 5
    assert coverage[3]["status"] == "unavailable"


def test_all_outages_are_explicit(monkeypatch):
    def unavailable(_):
        raise ValueError("unavailable")

    for name in ["web", "crossref", "europepmc", "arxiv", "wikipedia"]:
        monkeypatch.setattr(sources, name, unavailable)
    with pytest.raises(ValueError, match="No source service"):
        sources.search_with_coverage("retrieval")


def test_private_and_unsafe_source_links():
    for url in [
        "javascript:alert(1)",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://[::1]",
        "https://user:password@example.org",
    ]:
        assert sources.safe_url(url) is None
    assert sources.safe_url("https://example.org/docs") == "https://example.org/docs"
