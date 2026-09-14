from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeCursor:
    def __init__(self, fetchone_responses=None):
        self.fetchone_responses = list(fetchone_responses or [])

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        if not self.fetchone_responses:
            return None
        return self.fetchone_responses.pop(0)


class FakeConnection:
    def __init__(self, fetchone_responses=None):
        self.cursor_obj = FakeCursor(fetchone_responses)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


@contextmanager
def fake_db_connection(*fetchone_responses):
    yield FakeConnection(list(fetchone_responses))


def build_client():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"):
        return TestClient(app)


def test_register_user_success():
    client = build_client()

    with patch("app.api.v1.endpoints.auth.get_db_connection") as mock_db, patch(
        "app.api.v1.endpoints.auth.hash_password", return_value="hashed-pass"
    ):
        mock_db.return_value = fake_db_connection(None, (42,))

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "JUAN@demo.com", "password": "Password123"},
        )

    assert response.status_code == 201
    assert response.json()["email"] == "juan@demo.com"
    assert response.json()["id"] == 42


def test_register_user_conflict():
    client = build_client()

    with patch("app.api.v1.endpoints.auth.get_db_connection") as mock_db:
        mock_db.return_value = fake_db_connection((7,))

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "juan@demo.com", "password": "Password123"},
        )

    assert response.status_code == 409
    assert "ya está registrado" in response.json()["detail"].lower()


def test_login_success():
    client = build_client()

    with patch("app.api.v1.endpoints.auth.get_db_connection") as mock_db, patch(
        "app.api.v1.endpoints.auth.verify_password", return_value=True
    ), patch("app.api.v1.endpoints.auth.create_access_token", return_value="test-token"):
        mock_db.return_value = fake_db_connection((7, "hashed-password"))

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "juan@demo.com", "password": "Password123"},
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-token"
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials():
    client = build_client()

    with patch("app.api.v1.endpoints.auth.get_db_connection") as mock_db, patch(
        "app.api.v1.endpoints.auth.verify_password", return_value=False
    ):
        mock_db.return_value = fake_db_connection((7, "hashed-password"))

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "juan@demo.com", "password": "WrongPassword"},
        )

    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"].lower()


def test_cors_preflight_allows_localhost_ports():
    client = build_client()

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5174"

