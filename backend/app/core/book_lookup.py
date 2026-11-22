"""Búsqueda de datos de un libro por ISBN combinando Open Library y Google Books.

Open Library es la base (comunitaria, buenas portadas); Google Books completa
los datos que falten (mejor cobertura en español). Ambas se consultan en
paralelo y la falla de una no impide usar la otra.
"""

import asyncio
import logging
import time
from collections import OrderedDict

import httpx

logger = logging.getLogger(__name__)

OPEN_LIBRARY = "openlibrary"
GOOGLE_BOOKS = "google_books"
FIELDS = ("title", "authors", "publisher", "year", "page_count", "cover_url")

TIMEOUT = httpx.Timeout(10.0, connect=6.0)
USER_AGENT = "BibliotecaPersonal/1.0 (+https://biblioteca-personal.site)"
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_MAX_ENTRIES = 512

_cache: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()


def _empty(value) -> bool:
    return value is None or value == "" or value == [] or value == 0


def _year(value) -> int | None:
    text = str(value or "")[:4]
    return int(text) if text.isdigit() else None


async def _get_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> dict | None:
    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException:
        # Open Library a veces tarda en aceptar la conexión: un reintento.
        response = await client.get(url, params=params)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


async def _open_library_authors(client: httpx.AsyncClient, isbn: str) -> list[str]:
    """Respaldo: la búsqueda a veces no trae autores; la edición o la obra sí."""
    edition = await _get_json(client, f"https://openlibrary.org/isbn/{isbn}.json")
    if not edition:
        return []
    keys = [a.get("key") for a in edition.get("authors", []) if a.get("key")]
    if not keys and edition.get("works"):
        work = await _get_json(client, f"https://openlibrary.org{edition['works'][0]['key']}.json")
        keys = [(a.get("author") or {}).get("key") for a in (work or {}).get("authors", [])]
        keys = [k for k in keys if k]
    names = []
    for key in keys[:5]:
        author = await _get_json(client, f"https://openlibrary.org{key}.json")
        if author and author.get("name"):
            names.append(author["name"])
    return names


async def fetch_open_library(client: httpx.AsyncClient, isbn: str) -> dict | None:
    data = await _get_json(client, "https://openlibrary.org/search.json", {
        "isbn": isbn,
        "fields": "title,author_name,publisher,first_publish_year,number_of_pages_median,cover_i",
        "limit": 1,
    })
    docs = (data or {}).get("docs") or []
    if not docs:
        return None
    doc = docs[0]
    authors = doc.get("author_name") or []
    if not authors:
        try:
            authors = await _open_library_authors(client, isbn)
        except (httpx.HTTPError, ValueError):
            authors = []
    return {
        "title": doc.get("title"),
        "authors": authors,
        "publisher": (doc.get("publisher") or [None])[0],
        "year": _year(doc.get("first_publish_year")),
        "page_count": doc.get("number_of_pages_median"),
        "cover_url": f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg" if doc.get("cover_i") else None,
    }


async def fetch_google_books(client: httpx.AsyncClient, isbn: str, api_key: str) -> dict | None:
    if not api_key:
        return None
    data = await _get_json(client, "https://www.googleapis.com/books/v1/volumes", {
        "q": f"isbn:{isbn}", "key": api_key, "maxResults": 1,
        "fields": "items(volumeInfo(title,authors,publisher,publishedDate,pageCount,imageLinks))",
    })
    items = (data or {}).get("items") or []
    if not items:
        return None
    info = items[0].get("volumeInfo", {})
    links = info.get("imageLinks") or {}
    cover = links.get("thumbnail") or links.get("smallThumbnail")
    return {
        "title": info.get("title"),
        "authors": info.get("authors") or [],
        "publisher": info.get("publisher"),
        "year": _year(info.get("publishedDate")),
        "page_count": info.get("pageCount") or None,  # Google usa 0 para «desconocido»
        "cover_url": cover.replace("http://", "https://", 1) if cover else None,
    }


def merge_results(primary: dict | None, secondary: dict | None, primary_name: str, secondary_name: str) -> dict:
    """Campo a campo: el dato de la fuente principal y, si falta, el de la otra."""
    merged = {field: None for field in FIELDS}
    sources = {}
    for field in FIELDS:
        for name, result in ((primary_name, primary), (secondary_name, secondary)):
            if result and not _empty(result.get(field)):
                merged[field] = result[field]
                sources[field] = name
                break
    merged["authors"] = merged["authors"] or []
    merged["sources"] = sources
    merged["found"] = bool(sources)
    return merged


async def lookup_isbn(isbn: str, google_api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> dict:
    """Datos combinados de un ISBN-13 válido (con caché en memoria)."""
    cached = _cache.get(isbn)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        _cache.move_to_end(isbn)
        return cached[1]

    async with httpx.AsyncClient(
        timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True, transport=transport,
    ) as client:
        ol_result, gb_result = await asyncio.gather(
            fetch_open_library(client, isbn),
            fetch_google_books(client, isbn, google_api_key),
            return_exceptions=True,
        )

    errors = []
    for name, result in ((OPEN_LIBRARY, ol_result), (GOOGLE_BOOKS, gb_result)):
        if isinstance(result, Exception):
            # Sin la clave en el mensaje: httpx incluye la URL con parámetros.
            logger.warning("Búsqueda de ISBN en %s falló: %s", name, type(result).__name__)
            errors.append(name)
    ol = None if isinstance(ol_result, Exception) else ol_result
    gb = None if isinstance(gb_result, Exception) else gb_result

    result = {"isbn": isbn, **merge_results(ol, gb, OPEN_LIBRARY, GOOGLE_BOOKS), "unavailable_sources": errors}

    # No se cachean respuestas incompletas por fallas temporales.
    if not errors:
        _cache[isbn] = (time.monotonic(), result)
        _cache.move_to_end(isbn)
        while len(_cache) > CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)
    return result


def clear_cache() -> None:
    _cache.clear()
