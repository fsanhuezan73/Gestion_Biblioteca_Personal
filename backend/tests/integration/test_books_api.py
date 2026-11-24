from contextlib import contextmanager, nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.books import get_current_user
from app.main import app


class FakeCursor:
    def __init__(self, fetchone_values=None, fetchall_values=None):
        self.fetchone_values = list(fetchone_values or [])
        self.fetchall_values = list(fetchall_values or [])

    def execute(self, *args, **kwargs):
        return None

    def var(self, _type):
        return Mock(**{"getvalue.return_value": [101]})

    def fetchone(self):
        if not self.fetchone_values:
            return None
        return self.fetchone_values.pop(0)

    def fetchall(self):
        if not self.fetchall_values:
            return []
        result = self.fetchall_values.pop(0)
        return result


class FakeConnection:
    def __init__(self, fetchone_values=None, fetchall_values=None):
        self.cursor_obj = FakeCursor(fetchone_values, fetchall_values)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


@contextmanager
def fake_db_connection(*, fetchone_values=None, fetchall_values=None):
    yield FakeConnection(fetchone_values, fetchall_values)


def build_client():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"):
        return TestClient(app)


def override_user():
    app.dependency_overrides[get_current_user] = lambda: 42


def clear_overrides():
    app.dependency_overrides.clear()


@pytest.mark.parametrize("extra,stored,expected", [
    ({}, None, []),
    ({"formats": ["kindle"]}, "kindle", ["kindle"]),
    (
        {"formats": ["kindle", "apple_books", "physical", "kindle"]},
        "apple_books,kindle,physical",
        ["physical", "kindle", "apple_books"],
    ),
])
def test_create_book_success(extra, stored, expected):
    client = build_client()
    override_user()

    fetchone_values = [
        None,
        (11,),
        None,
        (22,),
        None,
        (33,),
        (
            101,
            "1984",
            "9780451524935",
            1949,
            "Ciencia ficción",
            "Secker & Warburg",
            "2024-01-01T00:00:00",
            "https://example.com/cover.jpg",
            "Quiero leer",
            None,
            None,
            None,
            None,
            None,
            stored,
        ),
    ]
    fetchall_values = [[("George Orwell",)]]

    with patch("app.api.v1.endpoints.books.get_db_connection") as mock_db:
        conn = FakeConnection(fetchone_values, fetchall_values)
        conn.cursor_obj.execute = Mock()
        mock_db.return_value = nullcontext(conn)

        response = client.post(
            "/api/v1/books/",
            json={
                "title": "1984",
                "authors": ["George Orwell"],
                "isbn": "9780451524935",
                "year": 1949,
                "genre": "Ciencia ficción",
                "publisher": "Secker & Warburg",
                "cover_url": "https://example.com/cover.jpg",
                "reading_status": "Quiero leer",
                **extra,
            },
        )

    clear_overrides()
    assert response.status_code == 201
    assert response.json()["title"] == "1984"
    assert response.json()["formats"] == expected
    writes = [call.args[1] for call in conn.cursor_obj.execute.call_args_list if "INSERT INTO book_formats" in call.args[0]]
    assert writes == [{"bid": 101, "code": code} for code in expected]
    assert response.json()["authors"] == ["George Orwell"]
    assert response.json()["genre"] == "Ciencia ficción"


def test_create_book_requires_title_and_authors():
    client = build_client()
    override_user()

    response = client.post(
        "/api/v1/books/",
        json={
            "title": "",
            "authors": [],
        },
    )

    clear_overrides()
    assert response.status_code == 422


def test_list_books_returns_user_books():
    client = build_client()
    override_user()

    fetchone_values = []
    fetchall_values = [
        [
            (
                101,
                "1984",
                "9780451524935",
                1949,
                "Ciencia ficción",
                "Secker & Warburg",
                "2024-01-01T00:00:00",
                "https://example.com/cover.jpg",
                "Quiero leer",
                None,
                None,
                None,
                None,
                "apple_books,physical",
            )
        ],
        [("George Orwell",)],
    ]

    with patch("app.api.v1.endpoints.books.get_db_connection") as mock_db:
        mock_db.return_value = fake_db_connection(
            fetchone_values=fetchone_values,
            fetchall_values=fetchall_values,
        )

        response = client.get("/api/v1/books/?search=1984")

    clear_overrides()
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["title"] == "1984"
    assert response.json()[0]["authors"] == ["George Orwell"]
    assert response.json()[0]["formats"] == ["physical", "apple_books"]
