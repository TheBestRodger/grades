from __future__ import annotations

import csv
from io import BytesIO, StringIO
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from .work_employee_errors import WorkEmployeeImportError


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_rows(filename: str, content: bytes) -> list[dict[str, object]]:
    if filename.lower().endswith(".xlsx"):
        return _read_xlsx_rows(content)
    if filename.lower().endswith(".csv"):
        return _read_csv_rows(content)
    raise WorkEmployeeImportError("Поддерживаются только файлы CSV и XLSX.")


def _read_csv_rows(content: bytes) -> list[dict[str, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise WorkEmployeeImportError("CSV должен быть в кодировке UTF-8.") from exc
    try:
        delimiter = csv.Sniffer().sniff(text[:2048], delimiters=";,").delimiter
    except csv.Error:
        delimiter = ";"
    return [dict(row) for row in csv.DictReader(StringIO(text), delimiter=delimiter)]


def _read_xlsx_rows(content: bytes) -> list[dict[str, object]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            shared_strings = _shared_strings(archive)
            root = ET.fromstring(archive.read(_first_sheet_name(archive)))
    except (BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        raise WorkEmployeeImportError("Не удалось прочитать XLSX-файл.") from exc
    values: list[list[str]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        row_values: list[str] = []
        for cell in row.findall("a:c", NS):
            index = _column_index(cell.attrib.get("r", ""))
            while len(row_values) < index:
                row_values.append("")
            row_values.append(_cell_value(cell, shared_strings))
        values.append(row_values)
    if not values:
        return []
    headers = values[0]
    return [
        {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        for row in values[1:]
    ]


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
    return [
        "".join(text.text or "" for text in item.findall(".//a:t", NS))
        for item in root.findall("a:si", NS)
    ]


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", NS))
    value = cell.find("a:v", NS)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter.upper()) - ord("A") + 1
    return max(result - 1, 0)
