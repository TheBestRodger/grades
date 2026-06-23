from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from ...models import Document, DocumentLink, OrgUnit, StaffingLine
from .work_staffing_reader import collapsed_levels, normalize_text


WORK_ROOT_PREFIX = "WORK"


def seed_marked_documents(
    session: Session,
    rows: list[dict[str, str | float | None]],
) -> None:
    line_map = {
        (line.org_unit.path, line.title): line
        for line in session.scalars(
            select(StaffingLine)
            .where(StaffingLine.is_demo.is_(False), StaffingLine.is_active.is_(True))
            .options(selectinload(StaffingLine.org_unit))
        ).all()
    }
    unit_map = {
        unit.path: unit
        for unit in session.scalars(
            select(OrgUnit).where(OrgUnit.is_demo.is_(False), OrgUnit.is_active.is_(True))
        ).all()
    }
    session.execute(
        update(DocumentLink)
        .where(DocumentLink.is_demo.is_(False), DocumentLink.link_status == "imported")
        .values(confirmed_by_id=None, confirmed_at=None)
    )

    for row in rows:
        marker = normalize_text(row.get("Отнесенный текстовый документ"))
        if not marker:
            continue
        levels = collapsed_levels(
            [
                row.get("Уровень 1"),
                row.get("Уровень 2"),
                row.get("Уровень 3"),
                row.get("Уровень 4"),
                row.get("Уровень 5"),
            ]
        )
        title = normalize_text(row.get("Должность"))
        if not levels or not title:
            continue
        _link_documents_for_row(session, row=marker, levels=levels, title=title, line_map=line_map, unit_map=unit_map)
    session.flush()


def _link_documents_for_row(
    session: Session,
    *,
    row: str,
    levels: list[str],
    title: str,
    line_map: dict[tuple[str, str], StaffingLine],
    unit_map: dict[str, OrgUnit],
) -> None:
    unit_path = f"{WORK_ROOT_PREFIX}/" + "/".join(levels)
    line = line_map.get((unit_path, title))
    unit = unit_map.get(unit_path)
    if line is None or unit is None:
        return
    for source_name in _split_documents(row):
        document_type = document_type_for_source(source_name)
        document = get_or_create_document(session, source_name, document_type)
        target_type = "org_unit" if document_type == "unit_regulation" else "staffing_line"
        target_id = unit.id if target_type == "org_unit" else line.id
        exists = session.scalar(
            select(DocumentLink.id).where(
                DocumentLink.document_id == document.id,
                DocumentLink.target_type == target_type,
                DocumentLink.target_id == target_id,
            )
        )
        if exists:
            continue
        session.add(
            DocumentLink(
                document_id=document.id,
                target_type=target_type,
                target_id=target_id,
                link_status="imported",
                is_demo=False,
            )
        )


def get_or_create_document(session: Session, source_name: str, document_type: str) -> Document:
    code = document_code(source_name, document_type)
    existing = session.scalar(select(Document).where(Document.document_code == code))
    if existing is not None:
        return existing
    document = Document(
        document_code=code,
        document_type=document_type,
        title=document_title(source_name),
        version="import-15.05.2026",
        document_status="uploaded",
        source_file_path=source_name,
        content_text=f"Документ импортирован из разметки штатного расписания: {source_name}",
        ocr_quality_status="warning",
        is_demo=False,
    )
    session.add(document)
    session.flush()
    return document


def document_type_for_source(source_name: str) -> str:
    lowered = source_name.lower()
    if "профстандарт" in lowered or "профессиональн" in lowered:
        return "professional_standard"
    if "положение" in lowered:
        return "unit_regulation"
    return "job_instruction"


def document_code(source_name: str, document_type: str) -> str:
    prefixes = {
        "job_instruction": "WORK-DI",
        "unit_regulation": "WORK-POL",
        "professional_standard": "WORK-PS",
    }
    digest = sha1(source_name.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefixes.get(document_type, 'WORK-DOC')}-{digest}"


def document_title(source_name: str) -> str:
    title = Path(source_name).stem.replace("_", " ")
    return title[:255] if title else source_name[:255]


def _split_documents(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]
