from contextlib import contextmanager
from unittest.mock import patch
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.core.password_recovery import InvalidCurrentPassword, UnchangedPassword


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
    ), patch("app.api.v1.endpoints.auth.create_access_token", return_value="test-token") as mock_token:
        mock_db.return_value = fake_db_connection((7, "hashed-password", 2))

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "juan@demo.com", "password": "Password123"},
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-token"
    assert response.json()["token_type"] == "bearer"
    mock_token.assert_called_once_with(data={"sub": "7", "auth_version": 2})


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


def test_password_reset_request_is_disabled_until_mail_is_configured():
    client = build_client()
    response = client.post("/api/v1/auth/password-reset/request", json={"email": "user@example.com"})
    assert response.status_code == 503


def test_password_reset_request_rejects_incomplete_mail_configuration():
    client = build_client()
    settings = SimpleNamespace(password_reset_enabled=True)
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings), patch(
        "app.api.v1.endpoints.auth.mail_configured", return_value=False
    ), patch("app.api.v1.endpoints.auth.issue_password_reset") as issue:
        response = client.post("/api/v1/auth/password-reset/request", json={"email": "user@example.com"})
    assert response.status_code == 503
    issue.assert_not_called()


def test_password_reset_request_has_same_response_for_existing_and_unknown_email():
    client = build_client()
    settings = SimpleNamespace(password_reset_enabled=True)
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings), patch(
        "app.api.v1.endpoints.auth.mail_configured", return_value=True
    ), patch(
        "app.api.v1.endpoints.auth.issue_password_reset", side_effect=["secret", None]
    ) as issue, patch("app.api.v1.endpoints.auth.send_password_reset_link") as sender:
        existing = client.post("/api/v1/auth/password-reset/request", json={"email": "USER@example.com"})
        unknown = client.post("/api/v1/auth/password-reset/request", json={"email": "unknown@example.com"})

    assert existing.status_code == unknown.status_code == 200
    assert existing.json() == unknown.json()
    assert "secret" not in str(existing.json())
    assert issue.call_count == 2
    sender.assert_called_once_with("user@example.com", "secret")


def test_password_reset_request_hides_mail_delivery_error():
    client = build_client()
    settings = SimpleNamespace(password_reset_enabled=True)
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings), patch(
        "app.api.v1.endpoints.auth.mail_configured", return_value=True
    ), patch(
        "app.api.v1.endpoints.auth.issue_password_reset", return_value="secret"
    ), patch("app.api.v1.endpoints.auth.send_password_reset_link", side_effect=RuntimeError("smtp failed")):
        response = client.post("/api/v1/auth/password-reset/request", json={"email": "user@example.com"})

    assert response.status_code == 200
    assert "secret" not in str(response.json())


def test_password_reset_confirm_is_disabled_until_mail_is_configured():
    client = build_client()
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "a" * 43, "new_password": "new-password"},
    )
    assert response.status_code == 503


def test_password_reset_confirm_success_does_not_log_in_automatically():
    client = build_client()
    settings = SimpleNamespace(password_reset_enabled=True)
    with patch("app.api.v1.endpoints.auth.get_settings", return_value=settings), patch(
        "app.api.v1.endpoints.auth.mail_configured", return_value=True
    ), patch(
        "app.api.v1.endpoints.auth.confirm_password_reset"
    ) as confirm:
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": "a" * 43, "new_password": "new-password"},
        )

    assert response.status_code == 200
    assert "access_token" not in response.json()
    confirm.assert_called_once_with("a" * 43, "new-password")


def test_password_reset_confirm_rejects_short_and_oversized_passwords():
    client = build_client()
    for password in ("short", "é" * 40):
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": "a" * 43, "new_password": password},
        )
        assert response.status_code == 422


def test_password_change_requires_authentication():
    client = build_client()
    response = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "current-password", "new_password": "new-password"},
    )
    assert response.status_code == 401


def test_password_change_calls_authenticated_user_and_requires_new_login():
    client = build_client()
    app.dependency_overrides[get_current_user] = lambda: 7
    try:
        with patch("app.api.v1.endpoints.auth.change_password") as change:
            response = client.post(
                "/api/v1/auth/password/change",
                json={"current_password": "current-password", "new_password": "new-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "access_token" not in response.json()
    change.assert_called_once_with(7, "current-password", "new-password")


def test_password_change_rejects_invalid_current_or_unchanged_password():
    client = build_client()
    app.dependency_overrides[get_current_user] = lambda: 7
    try:
        for error in (InvalidCurrentPassword, UnchangedPassword):
            with patch("app.api.v1.endpoints.auth.change_password", side_effect=error):
                response = client.post(
                    "/api/v1/auth/password/change",
                    json={"current_password": "current-password", "new_password": "new-password"},
                )
            assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
