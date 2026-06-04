from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    ai_mode: str
    ai_provider: str
    ai_base_url: str | None
    ai_model_name: str | None
    ai_api_token: str | None
    ai_request_timeout_seconds: float
    database_url: str
    frontend_dist: Path
    work_staffing_file: Path | None = None
    document_storage_dir: Path | None = None
    public_base_url: str = "http://192.168.18.163:8010"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    bootstrap_hr_username: str | None = None
    bootstrap_hr_password: str | None = None
    auto_import_grades_documents: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(
            os.environ.get("PROFILER_DATA_DIR", str(PROJECT_ROOT / "backend" / "data"))
        ).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        default_database = f"sqlite:///{(data_dir / 'demo.sqlite').as_posix()}"
        return cls(
            app_name="Профилирование должностей",
            app_env=os.environ.get("APP_ENV", "demo-local"),
            ai_mode=os.environ.get("AI_MODE", "off"),
            ai_provider=os.environ.get("AI_PROVIDER", "off"),
            ai_base_url=os.environ.get("OPENAI_BASE_URL") or os.environ.get("AI_BASE_URL"),
            ai_model_name=os.environ.get("OPENAI_MODEL") or os.environ.get("AI_MODEL_NAME"),
            ai_api_token=os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_TOKEN"),
            ai_request_timeout_seconds=float(os.environ.get("AI_REQUEST_TIMEOUT_SECONDS", "60")),
            database_url=os.environ.get("DATABASE_URL", default_database),
            frontend_dist=PROJECT_ROOT / "frontend" / "dist",
            work_staffing_file=Path(
                os.environ.get(
                    "WORK_STAFFING_FILE",
                    str(
                        PROJECT_ROOT
                        / "Изначальные документы_история"
                        / "ШР по уровням на 15.05.26_размечено.xlsx"
                    ),
                )
            ).resolve(),
            document_storage_dir=data_dir / "documents",
            public_base_url=os.environ.get("PUBLIC_BASE_URL", "http://192.168.18.163:8010").rstrip("/"),
            smtp_host=os.environ.get("SMTP_HOST") or None,
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            smtp_username=os.environ.get("SMTP_USERNAME") or None,
            smtp_password=os.environ.get("SMTP_PASSWORD") or None,
            smtp_from_email=os.environ.get("SMTP_FROM_EMAIL") or os.environ.get("SMTP_USERNAME") or None,
            smtp_use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"},
            smtp_use_ssl=os.environ.get("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"},
            bootstrap_hr_username=os.environ.get("BOOTSTRAP_HR_USERNAME") or None,
            bootstrap_hr_password=os.environ.get("BOOTSTRAP_HR_PASSWORD") or None,
            auto_import_grades_documents=os.environ.get(
                "AUTO_IMPORT_GRADES_DOCUMENTS",
                "true",
            ).lower() in {"1", "true", "yes", "on"},
        )
