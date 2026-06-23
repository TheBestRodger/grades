from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_now = now
