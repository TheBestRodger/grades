from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import AuditEvent, Document, DocumentLink, Employee, StaffingLine
from .constants import LINK_COVERAGE_STATUSES
from .errors import DocumentOperationError
from .registry import get_document_registry
from .schemas import WorkDocumentLinkUpdate
from ..notifications.service import notify_hr_users


def set_work_document_link(
    session: Session,
    actor: Employee,
    request: WorkDocumentLinkUpdate,
) -> dict[str, object]:
    line = session.scalar(
        select(StaffingLine)
        .where(
            StaffingLine.id == request.staffing_line_id,
            StaffingLine.is_demo.is_(False),
            StaffingLine.is_active.is_(True),
        )
        .options(selectinload(StaffingLine.org_unit))
    )
    if line is None:
        raise DocumentOperationError("Рабочая штатная позиция не найдена.", 404)

    target_type = "org_unit" if request.document_type == "unit_regulation" else "staffing_line"
    target_id = line.org_unit_id if target_type == "org_unit" else line.id
    selected_document = _selected_document(session, request)
    candidates = session.scalars(
        select(DocumentLink)
        .join(DocumentLink.document)
        .where(
            DocumentLink.target_type == target_type,
            DocumentLink.target_id == target_id,
            DocumentLink.is_demo.is_(False),
            Document.document_type == request.document_type,
        )
        .options(selectinload(DocumentLink.document))
    ).all()
    before_codes = [
        link.document.document_code
        for link in candidates
        if link.link_status in LINK_COVERAGE_STATUSES
    ]
    now = datetime.now(UTC).replace(tzinfo=None)

    for link in candidates:
        if selected_document is not None and link.document_id == selected_document.id:
            link.link_status = "confirmed"
            link.confirmed_by_id = actor.id
            link.confirmed_at = now
        elif link.link_status in LINK_COVERAGE_STATUSES:
            link.link_status = "replaced" if selected_document is not None else "removed"
            link.confirmed_by_id = actor.id
            link.confirmed_at = now

    if selected_document is not None and not any(
        link.document_id == selected_document.id for link in candidates
    ):
        session.add(
            DocumentLink(
                document_id=selected_document.id,
                target_type=target_type,
                target_id=target_id,
                link_status="confirmed",
                confirmed_by_id=actor.id,
                confirmed_at=now,
                is_demo=False,
            )
        )

    _audit_link_update(session, actor, request, line, target_type, target_id, before_codes, selected_document)
    if selected_document is not None:
        notify_hr_users(
            session,
            is_demo=False,
            notification_type="document_linked",
            title="Документ привязан к структуре",
            message=(
                f"Документ «{selected_document.title}» привязан к позиции "
                f"«{line.title}»."
            ),
            target_section="documents",
            entity_type=target_type,
            entity_id=target_id,
            dedupe_key=(
                f"document-linked:{selected_document.id}:{target_type}:{target_id}"
            ),
            exclude_employee_id=actor.id,
        )
    session.flush()
    return get_document_registry(session, is_demo=False)


def _selected_document(
    session: Session,
    request: WorkDocumentLinkUpdate,
) -> Document | None:
    if request.document_id is None:
        return None
    document = session.scalar(
        select(Document).where(
            Document.id == request.document_id,
            Document.is_demo.is_(False),
            Document.document_type == request.document_type,
        )
    )
    if document is None:
        raise DocumentOperationError("Документ этого типа в рабочем реестре не найден.", 404)
    if (
        document.checksum
        and (
            document.ocr_quality_status != "good"
            or not (document.content_text or "").strip()
        )
    ):
        raise DocumentOperationError(
            "Перед подтверждением связи проверьте распознанный текст нового документа.",
            409,
        )
    return document


def _audit_link_update(
    session: Session,
    actor: Employee,
    request: WorkDocumentLinkUpdate,
    line: StaffingLine,
    target_type: str,
    target_id: int,
    before_codes: list[str],
    selected_document: Document | None,
) -> None:
    after_codes = [selected_document.document_code] if selected_document is not None else []
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="document.link_updated",
            entity_type=target_type,
            entity_id=str(target_id),
            details_json=json.dumps(
                {
                    "scope": "work",
                    "staffing_line_id": line.id,
                    "position_title": line.title,
                    "unit_name": line.org_unit.name,
                    "document_type": request.document_type,
                    "before_document_codes": before_codes,
                    "after_document_codes": after_codes,
                },
                ensure_ascii=False,
            ),
        )
    )
