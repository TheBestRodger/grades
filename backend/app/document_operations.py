from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import AuditEvent, Document, DocumentLink, Employee, OrgUnit, StaffingLine
from .organization import _visible_unit_ids
from .schemas import WorkDocumentLinkUpdate, WorkDocumentQualityUpdate


DOCUMENT_TYPE_LABELS = {
    "job_instruction": "Должностная инструкция",
    "unit_regulation": "Положение подразделения",
    "professional_standard": "Профстандарт",
}

OCR_QUALITY_LABELS = {
    "manual_demo": "Текст внесен вручную",
    "pending": "Текст ожидает проверки HR",
    "requires_text": "Нужно внести распознанный текст",
    "good": "Текст проверен HR",
    "warning": "Текст требует исправления",
}
DOCUMENT_COVERAGE_STATUSES = {"confirmed", "uploaded"}
LINK_COVERAGE_STATUSES = {"confirmed", "imported"}
UPLOAD_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class DocumentOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_manager_document_registry(session: Session, actor: Employee) -> dict[str, object]:
    if actor.system_role != "manager":
        raise DocumentOperationError("Документы зоны доступны только руководителю.", 403)
    return get_document_registry(
        session,
        is_demo=actor.is_demo,
        visible_unit_ids=_visible_unit_ids(session, actor, actor.is_demo),
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
            and any(_link_is_visible(link, visible_targets) for link in document.links)
        ]
    ocr_counts = Counter(document.ocr_quality_status for document in documents)
    links_by_type = _confirmed_links_by_type(documents)

    return {
        "scope": "demo" if is_demo else "work",
        "note": note or _registry_note(is_demo),
        "coverage": {
            "job_instruction": _staffing_line_coverage(
                "job_instruction",
                staffing_lines,
                _covered_target_ids(documents, "job_instruction", "staffing_line"),
            ),
            "professional_standard": _staffing_line_coverage(
                "professional_standard",
                staffing_lines,
                _covered_target_ids(documents, "professional_standard", "staffing_line"),
            ),
            "unit_regulation": _org_unit_coverage(
                "unit_regulation",
                org_units,
                _covered_target_ids(documents, "unit_regulation", "org_unit"),
            ),
        },
        "documents_total": len(documents),
        "confirmed_documents": sum(
            1 for document in documents if document.document_status == "confirmed"
        ),
        "ocr_quality_counts": dict(ocr_counts),
        "position_matrix": [
            _position_matrix_payload(line, links_by_type)
            for line in staffing_lines
        ],
        "documents": [
            _document_payload(document, line_map, unit_map, visible_targets)
            for document in documents
        ],
    }


def _registry_note(is_demo: bool) -> str:
    if is_demo:
        return "Документы текущего контура используются для проверки покрытия должностей."
    return (
        "Рабочая структура импортирована из размеченного ШР. HR может загрузить "
        "новый оригинал, проверить извлечённый или распознанный текст и только затем "
        "подтвердить его связь с позицией."
    )


def _link_is_visible(link: DocumentLink, visible_targets: dict[str, set[int]]) -> bool:
    return (
        link.link_status in LINK_COVERAGE_STATUSES
        and link.target_id in visible_targets.get(link.target_type, set())
    )


def _confirmed_links_by_type(
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


def _position_matrix_payload(
    line: StaffingLine,
    links_by_type: dict[tuple[str, str, int], list[tuple[Document, DocumentLink]]],
) -> dict[str, object]:
    job_instruction = _matrix_cell(
        links_by_type.get(("job_instruction", "staffing_line", line.id), [])
    )
    unit_regulation = _matrix_cell(
        links_by_type.get(("unit_regulation", "org_unit", line.org_unit_id), [])
    )
    professional_standard = _matrix_cell(
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


def _matrix_cell(documents: list[tuple[Document, DocumentLink]]) -> dict[str, object]:
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
    selected_document = None
    if request.document_id is not None:
        selected_document = session.scalar(
            select(Document).where(
                Document.id == request.document_id,
                Document.is_demo.is_(False),
                Document.document_type == request.document_type,
            )
        )
        if selected_document is None:
            raise DocumentOperationError("Документ этого типа в рабочем реестре не найден.", 404)
        if (
            selected_document.checksum
            and (
                selected_document.ocr_quality_status != "good"
                or not (selected_document.content_text or "").strip()
            )
        ):
            raise DocumentOperationError(
                "Перед подтверждением связи проверьте распознанный текст нового документа.",
                409,
            )

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
    session.flush()
    return get_document_registry(session, is_demo=False)


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
    document_code = document_code.strip()
    title = " ".join(title.split())
    version = version.strip()
    suffix = Path(filename).suffix.lower()
    if document_type not in DOCUMENT_TYPE_LABELS:
        raise DocumentOperationError("Неизвестный тип документа.")
    if not document_code or len(document_code) > 80:
        raise DocumentOperationError("Укажите код документа длиной до 80 символов.")
    if not title or len(title) > 255:
        raise DocumentOperationError("Укажите название документа длиной до 255 символов.")
    if not version or len(version) > 80:
        raise DocumentOperationError("Укажите версию документа длиной до 80 символов.")
    if suffix not in UPLOAD_EXTENSIONS:
        raise DocumentOperationError("Поддерживаются файлы TXT, MD, DOCX и PDF.")
    if not content:
        raise DocumentOperationError("Файл пуст.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentOperationError("Размер файла превышает 25 МБ.")
    if session.scalar(select(Document).where(Document.document_code == document_code)) is not None:
        raise DocumentOperationError("Документ с таким кодом уже существует.", 409)

    checksum = sha256(content).hexdigest()
    duplicate = session.scalar(
        select(Document).where(Document.is_demo.is_(False), Document.checksum == checksum)
    )
    if duplicate is not None:
        raise DocumentOperationError("Этот оригинал уже загружен в рабочий реестр.", 409)

    extracted_text, extraction_method = _extract_initial_text(content, suffix)
    quality_status = "pending" if extracted_text else "requires_text"
    original_dir = storage_dir.resolve() / "originals"
    original_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{_storage_token(document_code)}__{checksum[:12]}{suffix}"
    original_path = original_dir / stored_name
    try:
        with original_path.open("xb") as source_file:
            source_file.write(content)
    except FileExistsError as exc:
        raise DocumentOperationError("Оригинал с таким кодом и содержимым уже сохранён.", 409) from exc

    document = Document(
        document_code=document_code,
        document_type=document_type,
        title=title,
        version=version,
        document_status="uploaded",
        source_file_path=str(original_path),
        content_text=extracted_text,
        ocr_quality_status=quality_status,
        checksum=checksum,
        is_demo=False,
    )
    session.add(document)
    session.flush()
    if extracted_text:
        document.extracted_text_path = str(
            _store_text_snapshot(storage_dir, document.document_code, checksum, extracted_text)
        )
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
                    "size_bytes": len(content),
                    "extraction_method": extraction_method,
                    "ocr_quality_status": quality_status,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return get_document_registry(session, is_demo=False)


def review_work_document_quality(
    session: Session,
    actor: Employee,
    storage_dir: Path,
    document_id: int,
    request: WorkDocumentQualityUpdate,
) -> dict[str, object]:
    document = session.scalar(
        select(Document).where(Document.id == document_id, Document.is_demo.is_(False))
    )
    if document is None:
        raise DocumentOperationError("Рабочий документ не найден.", 404)
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
            _store_text_snapshot(storage_dir, document.document_code, text_hash, request.extracted_text)
        )
    else:
        text_hash = None
        document.extracted_text_path = None
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
                    "has_text": bool(request.extracted_text),
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return get_document_registry(session, is_demo=False)


def get_work_document_source(
    session: Session,
    storage_dir: Path,
    document_id: int,
) -> tuple[bytes, str, str]:
    document = session.scalar(
        select(Document).where(Document.id == document_id, Document.is_demo.is_(False))
    )
    if document is None:
        raise DocumentOperationError("Рабочий документ не найден.", 404)
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


def _extract_initial_text(content: bytes, suffix: str) -> tuple[str | None, str]:
    if suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise DocumentOperationError("Текстовый файл должен быть сохранён в UTF-8.") from exc
        return (text or None), "utf8_text"
    if suffix == ".docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                root = ET.fromstring(archive.read("word/document.xml"))
        except (BadZipFile, KeyError, ET.ParseError) as exc:
            raise DocumentOperationError("Не удалось прочитать DOCX документ.") from exc
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text = "\n".join(
            " ".join(fragment.text or "" for fragment in paragraph.findall(".//w:t", namespace)).strip()
            for paragraph in root.findall(".//w:p", namespace)
        ).strip()
        return (text or None), "docx_text"
    return None, "manual_ocr_required"


def _storage_token(document_code: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", document_code).strip("._")
    return token[:60] or "document"


def _store_text_snapshot(storage_dir: Path, document_code: str, digest: str, text: str) -> Path:
    text_dir = storage_dir.resolve() / "extracted"
    text_dir.mkdir(parents=True, exist_ok=True)
    path = text_dir / f"{_storage_token(document_code)}__{digest[:12]}.txt"
    if not path.exists():
        path.write_text(text, encoding="utf-8")
    return path


def _covered_target_ids(
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


def _staffing_line_coverage(
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
    return _coverage_payload(document_type, len(lines), len(lines) - len(gaps), gaps)


def _org_unit_coverage(
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
            "path": _visible_org_path(unit.path),
        }
        for unit in units
        if unit.id not in covered_ids
    ]
    return _coverage_payload(document_type, len(units), len(units) - len(gaps), gaps)


def _visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def _coverage_payload(
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


def _document_payload(
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
            _link_payload(link, line_map, unit_map)
            for link in sorted(document.links, key=lambda item: (item.target_type, item.target_id))
            if visible_targets is None or _link_is_visible(link, visible_targets)
        ],
    }


def _link_payload(
    link: DocumentLink,
    line_map: dict[int, StaffingLine],
    unit_map: dict[int, OrgUnit],
) -> dict[str, object]:
    return {
        "target_type": link.target_type,
        "target_id": link.target_id,
        "target_label": _target_label(link, line_map, unit_map),
        "link_status": link.link_status,
        "confirmed_at": link.confirmed_at.isoformat() if link.confirmed_at else None,
    }


def _target_label(
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
