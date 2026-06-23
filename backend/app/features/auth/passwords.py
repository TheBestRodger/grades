from __future__ import annotations

import hashlib
import secrets
import string

from ...models import Employee

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 120_000
TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits


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


def generate_temporary_password(length: int = 10) -> str:
    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(length))


def username_from_name(full_name: str, fallback_id: int | None = None) -> str:
    initials = "".join(part[0].lower() for part in full_name.split() if part)
    if len(initials) >= 2:
        return initials
    return f"user{fallback_id or secrets.randbelow(10_000):04d}"


def normalize_login_from_email(email: str) -> str:
    return email.strip().lower()


def issue_temporary_password(employee: Employee) -> dict[str, str]:
    password = generate_temporary_password()
    employee.username = normalize_login_from_email(employee.email)
    employee.password_hash = hash_password(password)
    return {"username": employee.username, "password": password}
