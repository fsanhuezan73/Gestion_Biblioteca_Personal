import asyncio

import httpx
import pytest

from app.core import book_search
from app.core.book_search import clean_synopsis, verify_candidates

KEY = "google-test-key"
GB_ITEMS = {"items": [
    {"volumeInfo": {"title": "Otro libro", "authors": ["Alguien Más"]}},
    {"volumeInfo": {
        "title": "Cien años de soledad", "authors": ["Gabriel García Márquez"], "publisher": "Sudamericana",
        "publishedDate": "1967-05-30", "pageCount": 471,
        "imageLinks": {"thumbnail": "http://books.google.com/x"},
        "description": "<p>La historia de los <b>Buendía</b>.</p>",
        "industryIdentifiers": [{"type": "ISBN_10", "identifier": "8497592204"}],
    }},
]}
OL_DOCS = {"docs": [{
    "title": "Rayuela", "author_name": ["Julio Cortázar"], "first_publish_year": 1963,
    "isbn": ["no-valido", "9788437604572"], "cover_i": 77, "publisher": ["Cátedra"],
}]}


@pytest.fixture(autouse=True)
def fresh_cache():
    book_search.clear_cache()
    yield
    book_search.clear_cache()


def transport(routes, calls):
    def handler(request: httpx.Request):
        calls.append(request)
        response = routes.get(request.url.host, httpx.Response(404, json={}))
        if isinstance(response, Exception):
            raise response
        return response
    return httpx.MockTransport(handler)


def run(coro):
    return asyncio.run(coro)


def test_google_match_skips_unrelated_items_and_cleans_data():
    calls = []
    t = transport({"www.googleapis.com": httpx.Response(200, json=GB_ITEMS)}, calls)
    [found] = run(verify_candidates([("Cien años de soledad", "Gabriel García Márquez")], KEY, t))
    assert found["source"] == "google_books"
    assert found["isbn"] == "9788497592208"
    assert found["cover_url"].startswith("https://")
    assert found["synopsis"] == "La historia de los Buendía."
    assert len(calls) == 1  # no hace falta Open Library
    assert 'intitle:"Cien años de soledad"' in calls[0].url.params["q"]


def test_falls_back_to_open_library_without_synopsis():
    calls = []
    t = transport({
        "www.googleapis.com": httpx.Response(200, json={}),
        "openlibrary.org": httpx.Response(200, json=OL_DOCS),
    }, calls)
    [found] = run(verify_candidates([("Rayuela", "Julio Cortázar")], KEY, t))
    assert found["source"] == "openlibrary"
    assert found["isbn"] == "9788437604572"
    assert found["synopsis"] is None
    assert found["cover_url"] == "https://covers.openlibrary.org/b/id/77-M.jpg"


def test_without_google_key_only_open_library_is_called():
    calls = []
    t = transport({"openlibrary.org": httpx.Response(200, json=OL_DOCS)}, calls)
    run(verify_candidates([("Rayuela", "Julio Cortázar")], "", t))
    assert [c.url.host for c in calls] == ["openlibrary.org"]


def test_nonexistent_book_returns_none_and_author_mismatch_is_rejected():
    calls = []
    t = transport({
        "www.googleapis.com": httpx.Response(200, json=GB_ITEMS),
        "openlibrary.org": httpx.Response(200, json={"docs": []}),
    }, calls)
    results = run(verify_candidates([("Libro inventado", "Nadie"), ("Cien años de soledad", "Isabel Allende")], KEY, t))
    assert results == [None, None]


def test_both_sources_failing_gives_none_and_is_not_cached():
    calls = []
    t = transport({
        "www.googleapis.com": httpx.ConnectError("caído"),
        "openlibrary.org": httpx.Response(500, json={}),
    }, calls)
    assert run(verify_candidates([("Rayuela", "Julio Cortázar")], KEY, t)) == [None]
    assert book_search._cache == {}


def test_results_are_cached():
    calls = []
    t = transport({"openlibrary.org": httpx.Response(200, json=OL_DOCS)}, calls)
    run(verify_candidates([("Rayuela", "Julio Cortázar")], "", t))
    run(verify_candidates([("RAYUELA", "julio cortazar")], "", t))
    assert len(calls) == 1


def test_clean_synopsis_limits_length():
    assert clean_synopsis(None) is None
    assert clean_synopsis("a &amp; b<br>c") == "a & b\nc"
    long_text = clean_synopsis("palabra " * 400)
    assert len(long_text) <= 1200 and long_text.endswith("…")


def test_slow_candidate_is_dropped_by_budget(monkeypatch):
    async def fake_find(client, title, author, key):
        if title == "Lento":
            await asyncio.sleep(5)
        return {"title": title, "authors": [author], "source": "google_books"}

    monkeypatch.setattr(book_search, "find_book", fake_find)
    results = run(verify_candidates([("Rápido", "A"), ("Lento", "B")], KEY, budget_seconds=0.2))
    assert results[0]["title"] == "Rápido" and results[1] is None
