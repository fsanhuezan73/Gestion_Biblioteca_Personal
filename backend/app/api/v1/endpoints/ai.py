"""Recomendaciones de lectura con IA (Fase 1).

La IA recibe solo metadatos de los libros leídos y valorados (título, autor,
género y estrellas); las notas privadas nunca se consultan. Cada candidato se
verifica en Google Books u Open Library antes de mostrarse.
"""

import json
import logging
from datetime import datetime, timezone

import httpx
import oracledb
from fastapi import APIRouter, Depends, HTTPException
from oracledb import DB_TYPE_CLOB
from starlette.concurrency import run_in_threadpool

from app.core.ai.orchestrator import (
    AllProvidersFailed, NoProvidersConfigured, build_providers, generate_candidates,
)
from app.core.book_search import verify_candidates
from app.core.config import get_settings
from app.core.reading import as_date, today
from app.core.recommendations import (
    MAX_RECOMMENDATIONS, build_profile, in_library, next_daily_count, normalize_title,
    rated_read_books, remaining_today,
)
from app.core.security import get_current_user
from app.db.session import get_db_connection
from app.schemas.recommendation import RecommendationsOut, RecommendedBook

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["IA"])

# Los tests lo reemplazan por un httpx.MockTransport (cero llamadas reales).
http_transport: httpx.AsyncBaseTransport | None = None


class DailyLimitReached(Exception):
    pass


# ---------------------------------------------------------------------------
# Acceso a datos (síncrono; se ejecuta fuera del event loop)
# ---------------------------------------------------------------------------

def _load_library(cursor, user_id: int) -> list[dict]:
    """Todos los libros activos con sus autores en una sola consulta.

    Solo metadatos: la consulta no selecciona personal_notes.
    """
    cursor.execute(
        """
        SELECT b.id, b.title, b.reading_status, b.rating, b.finished_at, g.name, a.name
        FROM books b
        LEFT JOIN genres g ON g.id = b.genre_id
        LEFT JOIN book_authors ba ON ba.book_id = b.id
        LEFT JOIN authors a ON a.id = ba.author_id
        WHERE b.user_id = :user_id AND b.deleted_at IS NULL
        ORDER BY b.id, a.name
        """,
        {"user_id": user_id},
    )
    books: dict[int, dict] = {}
    for book_id, title, status, rating, finished_at, genre, author in cursor.fetchall():
        book = books.setdefault(book_id, {
            "title": title, "authors": [], "reading_status": status, "rating": rating,
            "finished_at": as_date(finished_at), "genre": genre,
        })
        if author:
            book["authors"].append(author)
    return list(books.values())


def _load_state(cursor, user_id: int):
    cursor.execute(
        """
        SELECT result, provider, model, generated_at, daily_count, count_date
        FROM ai_recommendations WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    return cursor.fetchone()


def _read_all(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _load_library(cursor, user_id), _load_state(cursor, user_id)


def _save_result(user_id: int, result_json: str, provider: str, model: str, day, limit: int, retry: bool = True):
    """SELECT ... FOR UPDATE y luego UPDATE o INSERT (sin MERGE, por ORA-12860).

    Revisa el límite otra vez bajo bloqueo por si hubo dos solicitudes simultáneas.
    """
    generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT daily_count, count_date FROM ai_recommendations WHERE user_id = :user_id FOR UPDATE",
                {"user_id": user_id},
            )
            row = cursor.fetchone()
            count, count_date = (row[0], as_date(row[1])) if row else (0, None)
            if remaining_today(count, count_date, day, limit) == 0:
                raise DailyLimitReached()
            new_count = next_daily_count(count, count_date, day)
            params = {
                "user_id": user_id, "result": result_json, "provider": provider, "model": model,
                "generated_at": generated_at, "daily_count": new_count, "count_date": day,
            }
            cursor.setinputsizes(result=DB_TYPE_CLOB)
            if row:
                cursor.execute(
                    """
                    UPDATE ai_recommendations
                    SET result = :result, provider = :provider, model = :model,
                        generated_at = :generated_at, daily_count = :daily_count, count_date = :count_date
                    WHERE user_id = :user_id
                    """,
                    params,
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO ai_recommendations
                        (user_id, result, provider, model, generated_at, daily_count, count_date)
                    VALUES (:user_id, :result, :provider, :model, :generated_at, :daily_count, :count_date)
                    """,
                    params,
                )
    except oracledb.IntegrityError:
        # Otra solicitud insertó la fila primero: repetir por la rama UPDATE.
        if not retry:
            raise
        return _save_result(user_id, result_json, provider, model, day, limit, retry=False)
    return new_count, generated_at


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stored_books(result) -> list[dict]:
    """El CLOB con restricción IS JSON puede llegar como texto, LOB o ya decodificado
    (python-oracledb con Oracle 23ai/26ai entrega la lista directamente)."""
    data = result.read() if hasattr(result, "read") else result
    if isinstance(data, (bytes, str)):
        try:
            data = json.loads(data) if data else []
        except ValueError:
            logger.warning("Resultado de recomendaciones guardado no es JSON válido")
            return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def _with_library_flag(items: list[dict], library: list[dict]) -> list[RecommendedBook]:
    books = []
    for item in items:
        try:
            book = RecommendedBook.model_validate({**item, "in_library": False})
        except ValueError:
            continue
        book.in_library = in_library(book.title, book.authors, library)
        books.append(book)
    return books


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/recommendations",
    response_model=RecommendationsOut,
    summary="Último resultado de recomendaciones con IA",
)
async def get_recommendations(current_user_id: int = Depends(get_current_user)):
    settings = get_settings()
    library, state = await run_in_threadpool(_read_all, current_user_id)
    result = provider = model = generated_at = None
    daily_count, count_date = 0, None
    if state:
        result, provider, model, generated_at, daily_count, count_date = state
    return RecommendationsOut(
        recommendations=_with_library_flag(_stored_books(result), library),
        provider=provider,
        model=model,
        generated_at=_utc(generated_at),
        remaining_today=remaining_today(daily_count, as_date(count_date), today(), settings.ai_daily_limit),
        daily_limit=settings.ai_daily_limit,
        rated_books=len(rated_read_books(library)),
        min_rated_books=settings.ai_min_rated_books,
    )


@router.post(
    "/recommendations",
    response_model=RecommendationsOut,
    summary="Generar recomendaciones con IA (hasta 5 libros verificados)",
)
async def create_recommendations(current_user_id: int = Depends(get_current_user)):
    settings = get_settings()
    day = today()
    library, state = await run_in_threadpool(_read_all, current_user_id)

    rated = len(rated_read_books(library))
    if rated < settings.ai_min_rated_books:
        raise HTTPException(
            status_code=422,
            detail=f"Necesitas al menos {settings.ai_min_rated_books} libros leídos con valoración "
                   "para recibir recomendaciones.",
        )
    daily_count, count_date = (state[4], as_date(state[5])) if state else (0, None)
    if remaining_today(daily_count, count_date, day, settings.ai_daily_limit) == 0:
        raise HTTPException(status_code=429, detail="Ya usaste las recomendaciones de hoy. Vuelve mañana.")

    try:
        ai = await generate_candidates(build_providers(settings), build_profile(library), http_transport)
    except NoProvidersConfigured:
        raise HTTPException(status_code=503, detail="Las recomendaciones con IA no están configuradas.")
    except AllProvidersFailed:
        raise HTTPException(
            status_code=503,
            detail="El servicio de recomendaciones no está disponible ahora. Intenta más tarde.",
        )

    candidates = [c for c in ai.candidates if not in_library(c.title, [c.author], library)]
    verified = await verify_candidates(
        [(c.title, c.author) for c in candidates], settings.google_books_api_key, http_transport,
    )
    books: list[RecommendedBook] = []
    seen: set[str] = set()
    for candidate, found in zip(candidates, verified):
        if not found or in_library(found["title"], found["authors"], library):
            continue
        key = normalize_title(found["title"])
        if key in seen:
            continue
        seen.add(key)
        books.append(RecommendedBook(**found, reason=candidate.reason))
        if len(books) == MAX_RECOMMENDATIONS:
            break
    logger.info(
        "Recomendaciones: %s propuso %d, %d verificadas", ai.provider, len(ai.candidates), len(books),
    )
    if not books:
        # No cuenta para el límite diario: no hubo una generación útil.
        raise HTTPException(
            status_code=502,
            detail="No pudimos confirmar ninguna recomendación en los catálogos. Intenta de nuevo.",
        )

    result_json = json.dumps([b.model_dump(exclude={"in_library"}) for b in books], ensure_ascii=False)
    try:
        new_count, generated_at = await run_in_threadpool(
            _save_result, current_user_id, result_json, ai.provider, ai.model, day, settings.ai_daily_limit,
        )
    except DailyLimitReached:
        raise HTTPException(status_code=429, detail="Ya usaste las recomendaciones de hoy. Vuelve mañana.")

    return RecommendationsOut(
        recommendations=books,
        provider=ai.provider,
        model=ai.model,
        generated_at=_utc(generated_at),
        remaining_today=max(0, settings.ai_daily_limit - new_count),
        daily_limit=settings.ai_daily_limit,
        rated_books=rated,
        min_rated_books=settings.ai_min_rated_books,
    )
