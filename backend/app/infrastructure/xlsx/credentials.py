from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


def credentials_to_xlsx(rows: list[dict[str, object]]) -> bytes:
    headers = ["ФИО", "Email", "Email для входа", "Пароль", "Роль", "Должность"]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Доступы"
    sheet.append(headers)

    header_fill = PatternFill("solid", fgColor="E2F0D9")
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill

    for row in rows:
        sheet.append(
            [
                str(row.get("full_name") or ""),
                str(row.get("email") or ""),
                str(row.get("username") or ""),
                str(row.get("password") or ""),
                str(row.get("role") or ""),
                str(row.get("position") or ""),
            ]
        )

    sheet.freeze_panes = "A2"
    for index, width in enumerate([36, 32, 24, 20, 18, 36], start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
