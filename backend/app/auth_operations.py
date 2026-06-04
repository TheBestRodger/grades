from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
import hashlib
import json
import secrets
import smtplib
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .models import AuditEvent, AuthLoginToken, AuthSession, Employee


MAGIC_LINK_TTL_MINUTES = 15
SESSION_TTL_HOURS = 8
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 120_000
TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits


class AuthOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_ALGORITHM}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, salt, expected = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False
    actual = hash_password(password, salt).rsplit("$", 1)[-1]
    return secrets.compare_digest(actual, expected)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def generate_temporary_password(length: int = 10) -> str:
    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(length))


def username_from_name(full_name: str, fallback_id: int | None = None) -> str:
    initials = "".join(part[0].lower() for part in full_name.split() if part)
    if len(initials) >= 2:
        return initials
    return f"user{fallback_id or secrets.randbelow(10_000):04d}"


def _audit(
    session: Session,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


def employee_payload(employee: Employee) -> dict[str, object]:
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "username": employee.username,
        "role": employee.system_role,
        "is_demo": employee.is_demo,
    }


def ensure_bootstrap_hr_credentials(session: Session, settings: Settings) -> None:
    if not settings.bootstrap_hr_username or not settings.bootstrap_hr_password:
        return
    hr = session.scalar(
        select(Employee)
        .where(Employee.system_role == "hr", Employee.is_active.is_(True))
        .order_by(Employee.id)
    )
    if hr is None:
        return
    hr.username = settings.bootstrap_hr_username.strip()
    hr.password_hash = hash_password(settings.bootstrap_hr_password)


def login_with_password(session: Session, username: str, password: str) -> dict[str, object]:
    normalized = username.strip().lower()
    employee = session.scalar(
        select(Employee).where(
            func.lower(Employee.username) == normalized,
            Employee.is_active.is_(True),
        )
    )
    if employee is None or not verify_password(password, employee.password_hash):
        raise AuthOperationError("Неверный логин или пароль.", 401)

    now = _now()
    if employee.first_login_at is None:
        employee.first_login_at = now
    employee.last_login_at = now
    session_token = _new_token()
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    auth_session = AuthSession(
        employee_id=employee.id,
        token_hash=_hash_token(session_token),
        expires_at=expires_at,
        last_seen_at=now,
    )
    session.add(auth_session)
    _audit(
        session,
        employee.id,
        "auth.password_login",
        "employee",
        employee.id,
        {"session_ttl_hours": SESSION_TTL_HOURS, "is_demo": employee.is_demo},
    )
    return {
        "token": session_token,
        "expires_at": expires_at.isoformat(),
        "user": employee_payload(employee),
    }


def request_magic_link(session: Session, email: str, settings: Settings) -> dict[str, object]:
    normalized = email.strip().lower()
    employee = session.scalar(
        select(Employee).where(
            func.lower(Employee.email) == normalized,
            Employee.is_active.is_(True),
        )
    )
    expires_at = _now() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)
    response: dict[str, object] = {
        "email": normalized,
        "delivery_mode": "local_link" if settings.app_env in {"demo-local", "test"} else "email",
        "expires_at": expires_at.isoformat(),
        "login_token": None,
        "login_url": None,
        "message": "Будет выпущена одноразовая ссылка входа.",
    }
    if employee is None:
        _audit(
            session,
            None,
            "auth.magic_link_requested_unknown",
            "auth",
            "unknown",
            {"delivery_mode": response["delivery_mode"]},
        )
        raise AuthOperationError("Пользователь с таким email не найден.", 404)

    token = _new_token()
    session.add(
        AuthLoginToken(
            employee_id=employee.id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
        )
    )
    _audit(
        session,
        employee.id,
        "auth.magic_link_requested",
        "employee",
        employee.id,
        {"is_demo": employee.is_demo, "delivery_mode": response["delivery_mode"]},
    )
    login_url = f"{settings.public_base_url}/?auth_token={token}"
    if settings.app_env in {"demo-local", "test"}:
        response["login_token"] = token
        response["login_url"] = f"/?auth_token={token}"
        response["message"] = "Локальная одноразовая ссылка создана. В пилоте вместо показа ссылки будет отправка письма."
    else:
        _send_magic_link_email(settings, employee.email, login_url)
        response["message"] = "Одноразовая ссылка отправлена на email."
    return response


def _send_magic_link_email(settings: Settings, recipient: str, login_url: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise AuthOperationError("SMTP не настроен: задайте SMTP_HOST и SMTP_FROM_EMAIL.", 500)

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


def _smtp_login_if_configured(smtp: smtplib.SMTP, settings: Settings) -> None:
    if settings.smtp_username and settings.smtp_password:
        smtp.login(settings.smtp_username, settings.smtp_password)


def consume_magic_link(session: Session, token: str) -> dict[str, object]:
    now = _now()
    login_token = session.scalar(
        select(AuthLoginToken)
        .where(AuthLoginToken.token_hash == _hash_token(token))
        .options(selectinload(AuthLoginToken.employee))
    )
    if login_token is None:
        raise AuthOperationError("Ссылка входа не найдена.", 401)
    if login_token.consumed_at is not None:
        raise AuthOperationError("Ссылка входа уже использована.", 409)
    if login_token.expires_at < now:
        raise AuthOperationError("Срок действия ссылки входа истек.", 401)
    if not login_token.employee.is_active:
        raise AuthOperationError("Пользователь отключен.", 403)

    if login_token.employee.first_login_at is None:
        login_token.employee.first_login_at = now
    login_token.employee.last_login_at = now
    session_token = _new_token()
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    auth_session = AuthSession(
        employee_id=login_token.employee_id,
        token_hash=_hash_token(session_token),
        expires_at=expires_at,
        last_seen_at=now,
    )
    login_token.consumed_at = now
    session.add(auth_session)
    _audit(
        session,
        login_token.employee_id,
        "auth.magic_link_consumed",
        "employee",
        login_token.employee_id,
        {"session_ttl_hours": SESSION_TTL_HOURS, "is_demo": login_token.employee.is_demo},
    )
    return {
        "token": session_token,
        "expires_at": expires_at.isoformat(),
        "user": employee_payload(login_token.employee),
    }


def actor_from_authorization(session: Session, authorization: str | None) -> Employee | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthOperationError("Некорректный заголовок авторизации.", 401)
    now = _now()
    auth_session = session.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == _hash_token(token))
        .options(selectinload(AuthSession.employee))
    )
    if auth_session is None or auth_session.revoked_at is not None:
        raise AuthOperationError("Сессия не найдена или завершена.", 401)
    if auth_session.expires_at < now:
        raise AuthOperationError("Срок действия сессии истек.", 401)
    if not auth_session.employee.is_active:
        raise AuthOperationError("Пользователь отключен.", 403)
    auth_session.last_seen_at = now
    return auth_session.employee


def logout_session(session: Session, authorization: str | None) -> dict[str, object]:
    if not authorization:
        return {"revoked": False}
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return {"revoked": False}
    auth_session = session.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == _hash_token(token))
        .options(selectinload(AuthSession.employee))
    )
    if auth_session is None or auth_session.revoked_at is not None:
        return {"revoked": False}
    auth_session.revoked_at = _now()
    _audit(
        session,
        auth_session.employee_id,
        "auth.session_revoked",
        "employee",
        auth_session.employee_id,
        {"is_demo": auth_session.employee.is_demo},
    )
    return {"revoked": True}
