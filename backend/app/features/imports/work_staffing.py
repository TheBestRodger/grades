from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import PROJECT_ROOT
from ...models import OrgUnit, StaffingLine
from .work_staffing_documents import (
    document_code,
    document_title,
    document_type_for_source,
    get_or_create_document,
    seed_marked_documents,
)
from .work_staffing_reader import (
    collapsed_levels,
    normalize_text,
    read_staffing_rows,
    to_float,
)


MARKED_WORK_STAFFING_FILE = (
    PROJECT_ROOT
    / "backend"
    / "source_documents"
    / "Изначальные документы_история"
    / "ШР по уровням на 15.05.26_размечено.xlsx"
)
WORK_STAFFING_FILE = (
    MARKED_WORK_STAFFING_FILE
    if MARKED_WORK_STAFFING_FILE.exists()
    else PROJECT_ROOT / "backend" / "source_documents" / "ШР по уровням на 15.05.26.xlsx"
)
WORK_ROOT_PREFIX = "WORK"


def seed_work_staffing_data(session: Session, source_path: Path | None = None) -> None:
    source_path = source_path or WORK_STAFFING_FILE
    if not source_path.exists():
        return
    rows = list(read_staffing_rows(source_path))
    if not rows:
        return

    existing = session.scalar(
        select(OrgUnit.id).where(
            OrgUnit.is_demo.is_(False),
            OrgUnit.path.like(f"{WORK_ROOT_PREFIX}/%"),
        )
    )
    if existing:
        seed_marked_documents(session, rows)
        return

    unit_by_path: dict[str, OrgUnit] = {}
    line_totals: dict[tuple[str, str], tuple[float, float]] = {}
    for row in rows:
        _collect_staffing_row(session, row, unit_by_path, line_totals)

    for (unit_path, title), (approved, occupied) in line_totals.items():
        session.add(
            StaffingLine(
                org_unit=unit_by_path[unit_path],
                title=title,
                approved_fte=round(approved, 4),
                reported_occupied_fte=round(occupied, 4),
                is_demo=False,
            )
        )

    session.flush()
    seed_marked_documents(session, rows)


def _collect_staffing_row(
    session: Session,
    row: dict[str, str | float | None],
    unit_by_path: dict[str, OrgUnit],
    line_totals: dict[tuple[str, str], tuple[float, float]],
) -> None:
    title = normalize_text(row.get("Должность"))
    if not title:
        return
    levels = collapsed_levels(
        [
            row.get("Уровень 1"),
            row.get("Уровень 2"),
            row.get("Уровень 3"),
            row.get("Уровень 4"),
            row.get("Уровень 5"),
        ]
    )
    if not levels:
        return
    _ensure_units(session, levels, unit_by_path)
    unit_path = f"{WORK_ROOT_PREFIX}/" + "/".join(levels)
    approved = to_float(row.get("Ед. по ШР"))
    occupied = to_float(row.get("Занято"))
    current_approved, current_occupied = line_totals.get((unit_path, title), (0.0, 0.0))
    line_totals[(unit_path, title)] = (
        current_approved + approved,
        current_occupied + occupied,
    )


def _ensure_units(
    session: Session,
    levels: list[str],
    unit_by_path: dict[str, OrgUnit],
) -> None:
    parent: OrgUnit | None = None
    parts: list[str] = []
    for level in levels:
        parts.append(level)
        path = f"{WORK_ROOT_PREFIX}/" + "/".join(parts)
        unit = unit_by_path.get(path)
        if unit is None:
            unit = OrgUnit(name=level, path=path, parent=parent, is_demo=False)
            session.add(unit)
            session.flush()
            unit_by_path[path] = unit
        parent = unit


_read_staffing_rows = read_staffing_rows
_seed_marked_documents = seed_marked_documents
_document_type = document_type_for_source
_get_or_create_document = get_or_create_document
_document_code = document_code
_document_title = document_title
_normalize_text = normalize_text
_collapsed_levels = collapsed_levels
_to_float = to_float
