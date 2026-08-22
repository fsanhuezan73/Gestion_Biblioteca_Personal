from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_hash_and_verify_password():
    plain = "MiPassword123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("otra_clave", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token({"sub": "7"})
    payload = decode_access_token(token)

    assert payload["sub"] == "7"
    assert "exp" in payload


def test_decode_access_token_with_invalid_token_raises_error():
    try:
        decode_access_token("token-invalido")
        assert False, "Se esperaba una excepción para token inválido"
    except Exception as exc:
        assert exc is not None
