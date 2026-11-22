from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from oracledb import DB_TYPE_BLOB

from app.core.covers import MAX_COVER_BYTES
from app.core.security import get_current_user
from app.main import app
from app.schemas.book import BookOut

COVER_ID = "0123456789abcdef0123456789abcdef"
OTHER_ID = "fedcba9876543210fedcba9876543210"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 64
COVER_URL = f"https://api.example.com/api/v1/covers/{COVER_ID}"


@pytest.fixture
def api():
    cursor = MagicMock()
    cursor.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def connection():
        yield conn

    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), patch(
        "app.api.v1.endpoints.covers.get_db_connection", side_effect=connection
    ) as covers_db, patch(
        "app.api.v1.endpoints.books.get_db_connection", side_effect=connection
    ):
        app.dependency_overrides[get_current_user] = lambda: 42
        try:
            with TestClient(app) as client:
                yield client, cursor, covers_db
        finally:
            app.dependency_overrides.clear()


def executed_sql(cursor):
    return [" ".join(call.args[0].split()) for call in cursor.execute.call_args_list]


def test_upload_stores_blob_for_current_user(api):
    client, cursor, _ = api
    response = client.post("/api/v1/covers", content=JPEG, headers={"Content-Type": "image/jpeg"})

    assert response.status_code == 201
    body = response.json()
    assert len(body["id"]) == 32
    assert body == {"id": body["id"], "content_type": "image/jpeg", "byte_size": len(JPEG)}
    cursor.setinputsizes.assert_called_once_with(data=DB_TYPE_BLOB)
    sql, params = cursor.execute.call_args.args
    assert "INSERT INTO book_covers" in sql
    assert params == {
        "id": body["id"], "user_id": 42, "content_type": "image/jpeg",
        "byte_size": len(JPEG), "data": JPEG,
    }


def test_upload_detects_type_from_content_not_header(api):
    client, cursor, _ = api
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    response = client.post("/api/v1/covers", content=png, headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 201
    assert response.json()["content_type"] == "image/png"


@pytest.mark.parametrize(
    ("content", "status"),
    [
        (b"", 422),
        (b"<svg onload='alert(1)'></svg>", 415),
        (b"GIF89a" + b"\x00" * 10, 415),
        (b"\xff\xd8\xff" + b"\x00" * MAX_COVER_BYTES, 413),
    ],
)
def test_invalid_uploads_never_reach_database(api, content, status):
    client, _, covers_db = api
    response = client.post("/api/v1/covers", content=content, headers={"Content-Type": "image/jpeg"})
    assert response.status_code == status
    covers_db.assert_not_called()


def test_upload_requires_authentication(api):
    client, _, covers_db = api
    app.dependency_overrides.clear()
    response = client.post("/api/v1/covers", content=JPEG)
    assert response.status_code == 401
    covers_db.assert_not_called()


def test_get_cover_returns_image_with_long_cache(api):
    client, cursor, _ = api
    blob = MagicMock()
    blob.read.return_value = JPEG
    cursor.fetchone.return_value = ("image/jpeg", blob)
    app.dependency_overrides.clear()  # público: sin JWT

    response = client.get(f"/api/v1/covers/{COVER_ID}")

    assert response.status_code == 200
    assert response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert "immutable" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert cursor.execute.call_args.args[1] == {"id": COVER_ID}


def test_get_missing_cover_returns_404(api):
    client, cursor, _ = api
    cursor.fetchone.return_value = None
    assert client.get(f"/api/v1/covers/{COVER_ID}").status_code == 404


@pytest.mark.parametrize("cover_id", ["abc", "ABCDEF0123456789ABCDEF0123456789", "x" * 32])
def test_get_cover_with_invalid_id_skips_database(api, cover_id):
    client, _, covers_db = api
    assert client.get(f"/api/v1/covers/{cover_id}").status_code == 404
    covers_db.assert_not_called()


def _book(cover_url):
    return BookOut(id=7, title="Libro", authors=["Autora"], cover_url=cover_url,
                   reading_status="Quiero leer", created_at=datetime(2026, 11, 22))


@pytest.mark.parametrize(
    ("new_url", "deleted"),
    [
        (f"https://api.example.com/api/v1/covers/{OTHER_ID}", True),
        ("https://covers.openlibrary.org/b/id/1-M.jpg", True),
        (None, True),
        (COVER_URL, False),
    ],
)
def test_replacing_uploaded_cover_deletes_unused_image(api, new_url, deleted):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(7, "Quiero leer", None, None), (COVER_URL,)]
    with patch("app.api.v1.endpoints.books._fetch_book_row", return_value=_book(new_url)):
        response = client.put("/api/v1/books/7", json={"cover_url": new_url})

    assert response.status_code == 200
    deletes = [c for c in cursor.execute.call_args_list if "DELETE FROM book_covers" in c.args[0]]
    if deleted:
        assert len(deletes) == 1
        assert deletes[0].args[1] == {"cover_id": COVER_ID, "user_id": 42}
        assert "NOT EXISTS" in deletes[0].args[0]
    else:
        assert deletes == []


def test_editing_without_cover_field_keeps_uploaded_image(api):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(7, "Quiero leer", None, None)]
    with patch("app.api.v1.endpoints.books._fetch_book_row", return_value=_book(COVER_URL)):
        response = client.put("/api/v1/books/7", json={"title": "Nuevo título"})
    assert response.status_code == 200
    assert not any("book_covers" in sql for sql in executed_sql(cursor))


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:image/png;base64,AAAA", "//evil.example/x.jpg",
                                 "https://example.com/" + "a" * 500])
def test_book_rejects_unsafe_or_too_long_cover_urls(api, url):
    client, _, _ = api
    response = client.put("/api/v1/books/7", json={"cover_url": url})
    assert response.status_code == 422


def test_blank_cover_url_is_stored_as_null(api):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(7, "Quiero leer", None, None), (None,)]
    with patch("app.api.v1.endpoints.books._fetch_book_row", return_value=_book(None)):
        response = client.put("/api/v1/books/7", json={"cover_url": "   "})
    assert response.status_code == 200
    updates = [c.args[1] for c in cursor.execute.call_args_list if "SET cover_url" in c.args[0]]
    assert updates == [{"cover_url": None, "bid": 7}]
