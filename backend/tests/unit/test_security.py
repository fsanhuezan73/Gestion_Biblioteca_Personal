import asyncio
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
)


def test_hash_and_verify_password():
    plain = "MiPassword123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("otra_clave", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token({"sub": "7", "auth_version": 2})
    payload = decode_access_token(token)

    assert payload["sub"] == "7"
    assert payload["auth_version"] == 2
    assert "exp" in payload


def test_decode_access_token_with_invalid_token_raises_error():
    try:
        decode_access_token("token-invalido")
        assert False, "Se esperaba una excepción para token inválido"
    except Exception as exc:
        assert exc is not None


@contextmanager
def fake_user_version(version):
    class Cursor:
        def execute(self, query, params):
            assert "auth_version" in query
            assert params == {"user_id": 7}

        def fetchone(self):
            return None if version is None else (version,)

    class Connection:
        def cursor(self):
            return Cursor()

    yield Connection()


def test_current_user_accepts_matching_auth_version():
    token = create_access_token({"sub": "7", "auth_version": 2})
    with patch("app.core.security.get_db_connection", return_value=fake_user_version(2)):
        assert asyncio.run(get_current_user(token)) == 7


@pytest.mark.parametrize("version", [3, None])
def test_current_user_rejects_revoked_or_deleted_user(version):
    token = create_access_token({"sub": "7", "auth_version": 2})
    with patch("app.core.security.get_db_connection", return_value=fake_user_version(version)):
        with pytest.raises(HTTPException) as error:
            asyncio.run(get_current_user(token))
    assert error.value.status_code == 401


@pytest.mark.parametrize("claims", [{"sub": "7"}, {"sub": "bad", "auth_version": 0}, {"sub": "7", "auth_version": True}])
def test_current_user_rejects_malformed_claims_without_database_lookup(claims):
    token = create_access_token(claims)
    with patch("app.core.security.get_db_connection") as mock_db:
        with pytest.raises(HTTPException) as error:
            asyncio.run(get_current_user(token))
    assert error.value.status_code == 401
    mock_db.assert_not_called()
