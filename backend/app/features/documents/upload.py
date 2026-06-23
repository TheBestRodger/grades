from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...infrastructure.files.document_storage import (
    DocumentFileError,
    extract_initial_text,
    storage_token,
    store_text_snapshot,
)
from ...models import AuditEvent, Document, Employee
from .constants import DOCUMENT_TYPE_LABELS, MAX_UPLOAD_BYTES, UPLOAD_EXTENSIONS
from .errors import DocumentOperationError
from .registry import get_document_registry
from ..notifications.service import notify_hr_users


def upload_work_document(
    session: Session,
    actor: Employee,
    storage_dir: Path,
    *,
    filename: str,
    document_code: str,
    document_type: str,
    title: str,
    version: str,
    content: bytes,
) -> dict[str, object]:
    document_code, title, version, suffix = _validate_upload(
        session,
        filename=filename,
        document_code=document_code,
        document_type=document_type,
        title=title,
        version=version,
        content=content,
    )
    checksum = sha256(content).hexdigest()
    duplicate = session.scalar(
        select(Document).where(
            Document.is_demo.is_(False), Document.checksum == checksum
        )
    )
    if duplicate is not None:
        raise DocumentOperationError(
            "Этот оригинал уже загружен в рабочий реестр.", 409
        )

    try:
        extracted_text, extraction_method = extract_initial_text(content, suffix)
    except DocumentFileError as exc:
        raise DocumentOperationError(exc.message) from exc

    original_path = _store_original(
        storage_dir, document_code, checksum, suffix, content
    )
    text_snapshot_path: Path | None = None
    try:
        document = _create_document(
            document_code=document_code,
            document_type=document_type,
            title=title,
            version=version,
            checksum=checksum,
            original_path=original_path,
            extracted_text=extracted_text,
        )
        session.add(document)
        session.flush()
        if extracted_text:
            text_snapshot_path = store_text_snapshot(
                storage_dir, document.document_code, checksum, extracted_text
            )
            document.extracted_text_path = str(text_snapshot_path)
        _audit_upload(
            session,
            actor,
            document,
            filename,
            checksum,
            len(content),
            extraction_method,
        )
        notify_hr_users(
            session,
            is_demo=False,
            notification_type="document_uploaded",
            title="Загружен новый документ",
            message=f"В реестр добавлен документ «{document.title}» ({document.document_code}).",
            target_section="documents",
            entity_type="document",
            entity_id=document.id,
            dedupe_key=f"document-uploaded:{document.id}",
            exclude_employee_id=actor.id,
        )
        session.flush()
    except Exception as exc:
        _cleanup_upload_files(original_path, text_snapshot_path)
        if isinstance(exc, DocumentOperationError):
            raise
        raise DocumentOperationError(
            "Не удалось сохранить файл документа. Повторите загрузку."
        ) from exc
    return get_document_registry(session, is_demo=False)


def _validate_upload(
    session: Session,
    *,
    filename: str,
    document_code: str,
    document_type: str,
    title: str,
    version: str,
    content: bytes,
) -> tuple[str, str, str, str]:
    document_code = document_code.strip()
    title = " ".join(title.split())
    version = version.strip()
    suffix = Path(filename).suffix.lower()
    if document_type not in DOCUMENT_TYPE_LABELS:
        raise DocumentOperationError("Неизвестный тип документа.")
    if not document_code or len(document_code) > 80:
        raise DocumentOperationError("Укажите код документа длиной до 80 символов.")
    if not title or len(title) > 255:
        raise DocumentOperationError(
            "Укажите название документа длиной до 255 символов."
        )
    if not version or len(version) > 80:
        raise DocumentOperationError("Укажите версию документа длиной до 80 символов.")
    if suffix not in UPLOAD_EXTENSIONS:
        raise DocumentOperationError("Поддерживаются файлы TXT, MD, DOCX и PDF.")
    if not content:
        raise DocumentOperationError("Файл пуст.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentOperationError("Размер файла превышает 25 МБ.")
    if (
        session.scalar(select(Document).where(Document.document_code == document_code))
        is not None
    ):
        raise DocumentOperationError("Документ с таким кодом уже существует.", 409)
    return document_code, title, version, suffix


def _store_original(
    storage_dir: Path,
    document_code: str,
    checksum: str,
    suffix: str,
    content: bytes,
) -> Path:
    original_dir = storage_dir.resolve() / "originals"
    original_dir.mkdir(parents=True, exist_ok=True)
    original_path = (
        original_dir / f"{storage_token(document_code)}__{checksum[:12]}{suffix}"
    )
    try:
        with original_path.open("xb") as source_file:
            source_file.write(content)
    except FileExistsError as exc:
        raise DocumentOperationError(
            "Оригинал с таким кодом и содержимым уже сохранён.", 409
        ) from exc
    return original_path


def _create_document(
    *,
    document_code: str,
    document_type: str,
    title: str,
    version: str,
    checksum: str,
    original_path: Path,
    extracted_text: str,
) -> Document:
    return Document(
        document_code=document_code,
        document_type=document_type,
        title=title,
        version=version,
        document_status="uploaded",
        source_file_path=str(original_path),
        content_text=extracted_text,
        ocr_quality_status="pending" if extracted_text else "requires_text",
        checksum=checksum,
        is_demo=False,
    )


def _audit_upload(
    session: Session,
    actor: Employee,
    document: Document,
    filename: str,
    checksum: str,
    size_bytes: int,
    extraction_method: str,
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="document.uploaded",
            entity_type="document",
            entity_id=str(document.id),
            details_json=json.dumps(
                {
                    "scope": "work",
                    "document_id": document.id,
                    "document_code": document.document_code,
                    "document_type": document.document_type,
                    "version": document.version,
                    "original_filename": Path(filename).name,
                    "checksum_sha256": checksum,
                    "size_bytes": size_bytes,
                    "extraction_method": extraction_method,
                    "ocr_quality_status": document.ocr_quality_status,
                },
                ensure_ascii=False,
            ),
        )
    )


def _cleanup_upload_files(*paths: Path | None) -> None:
    for path in paths:
        if path is None:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
