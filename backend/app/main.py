from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .ai_gateway import build_ai_gateway
from .api.routers import (
    analytics,
    audit,
    auth,
    campaigns,
    demo,
    documents,
    exports,
    health,
    hr_reviews,
    manager_reviews,
    organization,
    profiles,
    settings as settings_router,
    structure,
)
from .config import PROJECT_ROOT, Settings
from .db import Database
from .auth_operations import ensure_bootstrap_hr_credentials
from .import_grades_documents import (
    DOCUMENTS_DIR,
    _default_staffing_file,
    import_grades_documents,
)
from .seed import seed_demo_data

ROUTERS = (
    health.router,
    demo.router,
    auth.router,
    settings_router.router,
    profiles.router,
    organization.router,
    structure.router,
    campaigns.router,
    audit.router,
    analytics.router,
    documents.router,
    exports.router,
    hr_reviews.router,
    manager_reviews.router,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.database_url)
    ai_gateway = build_ai_gateway(settings.ai_mode, settings.ai_provider)
    document_storage_dir = (
        settings.document_storage_dir or PROJECT_ROOT / "backend" / "data" / "documents"
    ).resolve()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.migrate()
        with database.session() as session:
            seed_demo_data(session, settings.work_staffing_file)
            ensure_bootstrap_hr_credentials(session, settings)
            if settings.auto_import_grades_documents:
                staffing_file = _default_staffing_file()
                if staffing_file.exists() and DOCUMENTS_DIR.exists():
                    import_grades_documents(
                        session,
                        staffing_file=staffing_file,
                        documents_dir=DOCUMENTS_DIR,
                        storage_dir=document_storage_dir,
                        apply_changes=True,
                    )
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.state.ai_gateway = ai_gateway
    app.state.document_storage_dir = document_storage_dir
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    if settings.frontend_dist.exists():
        app.mount(
            "/",
            StaticFiles(directory=settings.frontend_dist, html=True),
            name="frontend",
        )

    return app


app = create_app()
