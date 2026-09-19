from contextlib import contextmanager
import hashlib
import secrets
from unittest.mock import patch

import pytest

from app.core.password_recovery import (
    InvalidResetToken,
    InvalidCurrentPassword,
    UnchangedPassword,
    change_password,
    confirm_password_reset,
    issue_password_reset,
    RESET_TOKEN_LIFETIME,
)
from app.core.security import hash_password


class FakeCursor:
    def __init__(self, email_count=0, origin_count=0, user_id=7):
        self.results = [(email_count,), (origin_count,), None if user_id is None else (user_id,)]
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.results.pop(0)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor

    def cursor(self):
        return self.cursor_obj


@contextmanager
def fake_connection(cursor):
    yield FakeConnection(cursor)


def test_request_stores_only_hash_and_expires_in_15_minutes():
    cursor = FakeCursor()
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        token = issue_password_reset(" USER@Example.COM ", "127.0.0.1")

    assert token is not None
    assert len(token) >= 40
    statements = cursor.statements
    assert "LOCK TABLE password_reset_requests" in statements[0][0]
    assert statements[4][1] == {"email": "user@example.com"}
    params = statements[-1][1]
    assert params["token_hash"] == hashlib.sha256(token.encode("ascii")).hexdigest()
    assert params["expires_at"] - params["created_at"] == RESET_TOKEN_LIFETIME
    assert all(token not in str(sql) and token not in str(bind) for sql, bind in statements)
    assert "user@example.com" not in str(statements[3][1])


def test_unknown_email_has_same_rate_limit_record_but_no_token():
    cursor = FakeCursor(user_id=None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        token = issue_password_reset("nobody@example.com", "127.0.0.1")
    assert token is None
    assert any("INSERT INTO password_reset_requests" in sql for sql, _ in cursor.statements)
    assert not any("INSERT INTO password_reset_tokens" in sql for sql, _ in cursor.statements)


def test_email_limit_prevents_new_request():
    cursor = FakeCursor(email_count=3)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        assert issue_password_reset("user@example.com", "127.0.0.1") is None
    assert not any("INSERT INTO" in sql for sql, _ in cursor.statements)


def test_origin_limit_prevents_new_request():
    cursor = FakeCursor(origin_count=10)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        assert issue_password_reset("user@example.com", "127.0.0.1") is None
    assert not any("INSERT INTO" in sql for sql, _ in cursor.statements)


class ConfirmCursor:
    def __init__(self, token_row, user_row):
        self.results = [token_row, user_row]
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.results.pop(0)


def test_confirm_updates_password_revokes_sessions_and_consumes_tokens():
    token = secrets.token_urlsafe(32)
    cursor = ConfirmCursor((11, 7), (hash_password("old-password"),))
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        confirm_password_reset(token, "new-password")

    statements = cursor.statements
    assert statements[0][1] == {"token_hash": hashlib.sha256(token.encode("ascii")).hexdigest()}
    assert "FOR UPDATE" in statements[0][0]
    assert "FOR UPDATE" in statements[1][0]
    assert "auth_version = auth_version + 1" in statements[2][0]
    assert statements[2][1]["hashed_password"] != "new-password"
    assert statements[3][1] == {"user_id": 7}
    assert all(token not in str(bind) for _, bind in statements)


def test_confirm_rejects_expired_used_or_unknown_token_without_updates():
    token = secrets.token_urlsafe(32)
    cursor = ConfirmCursor(None, None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        with pytest.raises(InvalidResetToken):
            confirm_password_reset(token, "new-password")
    assert len(cursor.statements) == 1


def test_confirm_rejects_current_password_without_updates():
    token = secrets.token_urlsafe(32)
    cursor = ConfirmCursor((11, 7), (hash_password("same-password"),))
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        with pytest.raises(UnchangedPassword):
            confirm_password_reset(token, "same-password")
    assert len(cursor.statements) == 2


def test_confirm_allows_a_password_used_before_the_current_one():
    token = secrets.token_urlsafe(32)
    cursor = ConfirmCursor((11, 7), (hash_password("current-password"),))
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        confirm_password_reset(token, "previous-password")
    assert "auth_version = auth_version + 1" in cursor.statements[2][0]


@pytest.mark.parametrize("token", ["short", "a" * 42 + "é", "a" * 44])
def test_confirm_rejects_malformed_token_before_database_access(token):
    with patch("app.core.password_recovery.get_db_connection") as db:
        with pytest.raises(InvalidResetToken):
            confirm_password_reset(token, "new-password")
    db.assert_not_called()


def test_authenticated_change_revokes_jwt_and_pending_reset_links():
    cursor = ConfirmCursor((hash_password("current-password"),), None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        change_password(7, "current-password", "new-password")

    assert cursor.statements[0][1] == {"user_id": 7}
    assert "FOR UPDATE" in cursor.statements[0][0]
    assert "auth_version = auth_version + 1" in cursor.statements[1][0]
    assert cursor.statements[1][1]["hashed_password"] != "new-password"
    assert "DISABLE_PARALLEL_DML */ password_reset_tokens" in cursor.statements[2][0]
    assert "GREATEST(SYSTIMESTAMP, created_at)" in cursor.statements[2][0]
    assert cursor.statements[2][1] == {"user_id": 7}


@pytest.mark.parametrize("user_row", [None, (hash_password("current-password"),)])
def test_authenticated_change_rejects_wrong_current_password(user_row):
    cursor = ConfirmCursor(user_row, None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        with pytest.raises(InvalidCurrentPassword):
            change_password(7, "wrong-password", "new-password")
    assert len(cursor.statements) == 1


def test_authenticated_change_rejects_same_password_without_updates():
    cursor = ConfirmCursor((hash_password("current-password"),), None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        with pytest.raises(UnchangedPassword):
            change_password(7, "current-password", "current-password")
    assert len(cursor.statements) == 1


def test_authenticated_change_allows_previous_password():
    cursor = ConfirmCursor((hash_password("current-password"),), None)
    with patch("app.core.password_recovery.get_db_connection", return_value=fake_connection(cursor)):
        change_password(7, "current-password", "previous-password")
    assert "auth_version = auth_version + 1" in cursor.statements[1][0]
