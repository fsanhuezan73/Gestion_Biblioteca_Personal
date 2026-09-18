from oracledb import DB_TYPE_CLOB

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.db.session import get_db_connection
from app.schemas.book import (
    VALID_READING_STATUSES, BookCreate, BookOut, BookPersonalUpdate, BookSummary, BookUpdate,
)

router = APIRouter(prefix="/books", tags=["Libros"])

# Sentinel: distingue "campo no enviado" de "campo enviado con valor None"
_UNSET = object()


# ---------------------------------------------------------------------------
# Helpers internos para los catálogos
# ---------------------------------------------------------------------------

def _get_or_create_id(cursor, table: str, name: str) -> int:
    """Obtiene el ID de un registro de catálogo; lo crea si no existe.

    Usa SELECT-first para evitar escrituras innecesarias y los bloqueos
    de índice (ORA-12860) que generan INSERT/MERGE en Oracle ADB.
    Solo hace INSERT cuando el registro realmente no existe."""
    allowed_tables = {"genres", "publishers", "authors"}
    if table not in allowed_tables:
        raise ValueError(f"Tabla de catálogo no permitida: {table}")

    if table == "genres":
        select_sql = "SELECT id FROM genres WHERE LOWER(name) = LOWER(:n)"
        insert_sql = "INSERT INTO genres (name) VALUES (:n)"
    elif table == "publishers":
        select_sql = "SELECT id FROM publishers WHERE LOWER(name) = LOWER(:n)"
        insert_sql = "INSERT INTO publishers (name) VALUES (:n)"
    else:
        select_sql = "SELECT id FROM authors WHERE LOWER(name) = LOWER(:n)"
        insert_sql = "INSERT INTO authors (name) VALUES (:n)"

    cursor.execute(select_sql, {"n": name})
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(insert_sql, {"n": name})
    cursor.execute(select_sql, {"n": name})
    return cursor.fetchone()[0]


def _fetch_book_row(cursor, book_id: int) -> BookOut | None:
    """Lee un libro completo con JOINs y retorna BookOut o None."""
    cursor.execute(
        """
        SELECT b.id,
               b.title,
               b.isbn,
               b.year,
               g.name   AS genre,
               p.name   AS publisher,
               b.created_at,
               b.cover_url,
               b.reading_status,
               b.rating,
               b.personal_notes
        FROM books b
        LEFT JOIN genres     g ON g.id = b.genre_id
        LEFT JOIN publishers p ON p.id = b.publisher_id
        WHERE b.id = :bid AND b.deleted_at IS NULL
        """,
        {"bid": book_id},
    )
    row = cursor.fetchone()
    if not row:
        return None

    cursor.execute(
        """
        SELECT a.name FROM authors a
        JOIN book_authors ba ON ba.author_id = a.id
        WHERE ba.book_id = :bid
        ORDER BY a.name
        """,
        {"bid": book_id},
    )
    authors = [r[0] for r in cursor.fetchall()]

    return BookOut(
        id=row[0],
        title=row[1],
        isbn=row[2],
        year=row[3],
        genre=row[4],
        publisher=row[5],
        created_at=row[6],
        cover_url=row[7],
        reading_status=row[8],
        rating=row[9],
        personal_notes=row[10].read() if hasattr(row[10], "read") else row[10],
        authors=authors,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[BookSummary],
    summary="Listar todos los libros del usuario",
)
def list_books(
    current_user_id: int = Depends(get_current_user),
    search: str | None = Query(None, description="Búsqueda libre en título, autor, ISBN, año, género"),
    genre: str | None = Query(None, description="Filtrar por género exacto"),
    reading_status: str | None = Query(None, description="Filtrar por estado de lectura"),
):
    """HU-02 + HU-05: Retorna libros activos del usuario con búsqueda y filtros."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Base query
        sql = """
            SELECT b.id,
                   b.title,
                   b.isbn,
                   b.year,
                   g.name   AS genre,
                   p.name   AS publisher,
                   b.created_at,
                   b.cover_url,
                   b.reading_status,
                   b.rating
            FROM books b
            LEFT JOIN genres     g ON g.id = b.genre_id
            LEFT JOIN publishers p ON p.id = b.publisher_id
            WHERE b.user_id = :user_id AND b.deleted_at IS NULL
        """
        bind = {"user_id": current_user_id}

        # Filtro por género exacto
        if genre:
            sql += " AND LOWER(g.name) = LOWER(:genre)"
            bind["genre"] = genre

        # Filtro por estado de lectura exacto
        if reading_status:
            sql += " AND b.reading_status = :reading_status"
            bind["reading_status"] = reading_status

        # Búsqueda libre: coincidencia parcial en título, autor, ISBN, año, género
        if search:
            sql += """
                AND (
                    LOWER(b.title) LIKE '%' || LOWER(:search) || '%'
                    OR LOWER(b.isbn) LIKE '%' || LOWER(:search) || '%'
                    OR TO_CHAR(b.year) LIKE '%' || :search || '%'
                    OR LOWER(g.name) LIKE '%' || LOWER(:search) || '%'
                    OR EXISTS (
                        SELECT 1 FROM book_authors ba2
                        JOIN authors a2 ON a2.id = ba2.author_id
                        WHERE ba2.book_id = b.id
                        AND LOWER(a2.name) LIKE '%' || LOWER(:search) || '%'
                    )
                )
            """
            bind["search"] = search

        sql += " ORDER BY b.created_at DESC"

        cursor.execute(sql, bind)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            cursor.execute(
                """
                SELECT a.name FROM authors a
                JOIN book_authors ba ON ba.author_id = a.id
                WHERE ba.book_id = :bid ORDER BY a.name
                """,
                {"bid": r[0]},
            )
            authors = [x[0] for x in cursor.fetchall()]
            result.append(BookSummary(
                id=r[0], title=r[1], isbn=r[2], year=r[3],
                genre=r[4], publisher=r[5], created_at=r[6], cover_url=r[7],
                reading_status=r[8], rating=r[9], authors=authors,
            ))
    return result


@router.post(
    "/",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir un nuevo libro",
)
def create_book(book_in: BookCreate, current_user_id: int = Depends(get_current_user)):
    """HU-01: Crea un libro asociado al usuario autenticado."""
    if not book_in.title or not book_in.title.strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio")
    if not book_in.authors:
        raise HTTPException(status_code=422, detail="Debe indicar al menos un autor")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Resolver catálogos (INSERT + catch ORA-00001, sin MERGE)
        genre_id = _get_or_create_id(cursor, "genres", book_in.genre) if book_in.genre else None
        publisher_id = _get_or_create_id(cursor, "publishers", book_in.publisher) if book_in.publisher else None
        author_ids = [
            _get_or_create_id(cursor, "authors", name.strip())
            for name in book_in.authors
            if name.strip()
        ]

        # Commit catálogos para liberar bloqueos de índice antes de
        # las operaciones FK (book_authors). Previene ORA-12860.
        conn.commit()

        cursor.execute(
            """
            INSERT INTO books (user_id, title, isbn, year, genre_id, publisher_id, created_at, cover_url, reading_status)
            VALUES (:user_id, :title, :isbn, :pub_year, :genre_id, :publisher_id, SYSTIMESTAMP, :cover_url, :reading_status)
            """,
            {
                "user_id": current_user_id,
                "title": book_in.title,
                "isbn": book_in.isbn,
                "pub_year": book_in.year,
                "genre_id": genre_id,
                "publisher_id": publisher_id,
                "cover_url": book_in.cover_url,
                "reading_status": book_in.reading_status or "Quiero leer",
            },
        )
        cursor.execute(
            "SELECT id FROM books WHERE user_id = :user_id AND title = :title ORDER BY created_at DESC FETCH FIRST 1 ROW ONLY",
            {"user_id": current_user_id, "title": book_in.title},
        )
        book_id = cursor.fetchone()[0]

        for aid in author_ids:
            cursor.execute(
                "INSERT INTO book_authors (book_id, author_id) VALUES (:bid, :aid)",
                {"bid": book_id, "aid": aid},
            )

        book = _fetch_book_row(cursor, book_id)

    return book


@router.get(
    "/genres",
    response_model=list[str],
    summary="Listar géneros usados por el usuario",
)
def list_genres(current_user_id: int = Depends(get_current_user)):
    """HU-05: Retorna los nombres de géneros que el usuario tiene asignados a sus libros."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT g.name
            FROM genres g
            JOIN books b ON b.genre_id = g.id
            WHERE b.user_id = :user_id AND b.deleted_at IS NULL
            ORDER BY g.name
            """,
            {"user_id": current_user_id},
        )
        return [r[0] for r in cursor.fetchall()]


@router.get(
    "/{book_id}",
    response_model=BookOut,
    summary="Obtener detalle de un libro",
)
def get_book(book_id: int, current_user_id: int = Depends(get_current_user)):
    """Retorna el detalle de un libro del usuario autenticado."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM books WHERE id = :bid AND user_id = :user_id AND deleted_at IS NULL",
            {"bid": book_id, "user_id": current_user_id},
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        book = _fetch_book_row(cursor, book_id)
    return book


@router.put(
    "/{book_id}",
    response_model=BookOut,
    summary="Actualizar datos de un libro",
)
def update_book(
    book_id: int,
    book_in: BookUpdate,
    current_user_id: int = Depends(get_current_user),
):
    """HU-03: Actualiza los campos enviados de un libro del usuario."""
    updates = book_in.model_dump(exclude_unset=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM books WHERE id = :bid AND user_id = :user_id AND deleted_at IS NULL",
            {"bid": book_id, "user_id": current_user_id},
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")

        # Resolver catálogos (INSERT + catch ORA-00001, sin MERGE)
        genre_id = _UNSET
        publisher_id = _UNSET
        author_ids = None

        if "genre" in updates:
            genre_id = (
                _get_or_create_id(cursor, "genres", updates["genre"])
                if updates["genre"]
                else None
            )
        if "publisher" in updates:
            publisher_id = (
                _get_or_create_id(cursor, "publishers", updates["publisher"])
                if updates["publisher"]
                else None
            )
        if "authors" in updates and updates["authors"] is not None:
            author_ids = [
                _get_or_create_id(cursor, "authors", name.strip())
                for name in updates["authors"]
                if name.strip()
            ]

        # Commit catálogos para liberar bloqueos de índice antes de
        # las operaciones FK (book_authors). Previene ORA-12860.
        conn.commit()

        scalar_map = {
            "title": {"sql": "UPDATE books SET title = :title WHERE id = :bid", "param": "title"},
            "isbn": {"sql": "UPDATE books SET isbn = :isbn WHERE id = :bid", "param": "isbn"},
            "year": {"sql": "UPDATE books SET year = :pub_year WHERE id = :bid", "param": "pub_year"},
            "cover_url": {"sql": "UPDATE books SET cover_url = :cover_url WHERE id = :bid", "param": "cover_url"},
            "reading_status": {
                "sql": "UPDATE books SET reading_status = :reading_status WHERE id = :bid",
                "param": "reading_status",
            },
        }

        for field, config in scalar_map.items():
            if field in updates:
                cursor.execute(config["sql"], {config["param"]: updates[field], "bid": book_id})

        if genre_id is not _UNSET:
            cursor.execute(
                "UPDATE books SET genre_id = :genre_id WHERE id = :bid",
                {"genre_id": genre_id, "bid": book_id},
            )

        if publisher_id is not _UNSET:
            cursor.execute(
                "UPDATE books SET publisher_id = :publisher_id WHERE id = :bid",
                {"publisher_id": publisher_id, "bid": book_id},
            )

        if author_ids is not None:
            # Diff-based: solo borrar las eliminadas, solo insertar las nuevas.
            # Evita DELETE+INSERT de la misma fila, que causa ORA-12860 en
            # Oracle ADB (BOOK_AUTHORS se comporta como IOT por tener PK compuesta
            # que abarca todas las columnas).
            cursor.execute(
                "SELECT author_id FROM book_authors WHERE book_id = :bid",
                {"bid": book_id},
            )
            current_aids = {r[0] for r in cursor.fetchall()}
            new_aids = set(author_ids)

            for aid in current_aids - new_aids:
                cursor.execute(
                    "DELETE FROM book_authors WHERE book_id = :bid AND author_id = :aid",
                    {"bid": book_id, "aid": aid},
                )
            for aid in new_aids - current_aids:
                cursor.execute(
                    "INSERT INTO book_authors (book_id, author_id) VALUES (:bid, :aid)",
                    {"bid": book_id, "aid": aid},
                )

        book = _fetch_book_row(cursor, book_id)

    return book


@router.patch(
    "/{book_id}/personal",
    response_model=BookOut,
    summary="Guardar valoración y notas privadas de un libro",
)
def update_personal_details(
    book_id: int,
    body: BookPersonalUpdate,
    current_user_id: int = Depends(get_current_user),
):
    """Campos omitidos se conservan; null elimina la valoración o las notas."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Indica una valoración o notas para actualizar")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Nombres de columna fijos; todos los valores se envían como parámetros.
        assignments = []
        if "rating" in updates:
            assignments.append("rating = :rating")
        if "personal_notes" in updates:
            assignments.append("personal_notes = :personal_notes")
            cursor.setinputsizes(personal_notes=DB_TYPE_CLOB)
        cursor.execute(
            "UPDATE books SET " + ", ".join(assignments)
            + " WHERE id = :bid AND user_id = :user_id AND deleted_at IS NULL",
            {**updates, "bid": book_id, "user_id": current_user_id},
        )
        # Mismo resultado para libros ajenos, eliminados o inexistentes.
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        book = _fetch_book_row(cursor, book_id)
    return book


@router.patch(
    "/{book_id}/status",
    response_model=BookOut,
    summary="Cambiar estado de lectura de un libro",
)
def update_reading_status(
    book_id: int,
    body: dict,
    current_user_id: int = Depends(get_current_user),
):
    """HU-06: Actualiza rápidamente el estado de lectura de un libro."""
    new_status = body.get("reading_status")
    if new_status not in VALID_READING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Estado inválido. Valores permitidos: {', '.join(VALID_READING_STATUSES)}",
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM books WHERE id = :bid AND user_id = :user_id AND deleted_at IS NULL",
            {"bid": book_id, "user_id": current_user_id},
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        cursor.execute(
            "UPDATE books SET reading_status = :status WHERE id = :bid",
            {"status": new_status, "bid": book_id},
        )
        book = _fetch_book_row(cursor, book_id)
    return book


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un libro (soft delete)",
)
def delete_book(book_id: int, current_user_id: int = Depends(get_current_user)):
    """HU-04: Marca el libro como eliminado (soft delete vía deleted_at)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM books WHERE id = :bid AND user_id = :user_id AND deleted_at IS NULL",
            {"bid": book_id, "user_id": current_user_id},
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        cursor.execute(
            "UPDATE books SET deleted_at = SYSTIMESTAMP WHERE id = :bid",
            {"bid": book_id},
        )


