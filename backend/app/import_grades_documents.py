from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import json
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import PROJECT_ROOT, Settings
from .db import Database
from .document_operations import _extract_initial_text, _storage_token, _store_text_snapshot
from .models import Document, DocumentLink, OrgUnit, StaffingLine
from .work_staffing_import import (
    WORK_ROOT_PREFIX,
    _collapsed_levels,
    _normalize_text,
    _read_staffing_rows,
)


GRADES_DIR = PROJECT_ROOT / "Грейды"
DOCUMENTS_DIR = GRADES_DIR / "ИИ_Тестовая"
DOCUMENT_NAME_RE = re.compile(r"^(INS|REG)_(\d+)_(.+)\.docx$", re.IGNORECASE)


@dataclass(frozen=True)
class DocumentSpec:
    source_path: Path
    kind: str
    number: str
    document_code: str
    document_type: str
    title: str


@dataclass
class ImportReport:
    apply: bool
    staffing_file: str
    documents_dir: str
    rows_total: int = 0
    units_matched: int = 0
    units_updated: int = 0
    unit_code_conflicts: list[dict[str, object]] = field(default_factory=list)
    units_unmatched: list[str] = field(default_factory=list)
    staffing_lines_matched: int = 0
    staffing_lines_updated: int = 0
    staffing_line_code_conflicts: list[dict[str, object]] = field(default_factory=list)
    staffing_lines_unmatched: list[dict[str, object]] = field(default_factory=list)
    documents_scanned: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents_existing: int = 0
    documents_skipped: list[dict[str, object]] = field(default_factory=list)
    links_created: int = 0
    links_existing: int = 0
    links_unmatched: list[dict[str, object]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": "apply" if self.apply else "dry-run",
            "staffing_file": self.staffing_file,
            "documents_dir": self.documents_dir,
            "structure": {
                "rows_total": self.rows_total,
                "units_matched": self.units_matched,
                "units_updated": self.units_updated,
                "unit_code_conflicts": self.unit_code_conflicts,
                "units_unmatched": self.units_unmatched,
                "staffing_lines_matched": self.staffing_lines_matched,
                "staffing_lines_updated": self.staffing_lines_updated,
                "staffing_line_code_conflicts": self.staffing_line_code_conflicts,
                "staffing_lines_unmatched": self.staffing_lines_unmatched,
            },
            "documents": {
                "documents_scanned": self.documents_scanned,
                "documents_created": self.documents_created,
                "documents_updated": self.documents_updated,
                "documents_existing": self.documents_existing,
                "documents_skipped": self.documents_skipped,
                "links_created": self.links_created,
                "links_existing": self.links_existing,
                "links_unmatched": self.links_unmatched,
            },
        }


def import_grades_documents(
    session: Session,
    *,
    staffing_file: Path,
    documents_dir: Path,
    storage_dir: Path,
    apply_changes: bool,
) -> ImportReport:
    report = ImportReport(
        apply=apply_changes,
        staffing_file=str(staffing_file),
        documents_dir=str(documents_dir),
    )
    rows = _read_staffing_rows(staffing_file)
    report.rows_total = len(rows)

    units = session.scalars(
        select(OrgUnit).where(OrgUnit.is_demo.is_(False), OrgUnit.is_active.is_(True))
    ).all()
    staffing_lines = session.scalars(
        select(StaffingLine)
        .where(StaffingLine.is_demo.is_(False), StaffingLine.is_active.is_(True))
        .options(selectinload(StaffingLine.org_unit))
    ).all()
    unit_by_path = {unit.path: unit for unit in units}
    lines_by_key: dict[tuple[str, str], list[StaffingLine]] = {}
    for line in staffing_lines:
        key = (line.org_unit.path, _normalize_title(line.title))
        lines_by_key.setdefault(key, []).append(line)

    unit_codes: dict[str, set[str]] = {}
    line_codes: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        levels = _collapsed_levels(
            [
                row.get("Уровень 1"),
                row.get("Уровень 2"),
                row.get("Уровень 3"),
                row.get("Уровень 4"),
                row.get("Уровень 5"),
            ]
        )
        title = _normalize_title(row.get("Должность"))
        department_code = _normalize_code(row.get("Код подразделения"))
        position_code = _normalize_code(row.get("Позиция.Код"))
        if not levels:
            continue
        unit_path = f"{WORK_ROOT_PREFIX}/" + "/".join(levels)
        if department_code:
            unit_codes.setdefault(unit_path, set()).add(department_code)
        if title and position_code:
            line_codes.setdefault((unit_path, title), set()).add(position_code)

    _apply_unit_codes(session, unit_by_path, unit_codes, report)
    _apply_staffing_line_codes(session, lines_by_key, line_codes, report)
    session.flush()

    units_by_code = _units_by_code(units)
    lines_by_code = _lines_by_code(staffing_lines)
    for spec in _document_specs(documents_dir):
        report.documents_scanned += 1
        document = _upsert_document(session, spec, storage_dir, apply_changes, report)
        _link_document(session, document, spec, units_by_code, lines_by_code, report)
    session.flush()
    return report


def _apply_unit_codes(
    session: Session,
    unit_by_path: dict[str, OrgUnit],
    unit_codes: dict[str, set[str]],
    report: ImportReport,
) -> None:
    for unit_path, codes in sorted(unit_codes.items()):
        unit = unit_by_path.get(unit_path)
        if unit is None:
            report.units_unmatched.append(unit_path)
            continue
        if len(codes) > 1:
            report.unit_code_conflicts.append({"path": unit_path, "codes": sorted(codes)})
            continue
        code = next(iter(codes))
        report.units_matched += 1
        if unit.department_code != code:
            unit.department_code = code
            session.add(unit)
            report.units_updated += 1


def _apply_staffing_line_codes(
    session: Session,
    lines_by_key: dict[tuple[str, str], list[StaffingLine]],
    line_codes: dict[tuple[str, str], set[str]],
    report: ImportReport,
) -> None:
    for (unit_path, title), codes in sorted(line_codes.items()):
        lines = lines_by_key.get((unit_path, title), [])
        if not lines:
            report.staffing_lines_unmatched.append({"path": unit_path, "title": title, "codes": sorted(codes)})
            continue
        if len(codes) > 1:
            report.staffing_line_code_conflicts.append(
                {"path": unit_path, "title": title, "codes": sorted(codes), "line_ids": [line.id for line in lines]}
            )
            continue
        code = next(iter(codes))
        report.staffing_lines_matched += len(lines)
        for line in lines:
            if line.position_code != code:
                line.position_code = code
                session.add(line)
                report.staffing_lines_updated += 1


def _document_specs(documents_dir: Path) -> list[DocumentSpec]:
    specs: list[DocumentSpec] = []
    for source_path in sorted(documents_dir.rglob("*.docx")):
        if source_path.name.startswith("~$"):
            continue
        match = DOCUMENT_NAME_RE.match(source_path.name)
        if match is None:
            continue
        kind = match.group(1).upper()
        number = _code_key(match.group(2))
        raw_title = _normalize_text(Path(match.group(3)).stem.replace("_", " "))
        document_type = "job_instruction" if kind == "INS" else "unit_regulation"
        type_label = "Должностная инструкция" if kind == "INS" else "Положение о подразделении"
        specs.append(
            DocumentSpec(
                source_path=source_path,
                kind=kind,
                number=number,
                document_code=f"{kind}-{number}",
                document_type=document_type,
                title=f"{type_label}: {raw_title}"[:255],
            )
        )
    return specs


def _upsert_document(
    session: Session,
    spec: DocumentSpec,
    storage_dir: Path,
    apply_changes: bool,
    report: ImportReport,
) -> Document:
    content = spec.source_path.read_bytes()
    checksum = sha256(content).hexdigest()
    extracted_text, _ = _extract_initial_text(content, ".docx")
    source_file_path = str(_original_path(storage_dir, spec, checksum))
    extracted_text_path = (
        str(_text_snapshot_path(storage_dir, spec.document_code, checksum))
        if extracted_text
        else None
    )
    if apply_changes:
        _store_original(storage_dir, spec, checksum, content)
        if extracted_text:
            _store_text_snapshot(storage_dir, spec.document_code, checksum, extracted_text)

    document = session.scalar(select(Document).where(Document.document_code == spec.document_code))
    if document is None:
        document = Document(
            document_code=spec.document_code,
            document_type=spec.document_type,
            title=spec.title,
            version="grades-import",
            document_status="uploaded",
            source_file_path=source_file_path,
            extracted_text_path=extracted_text_path,
            content_text=extracted_text,
            ocr_quality_status="pending" if extracted_text else "requires_text",
            checksum=checksum,
            is_demo=False,
        )
        session.add(document)
        session.flush()
        report.documents_created += 1
        return document

    changed = False
    updates = {
        "document_type": spec.document_type,
        "title": spec.title,
        "version": "grades-import",
        "document_status": "uploaded",
        "source_file_path": source_file_path,
        "extracted_text_path": extracted_text_path,
        "content_text": extracted_text,
        "ocr_quality_status": "pending" if extracted_text else "requires_text",
        "checksum": checksum,
        "is_demo": False,
    }
    for field_name, value in updates.items():
        if getattr(document, field_name) != value:
            setattr(document, field_name, value)
            changed = True
    session.add(document)
    report.documents_updated += int(changed)
    report.documents_existing += int(not changed)
    return document


def _link_document(
    session: Session,
    document: Document,
    spec: DocumentSpec,
    units_by_code: dict[str, list[OrgUnit]],
    lines_by_code: dict[str, list[StaffingLine]],
    report: ImportReport,
) -> None:
    if spec.kind == "REG":
        target_type = "org_unit"
        targets = units_by_code.get(spec.number, [])
    else:
        target_type = "staffing_line"
        targets = lines_by_code.get(spec.number, [])
    if not targets:
        report.links_unmatched.append(
            {
                "document": spec.document_code,
                "type": spec.document_type,
                "expected_code": spec.number,
                "target_type": target_type,
                "source": str(spec.source_path),
            }
        )
        return

    for target in targets:
        exists = session.scalar(
            select(DocumentLink.id).where(
                DocumentLink.document_id == document.id,
                DocumentLink.target_type == target_type,
                DocumentLink.target_id == target.id,
            )
        )
        if exists is not None:
            report.links_existing += 1
            continue
        session.add(
            DocumentLink(
                document_id=document.id,
                target_type=target_type,
                target_id=target.id,
                link_status="imported",
                confirmed_at=datetime.now(UTC).replace(tzinfo=None),
                is_demo=False,
            )
        )
        report.links_created += 1


def _units_by_code(units: list[OrgUnit]) -> dict[str, list[OrgUnit]]:
    result: dict[str, list[OrgUnit]] = {}
    for unit in units:
        key = _code_key(unit.department_code)
        if key:
            result.setdefault(key, []).append(unit)
    return result


def _lines_by_code(lines: list[StaffingLine]) -> dict[str, list[StaffingLine]]:
    result: dict[str, list[StaffingLine]] = {}
    for line in lines:
        key = _code_key(line.position_code)
        if key:
            result.setdefault(key, []).append(line)
    return result


def _store_original(storage_dir: Path, spec: DocumentSpec, checksum: str, content: bytes) -> Path:
    path = _original_path(storage_dir, spec, checksum)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return path


def _original_path(storage_dir: Path, spec: DocumentSpec, checksum: str) -> Path:
    original_dir = storage_dir.resolve() / "originals"
    return original_dir / f"{_storage_token(spec.document_code)}__{checksum[:12]}{spec.source_path.suffix.lower()}"


def _text_snapshot_path(storage_dir: Path, document_code: str, digest: str) -> Path:
    text_dir = storage_dir.resolve() / "extracted"
    return text_dir / f"{_storage_token(document_code)}__{digest[:12]}.txt"


def _normalize_title(value: object) -> str:
    return _normalize_text(value).lower()


def _normalize_code(value: object) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        text = text.split(".", 1)[0]
    return text.strip()


def _code_key(value: object) -> str:
    code = _normalize_code(value)
    if not code:
        return ""
    if code.isdigit():
        return code.lstrip("0") or "0"
    return code


def _default_staffing_file() -> Path:
    grades_dir = _grades_dir()
    candidates = sorted(grades_dir.glob("Перечень*.xlsx"))
    if not candidates:
        return grades_dir / "Перечень позиций Пр по эк и фин.xlsx"
    return candidates[0]


def _grades_dir() -> Path:
    if GRADES_DIR.exists():
        return GRADES_DIR
    target_name = unicodedata.normalize("NFC", GRADES_DIR.name)
    for child in PROJECT_ROOT.iterdir():
        if child.is_dir() and unicodedata.normalize("NFC", child.name) == target_name:
            return child
    return GRADES_DIR


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Импорт кодов структуры и документов Грейдов.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Показать отчёт без записи в БД.")
    mode.add_argument("--apply", action="store_true", help="Записать изменения в БД и storage.")
    parser.add_argument("--staffing-file", type=Path, default=_default_staffing_file())
    parser.add_argument("--documents-dir", type=Path, default=_grades_dir() / "ИИ_Тестовая")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    staffing_file = args.staffing_file.resolve()
    documents_dir = args.documents_dir.resolve()
    if not staffing_file.exists():
        raise SystemExit(f"Файл структуры не найден: {staffing_file}")
    if not documents_dir.exists():
        raise SystemExit(f"Папка документов не найдена: {documents_dir}")

    settings = Settings.from_env()
    database = Database(settings.database_url)
    database.migrate()
    session = database.session_factory()
    try:
        report = import_grades_documents(
            session,
            staffing_file=staffing_file,
            documents_dir=documents_dir,
            storage_dir=settings.document_storage_dir or PROJECT_ROOT / "backend" / "data" / "documents",
            apply_changes=args.apply,
        )
        if args.apply:
            session.commit()
        else:
            session.rollback()
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
