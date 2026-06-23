from __future__ import annotations

from .core.config import PROJECT_ROOT, Settings
from .core.db import Database
from .features.auth.service import ensure_bootstrap_hr_credentials
from .features.imports.demo_seed import seed_demo_data
from .features.imports.grades_documents import (
    DOCUMENTS_DIR,
    _default_staffing_file,
    import_grades_documents,
)


def prepare_runtime_database(settings: Settings) -> None:
    database = Database(settings.database_url)
    database.migrate()
    document_storage_dir = (
        settings.document_storage_dir or PROJECT_ROOT / "backend" / "data" / "documents"
    ).resolve()

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
