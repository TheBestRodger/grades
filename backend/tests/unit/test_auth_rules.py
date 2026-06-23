from __future__ import annotations

from datetime import datetime, timedelta

from app.features.auth.magic_links import MAGIC_LINK_TTL_MINUTES, hash_token, magic_link_expires_at
from app.features.auth.passwords import (
    PASSWORD_HASH_ALGORITHM,
    TEMP_PASSWORD_ALPHABET,
    generate_temporary_password,
    hash_password,
    normalize_login_from_email,
    username_from_name,
    verify_password,
)


def test_password_hash_roundtrip_and_malformed_values_are_rejected() -> None:
    stored_hash = hash_password("strong-password", salt="fixed-salt")

    assert stored_hash.startswith(f"{PASSWORD_HASH_ALGORITHM}$fixed-salt$")
    assert verify_password("strong-password", stored_hash)
    assert not verify_password("wrong-password", stored_hash)
    assert not verify_password("strong-password", None)
    assert not verify_password("strong-password", "not-a-valid-hash")
    assert not verify_password("strong-password", stored_hash.replace(PASSWORD_HASH_ALGORITHM, "sha1", 1))


def test_temporary_password_and_login_helpers_normalize_pilot_credentials() -> None:
    password = generate_temporary_password(32)

    assert len(password) == 32
    assert set(password) <= set(TEMP_PASSWORD_ALPHABET)
    assert normalize_login_from_email("  USER@Example.COM ") == "user@example.com"
    assert username_from_name("Иван Петров") == "ип"
    assert username_from_name("A", fallback_id=7) == "user0007"


def test_magic_link_token_helpers_are_stable_and_time_limited() -> None:
    issued_at = datetime(2026, 1, 1, 12, 0, 0)

    assert hash_token("token") == hash_token("token")
    assert hash_token("token") != hash_token("other-token")
    assert magic_link_expires_at(issued_at) == issued_at + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)
