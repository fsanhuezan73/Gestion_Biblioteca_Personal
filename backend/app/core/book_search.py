"""Verificación de un libro por título y autor: Google Books y, de respaldo, Open Library.

A diferencia de book_lookup (por ISBN), aquí se busca un libro sugerido por la IA
para confirmar que existe y obtener datos reales. La sinopsis sale solo de Google
Books; Open Library confirma la existencia y aporta portada e ISBN.
"""

import asyncio
import html
import logging
import re
import time
from collections import OrderedDict

import httpx

from app.core.book_lookup import TIMEOUT, USER_AGENT, _year
from app.core.isbn import to_isbn13
from app.core.recommendations import authors_match, normalize_text, titles_match

logger = logging.getLogger(__name__)

GOOGLE_BOOKS = "google_books"
OPEN_LIBRARY = "openlibrary"
MAX_SYNOPSIS_LENGTH = 1200
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_MAX_ENTRIES = 512

_cache: "OrderedDict[tuple[str, str], tuple[float, dict | None]]" = OrderedDict()


def clean_synopsis(value: str | None) -> str | None:
    """Google a veces entrega HTML simple: se deja texto plano y acotado."""
    if not value:
        return None
    text = re.sub(r"<br\s*/?>|</p>", "\n", value, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) > MAX_SYNOPSIS_LENGTH:
        text = text[: MAX_SYNOPSIS_LENGTH - 1].rsplit(" ", 1)[0] + "…"
    return text or None


def _matches(title: str, author: str, found_title: str | None, found_authors: list[str]) -> bool:
    return titles_match(title, found_title) and authors_match(author, found_authors)


def _google_isbn(identifiers: list[dict]) -> str | None:
    by_type = {i.get("type"): i.get("identifier") for i in identifiers or []}
    return to_isbn13(by_type.get("ISBN_13")) or to_isbn13(by_type.get("ISBN_10"))


async def search_google_books(client: httpx.AsyncClient, title: str, author: str, api_key: str) -> dict | None:
    if not api_key:
        return None
    response = await client.get("https://www.googleapis.com/books/v1/volumes", params={
        "q": f'intitle:"{title}" inauthor:"{author}"',
        "key": api_key,
        "maxResults": 5,
        "printType": "books",
        "fields": "items(volumeInfo(title,authors,publisher,publishedDate,pageCount,"
                  "imageLinks,description,industryIdentifiers))",
    })
    response.raise_for_status()
    for item in (response.json() or {}).get("items") or []:
        info = item.get("volumeInfo") or {}
        authors = info.get("authors") or []
        if not _matches(title, author, info.get("title"), authors):
            continue
        links = info.get("imageLinks") or {}
        cover = links.get("thumbnail") or links.get("smallThumbnail")
        return {
            "title": info.get("title"),
            "authors": authors,
            "isbn": _google_isbn(info.get("industryIdentifiers")),
            "year": _year(info.get("publishedDate")),
            "publisher": info.get("publisher"),
            "page_count": info.get("pageCount") or None,
            "cover_url": cover.replace("http://", "https://", 1) if cover else None,
            "synopsis": clean_synopsis(info.get("description")),
            "source": GOOGLE_BOOKS,
        }
    return None


async def search_open_library(client: httpx.AsyncClient, title: str, author: str) -> dict | None:
    response = await client.get("https://openlibrary.org/search.json", params={
        "title": title,
        "author": author,
        "limit": 5,
        "fields": "title,author_name,first_publish_year,isbn,cover_i,publisher,number_of_pages_median",
    })
    response.raise_for_status()
    for doc in (response.json() or {}).get("docs") or []:
        authors = doc.get("author_name") or []
        if not _matches(title, author, doc.get("title"), authors):
            continue
        isbn = next((v for v in map(to_isbn13, doc.get("isbn") or []) if v), None)
        return {
            "title": doc.get("title"),
            "authors": authors,
            "isbn": isbn,
            "year": _year(doc.get("first_publish_year")),
            "publisher": (doc.get("publisher") or [None])[0],
            "page_count": doc.get("number_of_pages_median"),
            "cover_url": f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg" if doc.get("cover_i") else None,
            "synopsis": None,
            "source": OPEN_LIBRARY,
        }
    return None


async def find_book(client: httpx.AsyncClient, title: str, author: str, google_api_key: str) -> dict | None:
    """Libro verificado o None si no aparece en ninguna fuente.

    Lanza la excepción solo si ambas fuentes fallaron (para no cachear la falla).
    """
    key = (normalize_text(title), normalize_text(author))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        _cache.move_to_end(key)
        return cached[1]

    failures = 0
    result = None
    for source, search in (
        (GOOGLE_BOOKS, lambda: search_google_books(client, title, author, google_api_key)),
        (OPEN_LIBRARY, lambda: search_open_library(client, title, author)),
    ):
        try:
            result = await search()
        except (httpx.HTTPError, ValueError) as error:
            # Sin la clave en el log: httpx incluye la URL con parámetros.
            logger.warning("Verificación en %s falló: %s", source, type(error).__name__)
            failures += 1
            continue
        if result:
            break
    if failures == 2:
        raise httpx.HTTPError("Ninguna fuente respondió")

    _cache[key] = (time.monotonic(), result)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)
    return result


async def verify_candidates(
    candidates: list[tuple[str, str]],
    google_api_key: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict | None]:
    """Verifica en paralelo; mantiene el orden y usa None para los no encontrados."""
    async with httpx.AsyncClient(
        timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True, transport=transport,
    ) as client:
        results = await asyncio.gather(
            *(find_book(client, title, author, google_api_key) for title, author in candidates),
            return_exceptions=True,
        )
    return [None if isinstance(r, Exception) else r for r in results]


def clear_cache() -> None:
    _cache.clear()
