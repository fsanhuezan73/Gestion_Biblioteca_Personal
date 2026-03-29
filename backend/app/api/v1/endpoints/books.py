from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

import oracledb

from app.db.session import get_db_connection
from app.core.security import get_current_user
from app.schemas.book import BookCreate, BookUpdate, BookOut

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
    cursor.execute(
        f"SELECT id FROM {table} WHERE LOWER(name) = LOWER(:n)", {"n": name}
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(f"INSERT INTO {table} (name) VALUES (:n)", {"n": name})
    cursor.execute(
        f"SELECT id FROM {table} WHERE LOWER(name) = LOWER(:n)", {"n": name}
    )
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
               b.cover_url
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
        authors=authors,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=List[BookOut],
    summary="Listar todos los libros del usuario",
)
def list_books(current_user_id: int = Depends(get_current_user)):
    """HU-02: Retorna todos los libros activos del usuario autenticado."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id,
                   b.title,
                   b.isbn,
                   b.year,
                   g.name   AS genre,
                   p.name   AS publisher,
                   b.created_at,
                   b.cover_url
            FROM books b
            LEFT JOIN genres     g ON g.id = b.genre_id
            LEFT JOIN publishers p ON p.id = b.publisher_id
            WHERE b.user_id = :user_id AND b.deleted_at IS NULL
            ORDER BY b.created_at DESC
            """,
            {"user_id": current_user_id},
        )
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
            result.append(BookOut(
                id=r[0], title=r[1], isbn=r[2], year=r[3],
                genre=r[4], publisher=r[5], created_at=r[6], cover_url=r[7], authors=authors,
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
            INSERT INTO books (user_id, title, isbn, year, genre_id, publisher_id, created_at, cover_url)
            VALUES (:user_id, :title, :isbn, :pub_year, :genre_id, :publisher_id, SYSTIMESTAMP, :cover_url)
            """,
            {
                "user_id": current_user_id,
                "title": book_in.title,
                "isbn": book_in.isbn,
                "pub_year": book_in.year,
                "genre_id": genre_id,
                "publisher_id": publisher_id,
                "cover_url": book_in.cover_url,
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

        scalar_map = {"title": "title", "isbn": "isbn", "year": "pub_year", "cover_url": "cover_url"}
        set_parts = []
        bind_params = {"bid": book_id}

        for field, bind in scalar_map.items():
            if field in updates:
                set_parts.append(f"{field} = :{bind}")
                bind_params[bind] = updates[field]

        if genre_id is not _UNSET:
            set_parts.append("genre_id = :genre_id")
            bind_params["genre_id"] = genre_id

        if publisher_id is not _UNSET:
            set_parts.append("publisher_id = :publisher_id")
            bind_params["publisher_id"] = publisher_id

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

        if set_parts:
            cursor.execute(
                f"UPDATE books SET {', '.join(set_parts)} WHERE id = :bid",
                bind_params,
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


