from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from oracledb import DB_TYPE_CLOB

from app.main import app
from app.core.security import get_current_user


def book_row(rating=None, notes=None):
    return (101, "1984", None, 1949, None, None, None, None, "Quiero leer", rating, notes)


@pytest.fixture
def api():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchall.return_value = [("George Orwell",)]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def connection():
        yield conn

    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), patch(
        "app.api.v1.endpoints.books.get_db_connection", side_effect=connection
    ) as db:
        app.dependency_overrides[get_current_user] = lambda: 42
        try:
            with TestClient(app) as client:
                yield client, cursor, db
        finally:
            app.dependency_overrides.clear()


@pytest.mark.parametrize("body", [
    {"rating": 0}, {"rating": 6}, {"rating": -1}, {"rating": 2.5},
    {"rating": True}, {"rating": "5"}, {"personal_notes": 7},
    {"personal_notes": "a" * 5001}, {"user_id": 43, "rating": 5}, {},
])
def test_invalid_input_is_rejected_before_database_access(api, body):
    client, _, db = api
    response = client.patch("/api/v1/books/101/personal", json=body)
    assert response.status_code == 422
    db.assert_not_called()


@pytest.mark.parametrize("rating", [1, 2, 3, 4, 5, None])
def test_rating_updates_preserve_notes_and_scope_write_to_owner(api, rating):
    client, cursor, _ = api
    cursor.fetchone.return_value = book_row(rating, "Nota anterior")
    response = client.patch("/api/v1/books/101/personal", json={"rating": rating})
    assert response.status_code == 200
    assert response.json()["rating"] == rating
    assert response.json()["personal_notes"] == "Nota anterior"
    sql, params = cursor.execute.call_args_list[0].args
    assert "user_id = :user_id" in sql
    assert "deleted_at IS NULL" in sql
    assert "personal_notes =" not in sql
    assert params == {"rating": rating, "bid": 101, "user_id": 42}


@pytest.mark.parametrize("notes,expected", [
    (None, None), ("", None), ("   \n", None),
    ("Mi reseña\nUna cita con acentos: corazón 📚", "Mi reseña\nUna cita con acentos: corazón 📚"),
    ("📚" * 5000, "📚" * 5000),
    ("<script>alert('nota')</script>", "<script>alert('nota')</script>"),
])
def test_notes_use_clob_and_preserve_rating(api, notes, expected):
    client, cursor, _ = api
    lob = MagicMock()
    lob.read.return_value = expected
    cursor.fetchone.return_value = book_row(4, lob if expected else None)
    response = client.patch("/api/v1/books/101/personal", json={"personal_notes": notes})
    assert response.status_code == 200
    assert response.json()["personal_notes"] == expected
    assert response.json()["rating"] == 4
    cursor.setinputsizes.assert_called_once_with(personal_notes=DB_TYPE_CLOB)
    sql, params = cursor.execute.call_args_list[0].args
    assert "rating =" not in sql
    assert params["personal_notes"] == expected
    assert expected is None or expected not in sql


def test_both_fields_can_be_saved_and_cleared_together(api):
    client, cursor, _ = api
    for rating, notes in [(5, "Favorito"), (None, None)]:
        cursor.fetchone.return_value = book_row(rating, notes)
        response = client.patch("/api/v1/books/101/personal", json={
            "rating": rating, "personal_notes": notes,
        })
        assert response.status_code == 200
        assert response.json()["rating"] == rating
        assert response.json()["personal_notes"] == notes


def test_no_matching_owned_active_book_returns_404_without_reading_notes(api):
    client, cursor, _ = api
    cursor.rowcount = 0
    response = client.patch("/api/v1/books/999/personal", json={"rating": 5})
    assert response.status_code == 404
    cursor.fetchone.assert_not_called()
    assert cursor.execute.call_count == 1


def test_authentication_required_before_database_access(api):
    client, _, db = api
    app.dependency_overrides.clear()
    for method, url in [("patch", "/api/v1/books/101/personal"), ("get", "/api/v1/books/101")]:
        response = getattr(client, method)(url, **({"json": {"rating": 5}} if method == "patch" else {}))
        assert response.status_code == 401
    db.assert_not_called()


def test_owner_can_read_notes_after_reloading_detail(api):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(101,), book_row(5, "Relectura pendiente")]
    response = client.get("/api/v1/books/101")
    assert response.status_code == 200
    assert response.json()["personal_notes"] == "Relectura pendiente"
    assert response.json()["rating"] == 5
    sql, params = cursor.execute.call_args_list[0].args
    assert "user_id = :user_id" in sql
    assert params["user_id"] == 42


def test_foreign_or_deleted_book_detail_does_not_reveal_notes(api):
    client, cursor, _ = api
    cursor.fetchone.return_value = None
    response = client.get("/api/v1/books/101")
    assert response.status_code == 404
    assert cursor.execute.call_count == 1


def test_library_returns_rating_without_fetching_personal_notes(api):
    client, cursor, _ = api
    cursor.fetchall.side_effect = [[book_row(4)[:10]], [("George Orwell",)]]
    response = client.get("/api/v1/books/")
    assert response.status_code == 200
    assert response.json()[0]["rating"] == 4
    assert "personal_notes" not in response.json()[0]
    sql, params = cursor.execute.call_args_list[0].args
    assert "personal_notes" not in sql
    assert "user_id = :user_id" in sql
    assert params["user_id"] == 42


@pytest.mark.parametrize("method,url,body", [
    ("put", "/api/v1/books/101", {"title": "Nuevo título"}),
    ("patch", "/api/v1/books/101/status", {"reading_status": "Leído"}),
])
def test_existing_edits_do_not_overwrite_personal_details(api, method, url, body):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(101,), book_row(4, "Mis notas")]
    response = getattr(client, method)(url, json=body)
    assert response.status_code == 200
    assert response.json()["rating"] == 4
    assert response.json()["personal_notes"] == "Mis notas"
    writes = [call.args[0] for call in cursor.execute.call_args_list if call.args[0].startswith("UPDATE")]
    assert writes
    assert all("personal_notes" not in sql and "rating" not in sql for sql in writes)
