"""Generación y límites de solicitudes de recuperación de contraseña."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import string

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.session import get_db_connection

RESET_TOKEN_LIFETIME = timedelta(minutes=15)
REQUEST_WINDOW = timedelta(hours=1)
MAX_REQUESTS_PER_EMAIL = 3
MAX_REQUESTS_PER_ORIGIN = 10


class InvalidResetToken(Exception):
    pass


class UnchangedPassword(Exception):
    pass


class InvalidCurrentPassword(Exception):
    pass


def _fingerprint(kind: str, value: str) -> str:
    key = get_settings().jwt_secret_key.encode("utf-8")
    return hmac.new(key, f"password-reset:{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def issue_password_reset(email: str, origin: str) -> str | None:
    """Registra una solicitud y devuelve un secreto solo para una cuenta existente.

    El llamador nunca debe devolver el secreto por HTTP ni escribirlo en logs.
    La tabla se bloquea durante el conteo e inserción para evitar carreras entre
    solicitudes concurrentes en distintas instancias de la aplicación.
    """
    normalized_email = email.strip().lower()
    email_fingerprint = _fingerprint("email", normalized_email)
    origin_fingerprint = _fingerprint("origin", origin)
    now = datetime.now(timezone.utc)
    cutoff = now - REQUEST_WINDOW

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("LOCK TABLE password_reset_requests IN EXCLUSIVE MODE WAIT 5")
        cursor.execute(
            """SELECT COUNT(*) FROM password_reset_requests
               WHERE email_fingerprint = :fingerprint AND created_at >= :cutoff""",
            {"fingerprint": email_fingerprint, "cutoff": cutoff},
        )
        email_count = cursor.fetchone()[0]
        cursor.execute(
            """SELECT COUNT(*) FROM password_reset_requests
               WHERE origin_fingerprint = :fingerprint AND created_at >= :cutoff""",
            {"fingerprint": origin_fingerprint, "cutoff": cutoff},
        )
        origin_count = cursor.fetchone()[0]
        if email_count >= MAX_REQUESTS_PER_EMAIL or origin_count >= MAX_REQUESTS_PER_ORIGIN:
            return None

        cursor.execute(
            """INSERT INTO password_reset_requests
               (email_fingerprint, origin_fingerprint, created_at)
               VALUES (:email_fingerprint, :origin_fingerprint, :created_at)""",
            {
                "email_fingerprint": email_fingerprint,
                "origin_fingerprint": origin_fingerprint,
                "created_at": now,
            },
        )
        cursor.execute("SELECT id FROM users WHERE email = :email", {"email": normalized_email})
        row = cursor.fetchone()
        if row is None:
            return None

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        # Conservar enlaces anteriores hasta que alguno se use: un fallo SMTP
        # no debe invalidar un enlace que el usuario ya recibió.
        cursor.execute(
            """INSERT INTO password_reset_tokens
               (user_id, token_hash, created_at, expires_at)
               VALUES (:user_id, :token_hash, :created_at, :expires_at)""",
            {
                "user_id": row[0],
                "token_hash": token_hash,
                "created_at": now,
                "expires_at": now + RESET_TOKEN_LIFETIME,
            },
        )
        return token


def confirm_password_reset(token: str, new_password: str) -> None:
    """Consume el enlace, cambia la clave y revoca JWT en una transacción."""
    # El formato es fijo para no admitir entradas arbitrariamente grandes.
    allowed_chars = string.ascii_letters + string.digits + "-_"
    if len(token) != 43 or not all(c in allowed_chars for c in token):
        raise InvalidResetToken
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, user_id FROM password_reset_tokens
               WHERE token_hash = :token_hash
                 AND consumed_at IS NULL AND expires_at > SYSTIMESTAMP
               FOR UPDATE""",
            {"token_hash": token_hash},
        )
        token_row = cursor.fetchone()
        if token_row is None:
            raise InvalidResetToken

        cursor.execute(
            "SELECT hashed_password FROM users WHERE id = :user_id FOR UPDATE",
            {"user_id": token_row[1]},
        )
        user_row = cursor.fetchone()
        if user_row is None:
            raise InvalidResetToken
        if verify_password(new_password, user_row[0]):
            raise UnchangedPassword

        cursor.execute(
            """UPDATE users SET hashed_password = :hashed_password,
               auth_version = auth_version + 1 WHERE id = :user_id""",
            {"hashed_password": hash_password(new_password), "user_id": token_row[1]},
        )
        cursor.execute(
            """UPDATE /*+ DISABLE_PARALLEL_DML */ password_reset_tokens
               SET consumed_at = GREATEST(SYSTIMESTAMP, created_at)
               WHERE user_id = :user_id AND consumed_at IS NULL""",
            {"user_id": token_row[1]},
        )


def change_password(user_id: int, current_password: str, new_password: str) -> None:
    """Revalida la contraseña y revoca sesiones/enlaces en una transacción."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT hashed_password FROM users WHERE id = :user_id FOR UPDATE",
            {"user_id": user_id},
        )
        row = cursor.fetchone()
        if row is None or not verify_password(current_password, row[0]):
            raise InvalidCurrentPassword
        if verify_password(new_password, row[0]):
            raise UnchangedPassword

        cursor.execute(
            """UPDATE users SET hashed_password = :hashed_password,
               auth_version = auth_version + 1 WHERE id = :user_id""",
            {"hashed_password": hash_password(new_password), "user_id": user_id},
        )
        cursor.execute(
            """UPDATE /*+ DISABLE_PARALLEL_DML */ password_reset_tokens
               SET consumed_at = GREATEST(SYSTIMESTAMP, created_at)
               WHERE user_id = :user_id AND consumed_at IS NULL""",
            {"user_id": user_id},
        )
