from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.reading import as_date, goal_progress, today
from app.core.security import get_current_user
from app.db.session import get_db_connection
from app.schemas.stats import (
    MAX_YEAR, MIN_YEAR, CurrentlyReading, GoalProgress, LabelCount, LibraryStats, MonthCount,
    RatingCount, StatsOut, YearStats,
)

router = APIRouter(prefix="/stats", tags=["Estadísticas"])

TOP_GENRES = 7
TOP_AUTHORS = 5
CURRENTLY_READING_LIMIT = 10

# Todas las consultas filtran por propietario y excluyen libros eliminados.
_OWNED = "b.user_id = :user_id AND b.deleted_at IS NULL"
# Libros terminados dentro del año consultado [year_start, year_end).
_READ_IN_YEAR = (
    _OWNED + " AND b.reading_status = 'Leído'"
    " AND b.finished_at >= :year_start AND b.finished_at < :year_end"
)


def _group_genres(rows) -> list[LabelCount]:
    """Top géneros; el resto se agrupa en «Otros» para que el gráfico sea legible."""
    genres = [LabelCount(label=name, count=count) for name, count in rows]
    if len(genres) <= TOP_GENRES + 1:
        return genres
    others = sum(g.count for g in genres[TOP_GENRES:])
    return genres[:TOP_GENRES] + [LabelCount(label="Otros", count=others)]


@router.get("/", response_model=StatsOut, summary="Estadísticas de lectura y avance de la meta anual")
def get_stats(
    year: int | None = Query(None, ge=MIN_YEAR, le=MAX_YEAR, description="Año a consultar (por defecto el actual)"),
    current_user_id: int = Depends(get_current_user),
):
    on = today()
    year = year or on.year
    owner = {"user_id": current_user_id}
    in_year = {**owner, "year_start": date(year, 1, 1), "year_end": date(year + 1, 1, 1)}

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # --- Biblioteca completa ------------------------------------------
        cursor.execute(
            f"""
            SELECT COUNT(*),
                   NVL(SUM(CASE WHEN b.reading_status = 'Quiero leer' THEN 1 ELSE 0 END), 0),
                   NVL(SUM(CASE WHEN b.reading_status = 'Leyendo' THEN 1 ELSE 0 END), 0),
                   NVL(SUM(CASE WHEN b.reading_status = 'Leído' THEN 1 ELSE 0 END), 0),
                   NVL(SUM(CASE WHEN b.reading_status = 'Leído' AND b.finished_at IS NULL THEN 1 ELSE 0 END), 0),
                   AVG(b.rating),
                   COUNT(b.rating)
            FROM books b
            WHERE {_OWNED}
            """,
            owner,
        )
        total, want, reading, read, undated, avg_rating, rated = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT b.rating, COUNT(*)
            FROM books b
            WHERE {_OWNED} AND b.rating IS NOT NULL
            GROUP BY b.rating
            ORDER BY b.rating
            """,
            owner,
        )
        ratings = [RatingCount(rating=r, count=c) for r, c in cursor.fetchall()]

        cursor.execute(
            f"""
            SELECT NVL(g.name, 'Sin género') AS genre, COUNT(*)
            FROM books b
            LEFT JOIN genres g ON g.id = b.genre_id
            WHERE {_OWNED}
            GROUP BY NVL(g.name, 'Sin género')
            ORDER BY COUNT(*) DESC, genre
            """,
            owner,
        )
        genres = _group_genres(cursor.fetchall())

        cursor.execute(
            f"""
            SELECT b.id, b.title, b.cover_url, b.started_at
            FROM books b
            WHERE {_OWNED} AND b.reading_status = 'Leyendo'
            ORDER BY b.started_at NULLS LAST, b.created_at
            FETCH FIRST {CURRENTLY_READING_LIMIT} ROWS ONLY
            """,
            owner,
        )
        currently_reading = []
        for book_id, title, cover_url, started in cursor.fetchall():
            started = as_date(started)
            currently_reading.append(CurrentlyReading(
                id=book_id, title=title, cover_url=cover_url, started_at=started,
                days_reading=(on - started).days if started else None,
            ))

        # --- Año consultado -----------------------------------------------
        cursor.execute(
            f"""
            SELECT EXTRACT(MONTH FROM b.finished_at), COUNT(*), NVL(SUM(b.page_count), 0)
            FROM books b
            WHERE {_READ_IN_YEAR}
            GROUP BY EXTRACT(MONTH FROM b.finished_at)
            """,
            in_year,
        )
        monthly = {int(m): (int(c), int(p)) for m, c, p in cursor.fetchall()}
        by_month = [
            MonthCount(month=m, books=monthly.get(m, (0, 0))[0], pages=monthly.get(m, (0, 0))[1])
            for m in range(1, 13)
        ]

        cursor.execute(
            f"""
            SELECT AVG(b.finished_at - b.started_at)
            FROM books b
            WHERE {_READ_IN_YEAR} AND b.started_at IS NOT NULL
            """,
            in_year,
        )
        avg_days = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT a.name, COUNT(*)
            FROM books b
            JOIN book_authors ba ON ba.book_id = b.id
            JOIN authors a ON a.id = ba.author_id
            WHERE {_READ_IN_YEAR}
            GROUP BY a.name
            ORDER BY COUNT(*) DESC, a.name
            FETCH FIRST {TOP_AUTHORS} ROWS ONLY
            """,
            in_year,
        )
        top_authors = [LabelCount(label=name, count=count) for name, count in cursor.fetchall()]

        cursor.execute(
            "SELECT target_books FROM reading_goals WHERE user_id = :user_id AND goal_year = :goal_year",
            {**owner, "goal_year": year},
        )
        goal_row = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT EXTRACT(YEAR FROM b.finished_at)
            FROM books b
            WHERE {_OWNED} AND b.reading_status = 'Leído' AND b.finished_at IS NOT NULL
            UNION
            SELECT goal_year FROM reading_goals WHERE user_id = :user_id
            """,
            owner,
        )
        years = {int(r[0]) for r in cursor.fetchall()}

    books_read = sum(m.books for m in by_month)
    goal = GoalProgress(**goal_progress(goal_row[0], books_read, year, on)) if goal_row else None

    return StatsOut(
        year_stats=YearStats(
            year=year,
            books_read=books_read,
            pages_read=sum(m.pages for m in by_month),
            avg_days_to_finish=round(float(avg_days), 1) if avg_days is not None else None,
            by_month=by_month,
            top_authors=top_authors,
            goal=goal,
        ),
        library=LibraryStats(
            total_books=int(total),
            want_to_read=int(want),
            reading=int(reading),
            read=int(read),
            read_without_date=int(undated),
            avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
            rated_books=int(rated),
            ratings=ratings,
            genres=genres,
            currently_reading=currently_reading,
        ),
        available_years=sorted(years | {on.year, year}, reverse=True),
    )
