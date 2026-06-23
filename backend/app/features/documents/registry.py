from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import Document, Employee, OrgUnit, StaffingLine
from ..organization.service import visible_unit_ids
from .constants import DOCUMENT_COVERAGE_STATUSES
from .errors import DocumentOperationError
from .serializers import document_registry_payload, link_is_visible


def get_manager_document_registry(session: Session, actor: Employee) -> dict[str, object]:
    if actor.system_role != "manager":
        raise DocumentOperationError("Документы зоны доступны только руководителю.", 403)
    return get_document_registry(
        session,
        is_demo=actor.is_demo,
        visible_unit_ids=visible_unit_ids(session, actor, actor.is_demo),
        note=(
            "Документы доступны только в зоне ответственности руководителя. "
            "Просмотр не изменяет подтвержденные HR связи."
        ),
    )


def get_document_registry(
    session: Session,
    is_demo: bool = True,
    visible_unit_ids: set[int] | None = None,
    note: str | None = None,
) -> dict[str, object]:
    documents = session.scalars(
        select(Document)
        .where(Document.is_demo.is_(is_demo))
        .options(selectinload(Document.links))
        .order_by(Document.document_type, Document.document_code)
    ).all()
    staffing_query = select(StaffingLine).where(
        StaffingLine.is_demo.is_(is_demo), StaffingLine.is_active.is_(True)
    )
    org_unit_query = select(OrgUnit).where(
        OrgUnit.is_demo.is_(is_demo), OrgUnit.is_active.is_(True)
    )
    if visible_unit_ids is not None:
        staffing_query = staffing_query.where(StaffingLine.org_unit_id.in_(visible_unit_ids))
        org_unit_query = org_unit_query.where(OrgUnit.id.in_(visible_unit_ids))
    staffing_lines = session.scalars(
        staffing_query.options(selectinload(StaffingLine.org_unit)).order_by(StaffingLine.id)
    ).all()
    org_units = session.scalars(org_unit_query.order_by(OrgUnit.path)).all()

    line_map = {line.id: line for line in staffing_lines}
    unit_map = {unit.id: unit for unit in org_units}
    visible_targets = (
        {"staffing_line": set(line_map), "org_unit": set(unit_map)}
        if visible_unit_ids is not None
        else None
    )
    if visible_targets is not None:
        documents = [
            document
            for document in documents
            if document.document_status in DOCUMENT_COVERAGE_STATUSES
            and any(link_is_visible(link, visible_targets) for link in document.links)
        ]

    return document_registry_payload(
        documents=documents,
        staffing_lines=staffing_lines,
        org_units=org_units,
        is_demo=is_demo,
        visible_targets=visible_targets,
        note=note,
    )

