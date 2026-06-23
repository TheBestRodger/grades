from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile


class DocumentFileError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def extract_initial_text(content: bytes, suffix: str) -> tuple[str | None, str]:
    if suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise DocumentFileError("Текстовый файл должен быть сохранён в UTF-8.") from exc
        return (text or None), "utf8_text"
    if suffix == ".docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                root = ET.fromstring(archive.read("word/document.xml"))
        except (BadZipFile, KeyError, ET.ParseError) as exc:
            raise DocumentFileError("Не удалось прочитать DOCX документ.") from exc
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        text = "\n".join(
            " ".join(fragment.text or "" for fragment in paragraph.findall(".//w:t", namespace)).strip()
            for paragraph in root.findall(".//w:p", namespace)
        ).strip()
        return (text or None), "docx_text"
    return None, "manual_ocr_required"


def storage_token(document_code: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", document_code).strip("._")
    return token[:60] or "document"


def store_text_snapshot(storage_dir: Path, document_code: str, digest: str, text: str) -> Path:
    text_dir = storage_dir.resolve() / "extracted"
    text_dir.mkdir(parents=True, exist_ok=True)
    path = text_dir / f"{storage_token(document_code)}__{digest[:12]}.txt"
    if not path.exists():
        path.write_text(text, encoding="utf-8")
    return path


_extract_initial_text = extract_initial_text
_storage_token = storage_token
_store_text_snapshot = store_text_snapshot
