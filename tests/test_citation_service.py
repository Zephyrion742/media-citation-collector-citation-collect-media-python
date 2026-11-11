from src.citation_service import Citation, dedupe_citations


def test_dedupe_keeps_first_source_and_order():
    items = [Citation("A", "https://source.test/a", "first"), Citation("A copy", "https://source.test/a/", "duplicate"), Citation("B", "https://source.test/b", "second")]
    assert dedupe_citations(items) == [items[0], items[2]]
