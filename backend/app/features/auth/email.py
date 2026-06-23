from __future__ import annotations

from email.message import EmailMessage
import smtplib

from ...core.config import Settings
from .errors import AuthOperationError
from .magic_links import MAGIC_LINK_TTL_MINUTES


def send_magic_link_email(settings: Settings, recipient: str, login_url: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise AuthOperationError("SMTP не настроен: задайте SMTP_HOST и SMTP_FROM_EMAIL.", 500)

    message = build_magic_link_email(settings, recipient, login_url)
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                _smtp_login_if_configured(smtp, settings)
                smtp.send_message(message)
            return
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            _smtp_login_if_configured(smtp, settings)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise AuthOperationError("Не удалось отправить письмо со ссылкой входа.", 502) from exc


def build_magic_link_email(settings: Settings, recipient: str, login_url: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Вход в систему профилирования должностей"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "Здравствуйте.",
                "",
                "Для входа в систему профилирования должностей перейдите по одноразовой ссылке:",
                login_url,
                "",
                f"Ссылка действует {MAGIC_LINK_TTL_MINUTES} минут и может быть использована только один раз.",
                "",
                "Если вы не запрашивали вход, проигнорируйте это письмо.",
            ]
        )
    )
    return message


def _smtp_login_if_configured(smtp: smtplib.SMTP, settings: Settings) -> None:
    if settings.smtp_username and settings.smtp_password:
        smtp.login(settings.smtp_username, settings.smtp_password)
