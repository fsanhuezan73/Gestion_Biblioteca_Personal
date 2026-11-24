from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

TODAY = date(2026, 7, 2)


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
        "app.api.v1.endpoints.goals.get_db_connection", side_effect=connection
    ) as goals_db, patch(
        "app.api.v1.endpoints.stats.get_db_connection", side_effect=connection
    ) as stats_db, patch(
        "app.api.v1.endpoints.books.get_db_connection", side_effect=connection
    ), patch("app.api.v1.endpoints.stats.today", return_value=TODAY), patch(
        "app.api.v1.endpoints.books.today", return_value=TODAY
    ):
        app.dependency_overrides[get_current_user] = lambda: 42
        try:
            with TestClient(app) as client:
                yield client, cursor, {"goals": goals_db, "stats": stats_db}
        finally:
            app.dependency_overrides.clear()


def all_params(cursor):
    return [call.args[1] for call in cursor.execute.call_args_list if len(call.args) > 1]


# ---------------------------------------------------------------------------
# Metas
# ---------------------------------------------------------------------------

def test_get_goal_returns_target(api):
    client, cursor, _ = api
    cursor.fetchone.return_value = (24,)
    response = client.get("/api/v1/goals/2026")
    assert response.status_code == 200
    assert response.json() == {"year": 2026, "target_books": 24}
    assert all_params(cursor)[0] == {"user_id": 42, "goal_year": 2026}


def test_get_missing_goal_returns_404(api):
    client, cursor, _ = api
    cursor.fetchone.return_value = None
    assert client.get("/api/v1/goals/2026").status_code == 404


def test_put_goal_updates_existing(api):
    client, cursor, _ = api
    cursor.rowcount = 1
    response = client.put("/api/v1/goals/2026", json={"target_books": 30})
    assert response.status_code == 200
    sqls = [call.args[0] for call in cursor.execute.call_args_list]
    assert len(sqls) == 1 and sqls[0].startswith("UPDATE reading_goals")


def test_put_goal_inserts_when_missing(api):
    client, cursor, _ = api
    cursor.rowcount = 0
    response = client.put("/api/v1/goals/2026", json={"target_books": 12})
    assert response.status_code == 200
    sqls = [call.args[0] for call in cursor.execute.call_args_list]
    assert sqls[1].startswith("INSERT INTO reading_goals")
    assert all(p["user_id"] == 42 for p in all_params(cursor))


@pytest.mark.parametrize("body", [
    {"target_books": 0}, {"target_books": 366}, {"target_books": "10"},
    {"target_books": 2.5}, {}, {"target_books": 10, "user_id": 7},
])
def test_put_goal_rejects_invalid_body(api, body):
    client, _, dbs = api
    assert client.put("/api/v1/goals/2026", json=body).status_code == 422
    dbs["goals"].assert_not_called()


@pytest.mark.parametrize("year", [1899, 2101])
def test_goal_year_out_of_range(api, year):
    client, _, dbs = api
    assert client.put(f"/api/v1/goals/{year}", json={"target_books": 5}).status_code == 422
    dbs["goals"].assert_not_called()


def test_delete_goal(api):
    client, cursor, _ = api
    cursor.rowcount = 1
    assert client.delete("/api/v1/goals/2026").status_code == 204
    cursor.rowcount = 0
    assert client.delete("/api/v1/goals/2026").status_code == 404


def test_goals_and_stats_require_auth():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"):
        client = TestClient(app)
        assert client.get("/api/v1/goals/2026").status_code == 401
        assert client.get("/api/v1/stats/").status_code == 401


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------

def set_stats_rows(cursor, *, goal=(24,), monthly=None, genres=None):
    cursor.fetchone.side_effect = [
        (20, 5, 2, 13, 3, 4.25, 8),  # totales de la biblioteca
        (12.5,),                       # promedio de días
        goal,                          # meta del año
    ]
    cursor.fetchall.side_effect = [
        [(3, 2), (4, 2), (5, 4)],                                   # valoraciones
        genres if genres is not None else [("Novela", 10), ("Ensayo", 6), ("Sin género", 4)],
        [(7, "Dune", None, datetime(2026, 6, 22)), (8, "Sin fecha", None, None)],
        monthly if monthly is not None else [(1, 2, 600), (3, 4, 1200), (6, 4, 900)],
        [("Ursula K. Le Guin", 3), ("Borges", 2)],
        [
            (31, "Los desposeídos", "Ursula K. Le Guin", datetime(2026, 5, 20), datetime(2026, 6, 15), 5, 400),
            (32, "Ficciones", "Borges", None, datetime(2026, 3, 2), None, None),
        ],
        [(2025,), (2026,)],
        [("physical", 15), ("kindle", 8), (None, 3)],
    ]


def test_stats_aggregates_year_and_library(api):
    client, cursor, _ = api
    set_stats_rows(cursor)
    response = client.get("/api/v1/stats/?year=2026")
    assert response.status_code == 200
    data = response.json()

    year = data["year_stats"]
    assert year["year"] == 2026
    assert year["books_read"] == 10
    assert year["pages_read"] == 2700
    assert year["avg_days_to_finish"] == 12.5
    assert len(year["by_month"]) == 12
    assert year["by_month"][2] == {"month": 3, "books": 4, "pages": 1200}
    assert year["by_month"][1] == {"month": 2, "books": 0, "pages": 0}
    assert year["top_authors"][0] == {"label": "Ursula K. Le Guin", "count": 3}
    assert year["books_read_list"][0] == {
        "id": 31, "title": "Los desposeídos", "authors": "Ursula K. Le Guin",
        "started_at": "2026-05-20", "finished_at": "2026-06-15", "days_to_finish": 26,
        "rating": 5, "page_count": 400,
    }
    assert year["books_read_list"][1]["days_to_finish"] is None
    assert year["goal"]["target_books"] == 24
    assert year["goal"]["status"] == "behind"  # 10 leídos vs ≈12 esperados

    lib = data["library"]
    assert lib["total_books"] == 20
    assert lib["formats"] == {"physical": 15, "kindle": 8, "apple_books": 0, "without_format": 3}
    assert (lib["want_to_read"], lib["reading"], lib["read"]) == (5, 2, 13)
    assert lib["read_without_date"] == 3
    assert lib["avg_rating"] == 4.25
    assert lib["ratings"] == [{"rating": 3, "count": 2}, {"rating": 4, "count": 2}, {"rating": 5, "count": 4}]
    assert lib["currently_reading"][0]["days_reading"] == 10
    assert lib["currently_reading"][1]["days_reading"] is None

    assert data["available_years"] == [2026, 2025]


def test_stats_scopes_every_query_to_user_and_year(api):
    client, cursor, _ = api
    set_stats_rows(cursor)
    client.get("/api/v1/stats/?year=2025")
    params = all_params(cursor)
    assert params and all(p["user_id"] == 42 for p in params)
    year_params = [p for p in params if "year_start" in p]
    assert year_params and all(
        p["year_start"] == date(2025, 1, 1) and p["year_end"] == date(2026, 1, 1) for p in year_params
    )
    sqls = [call.args[0] for call in cursor.execute.call_args_list]
    assert all("user_id = :user_id" in sql for sql in sqls)
    assert all("deleted_at IS NULL" in sql for sql in sqls if "FROM books" in sql)
    assert all_params(cursor)[-1] == {"user_id": 42}


def test_stats_empty_year_without_goal(api):
    client, cursor, _ = api
    set_stats_rows(cursor, goal=None, monthly=[])
    cursor.fetchone.side_effect = [(0, 0, 0, 0, 0, None, 0), (None,), None]
    response = client.get("/api/v1/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["year_stats"]["year"] == 2026  # año actual por defecto
    assert data["year_stats"]["books_read"] == 0
    assert data["year_stats"]["goal"] is None
    assert data["year_stats"]["avg_days_to_finish"] is None
    assert data["library"]["avg_rating"] is None


def test_stats_groups_extra_genres_as_others(api):
    client, cursor, _ = api
    genres = [(f"G{i}", 10 - i) for i in range(10)]
    set_stats_rows(cursor, genres=genres)
    labels = [g["label"] for g in client.get("/api/v1/stats/").json()["library"]["genres"]]
    assert len(labels) == 8 and labels[-1] == "Otros"


def test_stats_rejects_invalid_year(api):
    client, _, dbs = api
    assert client.get("/api/v1/stats/?year=1800").status_code == 422
    dbs["stats"].assert_not_called()


# ---------------------------------------------------------------------------
# Fechas automáticas en libros
# ---------------------------------------------------------------------------

def book_row(status="Leído", started=None, finished=None, formats=None):
    return (101, "1984", None, 1949, None, None, None, None, status, None, None, started, finished, 328, formats)


def update_params(cursor):
    return [
        call.args[1] for call in cursor.execute.call_args_list
        if call.args[0].startswith("UPDATE books SET") and "started_at" in call.args[0]
    ]


def test_status_change_to_read_sets_finish_date(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [(101, "Leyendo", datetime(2026, 6, 1), None), book_row()]
    response = client.patch("/api/v1/books/101/status", json={"reading_status": "Leído"})
    assert response.status_code == 200
    (params,) = update_params(cursor)
    assert params["started_at"] == date(2026, 6, 1)
    assert params["finished_at"] == TODAY


def test_status_change_to_want_clears_dates(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [(101, "Leído", datetime(2026, 6, 1), datetime(2026, 6, 20)), book_row()]
    client.patch("/api/v1/books/101/status", json={"reading_status": "Quiero leer"})
    (params,) = update_params(cursor)
    assert params["started_at"] is None and params["finished_at"] is None


def test_same_status_keeps_dates(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [(101, "Leído", datetime(2026, 6, 1), datetime(2026, 6, 20)), book_row()]
    client.patch("/api/v1/books/101/status", json={"reading_status": "Leído"})
    (params,) = update_params(cursor)
    assert params["finished_at"] == date(2026, 6, 20)


def test_put_explicit_dates_override_automatic_ones(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [(101, "Leyendo", None, None), book_row()]
    response = client.put("/api/v1/books/101", json={
        "reading_status": "Leído", "started_at": "2026-03-01", "finished_at": "2026-03-20", "page_count": 328,
    })
    assert response.status_code == 200
    (params,) = update_params(cursor)
    assert params == {"started_at": date(2026, 3, 1), "finished_at": date(2026, 3, 20), "bid": 101}
    page_updates = [c.args[1] for c in cursor.execute.call_args_list if "page_count = :page_count" in c.args[0]]
    assert page_updates == [{"page_count": 328, "bid": 101}]


def test_put_without_date_changes_does_not_write_dates(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [(101, "Leído", None, datetime(2026, 6, 20)), book_row()]
    client.put("/api/v1/books/101", json={"title": "Nuevo"})
    assert update_params(cursor) == []


@pytest.mark.parametrize("body,stored,existing,expected_formats,expected_writes", [
    ({"title": "Nuevo"}, "kindle,physical", [], ["physical", "kindle"], []),
    ({"formats": []}, None, [("kindle",)], [], [("DELETE", "kindle")]),
    ({"formats": ["apple_books", "physical"]}, "apple_books,physical", [("physical",), ("kindle",)],
     ["physical", "apple_books"], [("DELETE", "kindle"), ("INSERT", "apple_books")]),
    ({"formats": ["kindle", "kindle"]}, "kindle", [("kindle",)], ["kindle"], []),
])
def test_put_formats_only_changes_requested_associations(api, body, stored, existing, expected_formats, expected_writes):
    client, cursor, _ = api
    if "formats" in body:
        cursor.fetchone.side_effect = [(101, "Leído", None, None), (101,), book_row(formats=stored)]
        cursor.fetchall.side_effect = [existing, []]
    else:
        cursor.fetchone.side_effect = [(101, "Leído", None, None), book_row(formats=stored)]
        cursor.fetchall.return_value = []

    response = client.put("/api/v1/books/101", json=body)
    assert response.status_code == 200
    calls = [call.args for call in cursor.execute.call_args_list]
    assert any("FOR UPDATE" in sql for sql, _ in calls) == ("formats" in body)
    assert response.json()["formats"] == expected_formats
    assert [(sql.split()[0], params["code"]) for sql, params in calls
            if sql.startswith(("DELETE FROM book_formats", "INSERT INTO book_formats"))] == expected_writes


def test_format_updates_do_not_touch_foreign_or_deleted_books(api):
    client, cursor, _ = api
    cursor.fetchone.return_value = None
    assert client.put("/api/v1/books/101", json={"formats": ["physical"]}).status_code == 404
    (call,) = cursor.execute.call_args_list
    assert "user_id = :user_id AND deleted_at IS NULL" in call.args[0]


@pytest.mark.parametrize("method,url,body", [
    ("get", "/api/v1/books/?format=audiobook", None),
    ("get", "/api/v1/books/?format=kindle&without_format=true", None),
    ("post", "/api/v1/books/", {"title": "1984", "authors": ["George Orwell"], "formats": ["ebook"]}),
    ("put", "/api/v1/books/101", {"formats": None}),
])
def test_book_format_validation(api, method, url, body):
    client, cursor, _ = api
    assert client.request(method, url, json=body).status_code == 422
    cursor.execute.assert_not_called()


def test_list_books_combines_all_formats_with_other_filters(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    response = client.get(
        "/api/v1/books/?format=kindle&format=physical&format=physical&search=Dune&genre=Novela&reading_status=Leído"
    )
    assert response.status_code == 200
    (call,) = cursor.execute.call_args_list
    sql, params = call.args
    assert "b.user_id = :user_id AND b.deleted_at IS NULL" in sql
    assert sql.count("AND EXISTS (SELECT 1 FROM book_formats") == 2
    assert params == {
        "user_id": 42, "genre": "Novela", "reading_status": "Leído", "search": "Dune",
        "format_0": "physical", "format_1": "kindle",
    }


def test_list_books_can_filter_without_format(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    assert client.get("/api/v1/books/?without_format=true").status_code == 200
    assert "AND NOT EXISTS (SELECT 1 FROM book_formats" in cursor.execute.call_args.args[0]


@pytest.mark.parametrize("body,message", [
    ({"started_at": "2026-06-10", "finished_at": "2026-06-01"}, "anterior"),
    ({"finished_at": "2026-12-31"}, "futura"),
    ({"reading_status": "Terminado"}, "Estado inválido"),
    ({"reading_status": None}, "nulo"),
    ({"page_count": 0}, None),
])
def test_put_rejects_invalid_reading_data(api, body, message):
    client, cursor, _ = api
    cursor.fetchone.side_effect = [(101, "Leído", None, None)]
    response = client.put("/api/v1/books/101", json=body)
    assert response.status_code == 422
    if message:
        assert message in response.json()["detail"]
    assert not [c for c in cursor.execute.call_args_list if c.args[0].startswith("UPDATE")]


def insert_params(cursor):
    return [c.args[1] for c in cursor.execute.call_args_list if "INSERT INTO books" in c.args[0]][0]


@pytest.mark.parametrize("extra,expected", [
    ({}, (None, TODAY)),                                    # automático
    ({"finished_at": None}, (None, None)),                  # null explícito gana
    ({"started_at": "2025-01-05", "finished_at": "2025-02-01"}, (date(2025, 1, 5), date(2025, 2, 1))),
])
def test_create_read_book_dates(api, extra, expected):
    client, cursor, _ = api
    cursor.fetchall.return_value = [("George Orwell",)]
    cursor.var.return_value.getvalue.return_value = [101]
    cursor.fetchone.side_effect = [(1,), book_row()]
    response = client.post("/api/v1/books/", json={
        "title": "1984", "authors": ["George Orwell"], "reading_status": "Leído", **extra,
    })
    assert response.status_code == 201
    params = insert_params(cursor)
    assert (params["started_at"], params["finished_at"]) == expected


def test_list_books_can_filter_read_books_without_finish_date(api):
    client, cursor, _ = api
    cursor.fetchall.side_effect = [[], []]
    assert client.get("/api/v1/books/?without_finish_date=true").status_code == 200
    sql = cursor.execute.call_args_list[0].args[0]
    assert "b.finished_at IS NULL" in sql and "reading_status = 'Leído'" in sql


# ---------------------------------------------------------------------------
# Comprobación de ISBN (escáner)
# ---------------------------------------------------------------------------

def test_check_isbn_finds_owned_book_ignoring_format(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = [(101, "1984")]
    response = client.get("/api/v1/books/check-isbn", params={"isbn": "978-0-451-52493-5"})
    assert response.status_code == 200
    assert response.json() == {"isbn": "9780451524935", "exists": True, "books": [{"id": 101, "title": "1984"}]}
    sql, params = cursor.execute.call_args_list[0].args
    assert "user_id = :user_id" in sql and "deleted_at IS NULL" in sql
    assert params == {"user_id": 42, "isbn13": "9780451524935", "isbn10": "0451524934"}


def test_check_isbn_not_found(api):
    client, cursor, _ = api
    cursor.fetchall.return_value = []
    response = client.get("/api/v1/books/check-isbn", params={"isbn": "9791032305690"})
    assert response.json()["exists"] is False
    assert cursor.execute.call_args_list[0].args[1]["isbn10"] == "9791032305690"


@pytest.mark.parametrize("isbn", ["123", "9780451524936", "9771234567003"])
def test_check_isbn_rejects_invalid(api, isbn):
    client, cursor, _ = api
    assert client.get("/api/v1/books/check-isbn", params={"isbn": isbn}).status_code == 422
    cursor.execute.assert_not_called()


def test_lookup_endpoint_validates_and_uses_isbn13(api):
    client, cursor, _ = api
    fake = {"isbn": "9780306406157", "found": True, "title": "T", "authors": ["A"], "publisher": None,
            "year": None, "page_count": None, "cover_url": None, "sources": {"title": "openlibrary"},
            "unavailable_sources": []}
    with patch("app.api.v1.endpoints.books.lookup_isbn", return_value=fake) as lookup:
        response = client.get("/api/v1/books/lookup", params={"isbn": "0-306-40615-2"})
    assert response.status_code == 200 and response.json()["title"] == "T"
    assert lookup.call_args.args[0] == "9780306406157"
    assert client.get("/api/v1/books/lookup", params={"isbn": "123"}).status_code == 422


def test_lookup_requires_auth():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"):
        assert TestClient(app).get("/api/v1/books/lookup", params={"isbn": "9780306406157"}).status_code == 401
