"""Flujo HTTP completo con Oracle y correo simulados; no toca servicios reales."""

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.main import app


class SimulatedOracle:
    def __init__(self):
        self.email = "user@example.com"
        self.password_hash = hash_password("OldPassword123")
        self.auth_version = 0
        self.requests = []
        self.reset_tokens = []

    def cursor(self):
        return SimulatedCursor(self)


class SimulatedCursor:
    def __init__(self, db):
        self.db = db
        self.result = None

    def execute(self, sql, params=None):
        query = " ".join(sql.lower().split())
        params = params or {}
        self.result = None

        if query.startswith("lock table password_reset_requests"):
            return
        if query.startswith("select count(*) from password_reset_requests"):
            key = "email_fingerprint" if "email_fingerprint" in query else "origin_fingerprint"
            count = sum(
                row[key] == params["fingerprint"] and row["created_at"] >= params["cutoff"]
                for row in self.db.requests
            )
            self.result = (count,)
            return
        if query.startswith("insert into password_reset_requests"):
            self.db.requests.append(params.copy())
            return
        if query.startswith("select id from users where email"):
            self.result = (7,) if params["email"] == self.db.email else None
            return
        if query.startswith("insert into password_reset_tokens"):
            self.db.reset_tokens.append({**params, "id": len(self.db.reset_tokens) + 1, "consumed": False})
            return
        if query.startswith("select id, user_id from password_reset_tokens"):
            match = next((
                row for row in self.db.reset_tokens
                if row["token_hash"] == params["token_hash"]
                and not row["consumed"]
                and row["expires_at"] > datetime.now(timezone.utc)
            ), None)
            self.result = (match["id"], match["user_id"]) if match else None
            return
        if query.startswith("select hashed_password from users"):
            self.result = (self.db.password_hash,) if params["user_id"] == 7 else None
            return
        if query.startswith("update users set hashed_password"):
            self.db.password_hash = params["hashed_password"]
            self.db.auth_version += 1
            return
        if query.startswith("update /*+ disable_parallel_dml */ password_reset_tokens"):
            for row in self.db.reset_tokens:
                if row["user_id"] == params["user_id"]:
                    row["consumed"] = True
            return
        if query.startswith("select id, hashed_password, auth_version from users"):
            self.result = (7, self.db.password_hash, self.db.auth_version)
            return
        if query.startswith("select auth_version from users"):
            self.result = (self.db.auth_version,)
            return
        if query.startswith("select distinct g.name"):
            self.result = []
            return
        raise AssertionError(f"SQL no simulado: {query}")

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result or []


@contextmanager
def connection(db):
    yield db


def test_request_to_reset_revokes_old_jwt_and_blocks_replay():
    db = SimulatedOracle()
    sent_links = []
    settings = SimpleNamespace(password_reset_enabled=True)

    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), patch(
        "app.api.v1.endpoints.auth.get_db_connection", side_effect=lambda: connection(db)
    ), patch("app.core.security.get_db_connection", side_effect=lambda: connection(db)), patch(
        "app.core.password_recovery.get_db_connection", side_effect=lambda: connection(db)
    ), patch("app.api.v1.endpoints.books.get_db_connection", side_effect=lambda: connection(db)), patch(
        "app.api.v1.endpoints.auth.get_settings", return_value=settings
    ), patch("app.api.v1.endpoints.auth.mail_configured", return_value=True), patch(
        "app.api.v1.endpoints.auth.send_password_reset_link",
        side_effect=lambda email, token: sent_links.append((email, token)),
    ):
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": db.email, "password": "OldPassword123"},
            )
            assert login.status_code == 200
            old_jwt = login.json()["access_token"]
            assert client.get(
                "/api/v1/books/genres", headers={"Authorization": f"Bearer {old_jwt}"}
            ).status_code == 200

            request = client.post("/api/v1/auth/password-reset/request", json={"email": db.email})
            assert request.status_code == 200
            assert len(sent_links) == 1
            email, token = sent_links[0]
            assert email == db.email
            assert token not in str(request.json())
            assert token not in str(db.reset_tokens)

            confirm = client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": token, "new_password": "NewPassword123"},
            )
            assert confirm.status_code == 200
            assert db.auth_version == 1
            assert all(row["consumed"] for row in db.reset_tokens)
            assert client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": token, "new_password": "AnotherPassword123"},
            ).status_code == 400
            assert client.get(
                "/api/v1/books/genres", headers={"Authorization": f"Bearer {old_jwt}"}
            ).status_code == 401
            assert client.post(
                "/api/v1/auth/login",
                json={"email": db.email, "password": "OldPassword123"},
            ).status_code == 401
            new_login = client.post(
                "/api/v1/auth/login",
                json={"email": db.email, "password": "NewPassword123"},
            )
            assert new_login.status_code == 200
            new_jwt = new_login.json()["access_token"]
            changed = client.post(
                "/api/v1/auth/password/change",
                json={
                    "current_password": "NewPassword123",
                    "new_password": "PreviousPassword123",
                },
                headers={"Authorization": f"Bearer {new_jwt}"},
            )
            assert changed.status_code == 200
            assert db.auth_version == 2
            assert client.get(
                "/api/v1/books/genres", headers={"Authorization": f"Bearer {new_jwt}"}
            ).status_code == 401
            assert client.post(
                "/api/v1/auth/login",
                json={"email": db.email, "password": "PreviousPassword123"},
            ).status_code == 200


def test_request_limit_and_unknown_email_keep_the_same_public_response():
    db = SimulatedOracle()
    sent_links = []
    settings = SimpleNamespace(password_reset_enabled=True)

    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), patch(
        "app.core.password_recovery.get_db_connection", side_effect=lambda: connection(db)
    ), patch("app.api.v1.endpoints.auth.get_settings", return_value=settings), patch(
        "app.api.v1.endpoints.auth.mail_configured", return_value=True
    ), patch(
        "app.api.v1.endpoints.auth.send_password_reset_link",
        side_effect=lambda email, token: sent_links.append((email, token)),
    ):
        with TestClient(app) as client:
            known = [
                client.post("/api/v1/auth/password-reset/request", json={"email": db.email})
                for _ in range(4)
            ]
            unknown = client.post(
                "/api/v1/auth/password-reset/request",
                json={"email": "unknown@example.com"},
            )

    assert all(response.status_code == 200 for response in known)
    assert unknown.status_code == 200
    assert all(response.json() == unknown.json() for response in known)
    assert len(sent_links) == 3
    assert all(email == db.email for email, _ in sent_links)
