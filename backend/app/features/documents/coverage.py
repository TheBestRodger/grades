from __future__ import annotations

from ...models import Document, DocumentLink, OrgUnit, StaffingLine
from .constants import DOCUMENT_COVERAGE_STATUSES, DOCUMENT_TYPE_LABELS, LINK_COVERAGE_STATUSES


def covered_target_ids(
    documents: list[Document],
    document_type: str,
    target_type: str,
) -> set[int]:
    return {
        link.target_id
        for document in documents
        if document.document_type == document_type
        and document.document_status in DOCUMENT_COVERAGE_STATUSES
        for link in document.links
        if link.target_type == target_type and link.link_status in LINK_COVERAGE_STATUSES
    }


def staffing_line_coverage(
    document_type: str,
    lines: list[StaffingLine],
    covered_ids: set[int],
) -> dict[str, object]:
    gaps = [
        {
            "target_type": "staffing_line",
            "target_id": line.id,
            "label": f"{line.title} / {line.org_unit.name}",
            "title": line.title,
            "unit_name": line.org_unit.name,
        }
        for line in lines
        if line.id not in covered_ids
    ]
    return coverage_payload(document_type, len(lines), len(lines) - len(gaps), gaps)


def org_unit_coverage(
    document_type: str,
    units: list[OrgUnit],
    covered_ids: set[int],
) -> dict[str, object]:
    gaps = [
        {
            "target_type": "org_unit",
            "target_id": unit.id,
            "label": unit.name,
            "name": unit.name,
            "path": visible_org_path(unit.path),
        }
        for unit in units
        if unit.id not in covered_ids
    ]
    return coverage_payload(document_type, len(units), len(units) - len(gaps), gaps)


def visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def coverage_payload(
    document_type: str,
    total: int,
    covered: int,
    gaps: list[dict[str, object]],
) -> dict[str, object]:
    percent = round((covered / total) * 100, 2) if total else 0
    return {
        "document_type": document_type,
        "label": DOCUMENT_TYPE_LABELS[document_type],
        "total": total,
        "covered": covered,
        "missing": len(gaps),
        "percent": percent,
        "gaps": gaps,
    }

