from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.mail import mail_configured, send_password_reset_link


def settings(**overrides):
    values = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_security": "starttls",
        "smtp_username": "mailer",
        "smtp_password": "secret",
        "smtp_from_email": "biblioteca@example.com",
        "frontend_base_url": "https://books.example.com",
        "app_env": "production",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_mail_requires_complete_secure_configuration():
    assert mail_configured(settings()) is True
    assert mail_configured(settings(smtp_password="")) is False
    assert mail_configured(settings(frontend_base_url="http://books.example.com")) is False
    assert mail_configured(settings(frontend_base_url="https://books.example.com?next=evil")) is False
    assert mail_configured(settings(smtp_from_email="biblioteca@example.com\nBcc: evil@example.com")) is False
    assert mail_configured(settings(frontend_base_url="http://localhost:5173", app_env="development")) is True


def test_send_reset_link_uses_starttls_and_configured_frontend_url():
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("app.core.mail.get_settings", return_value=settings()), patch(
        "app.core.mail.smtplib.SMTP", return_value=smtp
    ) as smtp_class:
        send_password_reset_link("user@example.com", "secret-token")

    smtp_class.assert_called_once()
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("mailer", "secret")
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "user@example.com"
    assert "https://books.example.com/reset-password?token=secret-token" in message.get_content()
    assert "15 minutos" in message.get_content()


def test_send_reset_link_supports_implicit_tls():
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("app.core.mail.get_settings", return_value=settings(smtp_security="ssl", smtp_port=465)), patch(
        "app.core.mail.smtplib.SMTP_SSL", return_value=smtp
    ) as smtp_class:
        send_password_reset_link("user@example.com", "secret-token")

    smtp_class.assert_called_once()
    smtp.starttls.assert_not_called()
    smtp.send_message.assert_called_once()
