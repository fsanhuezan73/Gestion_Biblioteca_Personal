from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

TOKEN = "token-de-prueba-largo"


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.executed = []

    def execute(self, sql, *args, **kwargs):
        self.executed.append(sql)

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.cursor_obj = FakeCursor(row)

    def cursor(self):
        return self.cursor_obj


def build_client():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"):
        return TestClient(app)


def settings_with(token):
    return patch("app.main.get_settings", return_value=SimpleNamespace(healthcheck_token=token))


def test_health_db_ok_runs_sql():
    conn = FakeConnection((1,))

    @contextmanager
    def fake_db():
        yield conn

    with settings_with(TOKEN), patch("app.main.get_db_connection", fake_db):
        response = build_client().get("/health/db", headers={"X-Health-Token": TOKEN})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
    assert conn.cursor_obj.executed == ["SELECT 1 FROM DUAL"]


def test_health_db_returns_503_when_database_fails():
    @contextmanager
    def failing_db():
        raise RuntimeError("ORA-12541: secreto interno")
        yield  # pragma: no cover

    with settings_with(TOKEN), patch("app.main.get_db_connection", failing_db):
        response = build_client().get("/health/db", headers={"X-Health-Token": TOKEN})

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}
    assert "ORA" not in response.text


def test_health_db_rejects_missing_or_wrong_token():
    with settings_with(TOKEN), patch("app.main.get_db_connection") as mock_db:
        client = build_client()
        assert client.get("/health/db").status_code == 401
        assert client.get("/health/db", headers={"X-Health-Token": "otro"}).status_code == 401
    mock_db.assert_not_called()


def test_health_db_disabled_without_configured_token():
    with settings_with(""), patch("app.main.get_db_connection") as mock_db:
        response = build_client().get("/health/db", headers={"X-Health-Token": "lo-que-sea"})

    assert response.status_code == 404
    mock_db.assert_not_called()


def test_basic_health_does_not_need_token():
    assert build_client().get("/health").json() == {"status": "ok"}
