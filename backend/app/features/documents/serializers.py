from __future__ import annotations

from collections import Counter
from typing import Any

from ...models import Document, DocumentLink, OrgUnit, StaffingLine
from .constants import (
    DOCUMENT_COVERAGE_STATUSES,
    DOCUMENT_TYPE_LABELS,
    LINK_COVERAGE_STATUSES,
    OCR_QUALITY_LABELS,
)
from .coverage import covered_target_ids, org_unit_coverage, staffing_line_coverage


def registry_note(is_demo: bool) -> str:
    if is_demo:
        return "Документы текущего контура используются для проверки покрытия должностей."
    return (
        "Рабочая структура импортирована из размеченного ШР. HR может загрузить "
        "новый оригинал, проверить извлечённый или распознанный текст и только затем "
        "подтвердить его связь с позицией."
    )


def link_is_visible(link: DocumentLink, visible_targets: dict[str, set[int]]) -> bool:
    return (
        link.link_status in LINK_COVERAGE_STATUSES
        and link.target_id in visible_targets.get(link.target_type, set())
    )


def confirmed_links_by_type(
    documents: list[Document],
) -> dict[tuple[str, str, int], list[tuple[Document, DocumentLink]]]:
    result: dict[tuple[str, str, int], list[tuple[Document, DocumentLink]]] = {}
    for document in documents:
        if document.document_status not in DOCUMENT_COVERAGE_STATUSES:
            continue
        for link in document.links:
            if link.link_status not in LINK_COVERAGE_STATUSES:
                continue
            key = (document.document_type, link.target_type, link.target_id)
            result.setdefault(key, []).append((document, link))
    return result


def document_registry_payload(
    *,
    documents: list[Document],
    staffing_lines: list[StaffingLine],
    org_units: list[OrgUnit],
    is_demo: bool,
    visible_targets: dict[str, set[int]] | None,
    note: str | None,
) -> dict[str, object]:
    ocr_counts = Counter(document.ocr_quality_status for document in documents)
    links_by_type = confirmed_links_by_type(documents)
    line_map = {line.id: line for line in staffing_lines}
    unit_map = {unit.id: unit for unit in org_units}
    return {
        "scope": "demo" if is_demo else "work",
        "note": note or registry_note(is_demo),
        "coverage": {
            "job_instruction": staffing_line_coverage(
                "job_instruction",
                staffing_lines,
                covered_target_ids(documents, "job_instruction", "staffing_line"),
            ),
            "professional_standard": staffing_line_coverage(
                "professional_standard",
                staffing_lines,
                covered_target_ids(documents, "professional_standard", "staffing_line"),
            ),
            "unit_regulation": org_unit_coverage(
                "unit_regulation",
                org_units,
                covered_target_ids(documents, "unit_regulation", "org_unit"),
            ),
        },
        "documents_total": len(documents),
        "confirmed_documents": sum(
            1 for document in documents if document.document_status == "confirmed"
        ),
        "ocr_quality_counts": dict(ocr_counts),
        "position_matrix": [
            position_matrix_payload(line, links_by_type)
            for line in staffing_lines
        ],
        "documents": [
            document_payload(document, line_map, unit_map, visible_targets)
            for document in documents
        ],
    }


def position_matrix_payload(
    line: StaffingLine,
    links_by_type: dict[tuple[str, str, int], list[tuple[Document, DocumentLink]]],
) -> dict[str, object]:
    job_instruction = matrix_cell(
        links_by_type.get(("job_instruction", "staffing_line", line.id), [])
    )
    unit_regulation = matrix_cell(
        links_by_type.get(("unit_regulation", "org_unit", line.org_unit_id), [])
    )
    professional_standard = matrix_cell(
        links_by_type.get(("professional_standard", "staffing_line", line.id), [])
    )
    cells = [job_instruction, unit_regulation, professional_standard]
    covered = sum(1 for cell in cells if cell["covered"])
    return {
        "staffing_line_id": line.id,
        "position_title": line.title,
        "unit_name": line.org_unit.name,
        "covered_count": covered,
        "required_count": 3,
        "coverage_percent": round(covered / 3 * 100, 2),
        "job_instruction": job_instruction,
        "unit_regulation": unit_regulation,
        "professional_standard": professional_standard,
    }


def matrix_cell(documents: list[tuple[Document, DocumentLink]]) -> dict[str, object]:
    return {
        "covered": bool(documents),
        "documents": [
            {
                "document_id": document.id,
                "document_code": document.document_code,
                "title": document.title,
                "link_status": link.link_status,
            }
            for document, link in sorted(documents, key=lambda item: item[0].document_code)
        ],
    }


def document_payload(
    document: Document,
    line_map: dict[int, StaffingLine],
    unit_map: dict[int, OrgUnit],
    visible_targets: dict[str, set[int]] | None = None,
) -> dict[str, Any]:
    return {
        "id": document.id,
        "document_code": document.document_code,
        "document_type": document.document_type,
        "document_type_label": DOCUMENT_TYPE_LABELS.get(
            document.document_type,
            document.document_type,
        ),
        "title": document.title,
        "version": document.version,
        "document_status": document.document_status,
        "ocr_quality_status": document.ocr_quality_status,
        "ocr_quality_label": OCR_QUALITY_LABELS.get(
            document.ocr_quality_status,
            document.ocr_quality_status,
        ),
        "has_stored_original": bool(document.checksum and document.source_file_path),
        "has_extracted_text": bool(document.content_text),
        "content_text": document.content_text,
        "is_demo": document.is_demo,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "links": [
            link_payload(link, line_map, unit_map)
            for link in sorted(document.links, key=lambda item: (item.target_type, item.target_id))
            if visible_targets is None or link_is_visible(link, visible_targets)
        ],
    }


def link_payload(
    link: DocumentLink,
    line_map: dict[int, StaffingLine],
    unit_map: dict[int, OrgUnit],
) -> dict[str, object]:
    return {
        "target_type": link.target_type,
        "target_id": link.target_id,
        "target_label": target_label(link, line_map, unit_map),
        "link_status": link.link_status,
        "confirmed_at": link.confirmed_at.isoformat() if link.confirmed_at else None,
    }


def target_label(
    link: DocumentLink,
    line_map: dict[int, StaffingLine],
    unit_map: dict[int, OrgUnit],
) -> str:
    if link.target_type == "staffing_line":
        line = line_map.get(link.target_id)
        return f"{line.title} / {line.org_unit.name}" if line else "Штатная позиция удалена"
    if link.target_type == "org_unit":
        unit = unit_map.get(link.target_id)
        return unit.name if unit else "Подразделение удалено"
    return f"{link.target_type}:{link.target_id}"
