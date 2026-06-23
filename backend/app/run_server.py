from __future__ import annotations

import os

import uvicorn


def _positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be greater than zero.")
    return value


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=_positive_int("UVICORN_WORKERS", 1),
        timeout_graceful_shutdown=_positive_int(
            "UVICORN_GRACEFUL_SHUTDOWN_SECONDS",
            30,
        ),
    )


if __name__ == "__main__":
    main()
