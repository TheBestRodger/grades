from __future__ import annotations

import os


pytest_plugins = [
    "backend.tests.fixtures.app",
    "backend.tests.fixtures.postgres",
]


# Importing app.main creates the module-level ASGI app for uvicorn.
# The default app is unused by tests, but collection still requires valid env.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://grades_mgtu_test:grades_mgtu_test@localhost:5432/grades_mgtu_test",
)
