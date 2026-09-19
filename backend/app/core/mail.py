"""Entrega de enlaces de recuperación mediante SMTP cifrado."""

from email.message import EmailMessage
import smtplib
import ssl
from urllib.parse import quote, urlsplit

from app.core.config import Settings, get_settings


def mail_configured(settings: Settings) -> bool:
    """Verifica configuración antes de habilitar recuperación por correo."""
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email)):
        return False
    if not 1 <= settings.smtp_port <= 65535:
        return False
    if any("\n" in value or "\r" in value for value in (settings.smtp_from_email, settings.smtp_host)):
        return False
    if "@" not in settings.smtp_from_email:
        return False

    url = urlsplit(settings.frontend_base_url)
    if not url.hostname or url.username or url.password or url.query or url.fragment:
        return False
    if url.scheme == "https":
        return True
    return (
        settings.app_env == "development"
        and url.scheme == "http"
        and url.hostname in ("localhost", "127.0.0.1")
    )


def send_password_reset_link(email: str, token: str) -> None:
    settings = get_settings()
    if not mail_configured(settings):
        raise RuntimeError("El servicio de correo de recuperación no está configurado")

    reset_url = (
        settings.frontend_base_url.rstrip("/")
        + "/reset-password?token="
        + quote(token, safe="")
    )
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message["Subject"] = "Recupera tu contraseña — Biblioteca Personal"
    message.set_content(
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Abre este enlace (válido durante 15 minutos):\n{reset_url}\n\n"
        "Si no hiciste esta solicitud, ignora este correo. Tu contraseña no ha cambiado.\n"
    )

    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=10, context=context
        ) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
