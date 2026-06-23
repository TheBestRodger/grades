from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import PROJECT_ROOT, Settings
from .core.db import Database
from .core.health_router import router as health_router
from .core.observability import RequestObservabilityMiddleware, configure_request_logging
from .features.analytics.audit_router import router as audit_router
from .features.analytics.router import router as analytics_router
from .features.auth.router import router as auth_router
from .features.campaigns.router import router as campaigns_router
from .features.documents.router import router as documents_router
from .features.exports.router import router as exports_router
from .features.hr_reviews.router import router as hr_reviews_router
from .features.manager_reviews.router import router as manager_reviews_router
from .features.notifications.router import router as notifications_router
from .features.organization.router import router as organization_router
from .features.profiles.router import router as profiles_router
from .features.settings.demo_router import router as demo_router
from .features.settings.router import router as settings_router
from .features.structure.router import router as structure_router
from .infrastructure.ai.gateway import build_ai_gateway

ROUTERS = (
    health_router,
    demo_router,
    auth_router,
    settings_router,
    profiles_router,
    organization_router,
    structure_router,
    campaigns_router,
    audit_router,
    analytics_router,
    documents_router,
    exports_router,
    hr_reviews_router,
    manager_reviews_router,
    notifications_router,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.database_url.startswith("sqlite") and settings.app_env != "test":
        raise RuntimeError("SQLite runtime is no longer supported. Use PostgreSQL DATABASE_URL.")
    configure_request_logging()
    database = Database(settings.database_url)
    ai_gateway = build_ai_gateway(settings.ai_mode, settings.ai_provider)
    document_storage_dir = (
        settings.document_storage_dir or PROJECT_ROOT / "backend" / "data" / "documents"
    ).resolve()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            database.engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.state.ai_gateway = ai_gateway
    app.state.document_storage_dir = document_storage_dir
    app.add_middleware(RequestObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    if settings.serve_frontend_static and settings.frontend_dist.exists():
        app.mount(
            "/",
            StaticFiles(directory=settings.frontend_dist, html=True),
            name="frontend",
        )

    return app


app = create_app()
