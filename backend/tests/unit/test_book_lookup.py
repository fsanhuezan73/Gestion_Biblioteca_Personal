import asyncio

import httpx
import pytest

from app.core import book_lookup
from app.core.book_lookup import lookup_isbn, merge_results

ISBN = "9789584242181"
OL_DOC = {"docs": [{"title": "Los 7 hábitos", "publisher": ["Paidós"], "first_publish_year": 2014, "cover_i": 123}]}
GB_ITEM = {"items": [{"volumeInfo": {
    "title": "Los siete hábitos", "authors": ["Stephen R. Covey"], "publisher": None,
    "publishedDate": "2014-05-01", "pageCount": 496,
    "imageLinks": {"thumbnail": "http://books.google.com/books/content?id=x"},
}}]}


def transport(routes, calls=None):
    """routes: {fragmento_de_url: (status, json) | Exception}"""
    def handler(request: httpx.Request):
        url = str(request.url)
        if calls is not None:
            calls.append(url)
        for fragment, response in routes.items():
            if fragment in url:
                if isinstance(response, Exception):
                    raise response
                return httpx.Response(response[0], json=response[1])
        return httpx.Response(404, json={})
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def fresh_cache():
    book_lookup.clear_cache()
    yield
    book_lookup.clear_cache()


def run(coro):
    return asyncio.run(coro)


def test_merge_prefers_primary_and_fills_gaps():
    merged = merge_results(
        {"title": "A", "authors": [], "publisher": "P", "year": None, "page_count": 0, "cover_url": "c"},
        {"title": "B", "authors": ["X"], "publisher": None, "year": 2014, "page_count": 496, "cover_url": None},
        "openlibrary", "google_books",
    )
    assert merged["title"] == "A" and merged["authors"] == ["X"] and merged["page_count"] == 496
    assert merged["sources"] == {
        "title": "openlibrary", "authors": "google_books", "publisher": "openlibrary",
        "year": "google_books", "page_count": "google_books", "cover_url": "openlibrary",
    }
    assert merged["found"] is True


def test_merge_nothing_found():
    merged = merge_results(None, None, "openlibrary", "google_books")
    assert merged["found"] is False and merged["authors"] == [] and merged["sources"] == {}


def test_lookup_combines_both_sources():
    routes = {
        "openlibrary.org/search.json": (200, OL_DOC),
        "openlibrary.org/isbn/": (404, {}),
        "googleapis.com/books": (200, GB_ITEM),
    }
    result = run(lookup_isbn(ISBN, "clave", transport(routes)))
    assert result["found"] and result["unavailable_sources"] == []
    assert result["title"] == "Los 7 hábitos"                      # Open Library (base)
    assert result["authors"] == ["Stephen R. Covey"]              # completado por Google
    assert result["page_count"] == 496 and result["year"] == 2014
    assert result["cover_url"] == "https://covers.openlibrary.org/b/id/123-M.jpg"


def test_google_only_cover_is_forced_to_https_and_zero_pages_ignored():
    gb = {"items": [{"volumeInfo": {**GB_ITEM["items"][0]["volumeInfo"], "pageCount": 0}}]}
    routes = {"openlibrary.org/search.json": (200, {"docs": []}), "googleapis.com/books": (200, gb)}
    result = run(lookup_isbn(ISBN, "clave", transport(routes)))
    assert result["cover_url"].startswith("https://")
    assert result["page_count"] is None


def test_without_key_google_is_not_called():
    calls = []
    routes = {"openlibrary.org/search.json": (200, OL_DOC), "openlibrary.org/isbn/": (404, {})}
    run(lookup_isbn(ISBN, "", transport(routes, calls)))
    assert not any("googleapis" in c for c in calls)


def test_open_library_failure_falls_back_to_google_and_is_not_cached():
    calls = []
    routes = {"openlibrary.org": httpx.ConnectError("caído"), "googleapis.com/books": (200, GB_ITEM)}
    first = run(lookup_isbn(ISBN, "clave", transport(routes, calls)))
    assert first["found"] and first["unavailable_sources"] == ["openlibrary"]
    assert first["title"] == "Los siete hábitos"
    run(lookup_isbn(ISBN, "clave", transport(routes, calls)))
    assert sum("googleapis" in c for c in calls) == 2  # sin caché tras una falla


def test_successful_results_are_cached():
    calls = []
    routes = {"openlibrary.org/search.json": (200, OL_DOC), "openlibrary.org/isbn/": (404, {}), "googleapis.com/books": (200, GB_ITEM)}
    run(lookup_isbn(ISBN, "clave", transport(routes, calls)))
    count = len(calls)
    run(lookup_isbn(ISBN, "clave", transport(routes, calls)))
    assert len(calls) == count


def test_open_library_author_fallback_via_edition():
    routes = {
        "openlibrary.org/search.json": (200, {"docs": [{"title": "T"}]}),
        f"openlibrary.org/isbn/{ISBN}.json": (200, {"authors": [{"key": "/authors/OL1A"}]}),
        "openlibrary.org/authors/OL1A.json": (200, {"name": "Autora Uno"}),
    }
    result = run(lookup_isbn(ISBN, "", transport(routes)))
    assert result["authors"] == ["Autora Uno"]


def test_timeout_is_retried_once():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("lento")
        if "search.json" in str(request.url):
            return httpx.Response(200, json=OL_DOC)
        return httpx.Response(404, json={})

    result = run(lookup_isbn(ISBN, "", httpx.MockTransport(handler)))
    assert result["found"] and result["unavailable_sources"] == []
