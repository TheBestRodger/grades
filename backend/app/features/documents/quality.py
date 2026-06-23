from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...infrastructure.files.document_storage import store_text_snapshot
from ...models import AuditEvent, Document, Employee
from .errors import DocumentOperationError
from .registry import get_document_registry
from .schemas import WorkDocumentQualityUpdate


def review_work_document_quality(
    session: Session,
    actor: Employee,
    storage_dir: Path,
    document_id: int,
    request: WorkDocumentQualityUpdate,
) -> dict[str, object]:
    document = _work_document(session, document_id)
    if request.ocr_quality_status == "good" and not request.extracted_text:
        raise DocumentOperationError("Для подтверждения качества внесите текст документа.")

    before_status = document.ocr_quality_status
    before_text_hash = (
        sha256(document.content_text.encode("utf-8")).hexdigest()
        if document.content_text
        else None
    )
    document.content_text = request.extracted_text or None
    document.ocr_quality_status = request.ocr_quality_status
    if request.extracted_text:
        text_hash = sha256(request.extracted_text.encode("utf-8")).hexdigest()
        document.extracted_text_path = str(
            store_text_snapshot(storage_dir, document.document_code, text_hash, request.extracted_text)
        )
    else:
        text_hash = None
        document.extracted_text_path = None
    _audit_quality_review(session, actor, document, before_status, before_text_hash, text_hash)
    session.flush()
    return get_document_registry(session, is_demo=False)


def get_work_document_source(
    session: Session,
    storage_dir: Path,
    document_id: int,
) -> tuple[bytes, str, str]:
    document = _work_document(session, document_id)
    if not document.checksum or not document.source_file_path:
        raise DocumentOperationError("Для импортированной связи оригинал ещё не загружен.", 404)
    source_path = Path(document.source_file_path).resolve()
    originals_dir = (storage_dir.resolve() / "originals").resolve()
    if originals_dir not in source_path.parents or not source_path.is_file():
        raise DocumentOperationError("Оригинал документа недоступен.", 404)
    media_types = {
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    return (
        source_path.read_bytes(),
        source_path.name,
        media_types.get(source_path.suffix.lower(), "application/octet-stream"),
    )


def _work_document(session: Session, document_id: int) -> Document:
    document = session.scalar(
        select(Document).where(Document.id == document_id, Document.is_demo.is_(False))
    )
    if document is None:
        raise DocumentOperationError("Рабочий документ не найден.", 404)
    return document


def _audit_quality_review(
    session: Session,
    actor: Employee,
    document: Document,
    before_status: str,
    before_text_hash: str | None,
    text_hash: str | None,
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="document.quality_reviewed",
            entity_type="document",
            entity_id=str(document.id),
            details_json=json.dumps(
                {
                    "scope": "work",
                    "document_id": document.id,
                    "document_code": document.document_code,
                    "before_quality_status": before_status,
                    "after_quality_status": document.ocr_quality_status,
                    "before_text_sha256": before_text_hash,
                    "after_text_sha256": text_hash,
                    "has_text": bool(document.content_text),
                },
                ensure_ascii=False,
            ),
        )
    )

