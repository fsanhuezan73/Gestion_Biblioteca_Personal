"""Reglas de las recomendaciones con IA (funciones puras, sin red ni base de datos)."""

import re
import unicodedata
from datetime import date

from app.core.reading import STATUS_READ

MAX_PROFILE_BOOKS = 40
MAX_RECOMMENDATIONS = 5


def normalize_text(value: str | None) -> str:
    """Minúsculas, sin tildes ni puntuación y con espacios simples."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def normalize_title(value: str | None) -> str:
    """Título sin subtítulo (tras «:» o « - ») ni texto entre paréntesis o corchetes."""
    text = re.sub(r"[\(\[].*?[\)\]]", " ", value or "")
    text = re.split(r":| - | — ", text, maxsplit=1)[0]
    return normalize_text(text)


def titles_match(a: str | None, b: str | None) -> bool:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # «El principito» vs «El principito edición ilustrada»: prefijo con palabra completa.
    short, long = sorted((na, nb), key=len)
    return len(short.split()) >= 2 and long.startswith(short + " ")


def _surname(author: str) -> str:
    tokens = [t for t in normalize_text(author).split() if len(t) >= 3]
    return tokens[-1] if tokens else ""


def authors_match(author: str | None, candidates: list[str]) -> bool:
    """El apellido del autor indicado aparece en alguno de los autores encontrados."""
    surname = _surname(author or "")
    if not surname:
        return False
    return any(surname in normalize_text(name).split() for name in candidates)


def in_library(title: str, authors: list[str], library: list[dict]) -> bool:
    """library: [{title, authors}] con todos los libros activos del usuario."""
    for book in library:
        if not titles_match(title, book["title"]):
            continue
        # Mismo título: basta que coincida un autor, o que alguno no tenga autores.
        if not authors or not book["authors"]:
            return True
        if any(authors_match(a, book["authors"]) for a in authors):
            return True
    return False


def rated_read_books(library: list[dict]) -> list[dict]:
    return [b for b in library if b.get("reading_status") == STATUS_READ and b.get("rating")]


def build_profile(library: list[dict], limit: int = MAX_PROFILE_BOOKS) -> list[dict]:
    """Solo metadatos: título, autor, género y estrellas. Nunca notas privadas.

    Prioriza las mejores valoraciones y, entre iguales, las lecturas más recientes.
    """
    books = rated_read_books(library)
    books.sort(key=lambda b: (b["rating"], b.get("finished_at") or date.min), reverse=True)
    return [
        {
            "titulo": b["title"],
            "autor": ", ".join(b["authors"]) or None,
            "genero": b.get("genre"),
            "estrellas": b["rating"],
        }
        for b in books[:limit]
    ]


def remaining_today(daily_count: int | None, count_date: date | None, today: date, limit: int) -> int:
    if count_date != today:
        return limit
    return max(0, limit - (daily_count or 0))


def next_daily_count(daily_count: int | None, count_date: date | None, today: date) -> int:
    return 1 if count_date != today else (daily_count or 0) + 1
