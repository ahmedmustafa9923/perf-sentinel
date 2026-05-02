"""Performance benchmarks for the BookStore API."""
import pytest


def test_get_book_warm(client, benchmark):
    benchmark(lambda: client.get("/book/42").raise_for_status())


def test_get_book_404(client, benchmark):
    benchmark(lambda: client.get("/book/99999"))


@pytest.mark.parametrize("query", ["Title 1", "Author 5", "Title"])
def test_search(client, benchmark, query):
    benchmark(lambda: client.get("/search", params={"q": query}).raise_for_status())


def test_search_broad(client, benchmark):
    benchmark(lambda: client.get(
        "/search", params={"q": "Book", "limit": 100}
    ).raise_for_status())