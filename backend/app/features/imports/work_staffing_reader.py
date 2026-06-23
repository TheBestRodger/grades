from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_staffing_rows(path: Path) -> list[dict[str, str | float | None]]:
    with ZipFile(path) as archive:
        shared_strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(_first_sheet_name(archive)))

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
    headers = [normalize_text(value) for value in rows[0]]
    result: list[dict[str, str | float | None]] = []
    for row in rows[1:]:
        if not any(normalize_text(value) for value in row):
            continue
        result.append(
            {
                header: row[index] if index < len(row) else None
                for index, header in enumerate(headers)
                if header
            }
        )
    return result


def collapsed_levels(values: list[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = normalize_text(value)
        if not text or (result and result[-1] == text):
            continue
        result.append(text)
    return result


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).replace("\xa0", " ").split())


def to_float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    text = normalize_text(value).replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _first_sheet_name(archive: ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook.find(".//a:sheets/a:sheet", NS)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets.")
    rel_id = first_sheet.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
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
