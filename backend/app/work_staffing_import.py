from __future__ import annotations

from pathlib import Path
from hashlib import sha1
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from .config import PROJECT_ROOT
from .models import Document, DocumentLink, OrgUnit, StaffingLine


MARKED_WORK_STAFFING_FILE = (
    PROJECT_ROOT / "Изначальные документы_история" / "ШР по уровням на 15.05.26_размечено.xlsx"
)
WORK_STAFFING_FILE = (
    MARKED_WORK_STAFFING_FILE
    if MARKED_WORK_STAFFING_FILE.exists()
    else PROJECT_ROOT / "ШР по уровням на 15.05.26.xlsx"
)
WORK_ROOT_PREFIX = "WORK"
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def seed_work_staffing_data(session: Session, source_path: Path | None = None) -> None:
    source_path = source_path or WORK_STAFFING_FILE
    if not source_path.exists():
        return
    rows = list(_read_staffing_rows(source_path))
    if not rows:
        return

    existing = session.scalar(
        select(OrgUnit.id).where(OrgUnit.is_demo.is_(False), OrgUnit.path.like(f"{WORK_ROOT_PREFIX}/%"))
    )
    if existing:
        _seed_marked_documents(session, rows)
        return

    unit_by_path: dict[str, OrgUnit] = {}
    line_totals: dict[tuple[str, str], tuple[float, float]] = {}

    for row in rows:
        title = _normalize_text(row.get("Должность"))
        if not title:
            continue

        levels = _collapsed_levels(
            [
                row.get("Уровень 1"),
                row.get("Уровень 2"),
                row.get("Уровень 3"),
                row.get("Уровень 4"),
                row.get("Уровень 5"),
            ]
        )
        if not levels:
            continue

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

        unit_path = f"{WORK_ROOT_PREFIX}/" + "/".join(levels)
        key = (unit_path, title)
        approved = _to_float(row.get("Ед. по ШР"))
        occupied = _to_float(row.get("Занято"))
        current_approved, current_occupied = line_totals.get(key, (0.0, 0.0))
        line_totals[key] = (current_approved + approved, current_occupied + occupied)

    for (unit_path, title), (approved, occupied) in line_totals.items():
        unit = unit_by_path[unit_path]
        session.add(
            StaffingLine(
                org_unit=unit,
                title=title,
                approved_fte=round(approved, 4),
                reported_occupied_fte=round(occupied, 4),
                is_demo=False,
            )
        )

    session.flush()
    _seed_marked_documents(session, rows)


def _read_staffing_rows(path: Path) -> list[dict[str, str | float | None]]:
    with ZipFile(path) as archive:
        shared_strings = _shared_strings(archive)
        sheet_name = _first_sheet_name(archive)
        root = ET.fromstring(archive.read(sheet_name))

    rows: list[list[str | float | None]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        values: list[str | float | None] = []
        for cell in row.findall("a:c", NS):
            column_index = _column_index(cell.attrib.get("r", ""))
            while len(values) < column_index:
                values.append(None)
            values.append(_cell_value(cell, shared_strings))
        rows.append(values)

    if not rows:
        return []
    headers = [_normalize_text(value) for value in rows[0]]
    result: list[dict[str, str | float | None]] = []
    for row in rows[1:]:
        if not any(_normalize_text(value) for value in row):
            continue
        result.append(
            {
                header: row[index] if index < len(row) else None
                for index, header in enumerate(headers)
                if header
            }
        )
    return result


def _seed_marked_documents(session: Session, rows: list[dict[str, str | float | None]]) -> None:
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
        marker = _normalize_text(row.get("Отнесенный текстовый документ"))
        if not marker:
            continue
        levels = _collapsed_levels(
            [
                row.get("Уровень 1"),
                row.get("Уровень 2"),
                row.get("Уровень 3"),
                row.get("Уровень 4"),
                row.get("Уровень 5"),
            ]
        )
        title = _normalize_text(row.get("Должность"))
        if not levels or not title:
            continue
        unit_path = f"{WORK_ROOT_PREFIX}/" + "/".join(levels)
        line = line_map.get((unit_path, title))
        unit = unit_map.get(unit_path)
        if line is None or unit is None:
            continue
        for source_name in _split_documents(marker):
            document_type = _document_type(source_name)
            document = _get_or_create_document(session, source_name, document_type)
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
    session.flush()


def _split_documents(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _document_type(source_name: str) -> str:
    lowered = source_name.lower()
    if "профстандарт" in lowered or "профессиональн" in lowered:
        return "professional_standard"
    if "положение" in lowered:
        return "unit_regulation"
    return "job_instruction"


def _get_or_create_document(session: Session, source_name: str, document_type: str) -> Document:
    code = _document_code(source_name, document_type)
    existing = session.scalar(select(Document).where(Document.document_code == code))
    if existing is not None:
        return existing
    document = Document(
        document_code=code,
        document_type=document_type,
        title=_document_title(source_name),
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


def _document_code(source_name: str, document_type: str) -> str:
    prefixes = {
        "job_instruction": "WORK-DI",
        "unit_regulation": "WORK-POL",
        "professional_standard": "WORK-PS",
    }
    digest = sha1(source_name.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefixes.get(document_type, 'WORK-DOC')}-{digest}"


def _document_title(source_name: str) -> str:
    title = Path(source_name).stem.replace("_", " ")
    return title[:255] if title else source_name[:255]


def _first_sheet_name(archive: ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook.find(".//a:sheets/a:sheet", NS)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets.")
    rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    rel = rels.find(
        f".//{{http://schemas.openxmlformats.org/package/2006/relationships}}Relationship[@Id='{rel_id}']"
    )
    if rel is None:
        raise ValueError("Workbook sheet relationship is missing.")
    target = rel.attrib["Target"].lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("a:si", NS):
        texts = [text.text or "" for text in item.findall(".//a:t", NS)]
        values.append("".join(texts))
    return values


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | float | None:
    cell_type = cell.attrib.get("t")
    value = cell.find("a:v", NS)
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", NS))
    if value is None or value.text is None:
        return None
    if cell_type == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    if cell_type == "str":
        return value.text
    try:
        return float(value.text)
    except ValueError:
        return value.text


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter.upper()) - ord("A") + 1
    return max(result - 1, 0)


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).replace("\xa0", " ").split())


def _collapsed_levels(values: list[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _normalize_text(value)
        if not text or (result and result[-1] == text):
            continue
        result.append(text)
    return result


def _to_float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    text = _normalize_text(value).replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0
