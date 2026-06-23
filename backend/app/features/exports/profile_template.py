from __future__ import annotations

import io
import json
from pathlib import Path

from openpyxl import load_workbook


def fill_profile_template(template_path: Path, answers: dict[str, str]) -> bytes:
    workbook = load_workbook(template_path)
    worksheet = (
        workbook["Профиль должности"]
        if "Профиль должности" in workbook.sheetnames
        else workbook.active
    )
    _write_profile_cells(worksheet, answers)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _write_profile_cells(worksheet, answers: dict[str, str]) -> None:
    cell_values: dict[str, str] = {
        "C11": answers.get("position_name", ""),
        "C12": answers.get("org_structure", ""),
        "C13": answers.get("administrative_manager", ""),
        "C14": answers.get("functional_manager", ""),
        "C15": answers.get("direct_admin_reports", ""),
        "C16": answers.get("total_reports", ""),
        "C17": answers.get("functional_reports", ""),
        "C18": answers.get("completion_date", ""),
        "B24": answers.get("position_purpose", ""),
        "B43": answers.get("income_responsibility", ""),
        "C46": answers.get("expense_budget_type", ""),
        "C47": answers.get("expense_budget_volume", ""),
        "C48": answers.get("expense_budget_management", ""),
        "B62": answers.get("complex_task_example", ""),
        "B85": answers.get("government_interactions", ""),
        "B91": answers.get("independent_decisions", ""),
        "B95": answers.get("approval_decisions", ""),
        "C108": answers.get("specialization", ""),
        "C109": answers.get("certification", ""),
        "C112": answers.get("legal_knowledge", ""),
        "C113": answers.get("methods_knowledge", ""),
        "C114": answers.get("technology_knowledge", ""),
        "C115": answers.get("domain_context_knowledge", ""),
        "B124": answers.get("comments", ""),
    }

    for row_index, row in enumerate(_table_rows(answers.get("duties_results", ""), 8, 2), start=31):
        cell_values[f"B{row_index}"] = row[0]
        cell_values[f"C{row_index}"] = row[1]

    for row_index, row in enumerate(_table_rows(answers.get("external_interactions", ""), 5, 3), start=69):
        cell_values[f"B{row_index}"] = row[0]
        cell_values[f"C{row_index}"] = row[1]
        cell_values[f"D{row_index}"] = row[2]

    for row_index, row in enumerate(_table_rows(answers.get("internal_interactions", ""), 6, 3), start=77):
        cell_values[f"B{row_index}"] = row[0]
        cell_values[f"C{row_index}"] = row[1]
        cell_values[f"D{row_index}"] = row[2]

    experience = _table_rows(answers.get("experience_requirements", ""), 2, 3)
    if experience:
        cell_values["C119"] = experience[0][1]
        cell_values["D119"] = experience[0][2]
    if len(experience) > 1:
        cell_values["C120"] = experience[1][1]
        cell_values["D120"] = experience[1][2]

    task_choice_rows = {
        "Стандартные": "A55",
        "Типовые с вариациями": "A56",
        "Сложные / нестандартные": "A57",
        "Уникальные / пионерские": "A58",
    }
    selected_task = answers.get("task_typicality", "")
    for label, cell in task_choice_rows.items():
        cell_values[cell] = "X" if label == selected_task else ""

    education_rows = {
        "Среднее общее": "A101",
        "Среднее специальное / среднее профессиональное": "A102",
        "Неполное высшее": "A103",
        "Высшее (бакалавр / специалист / магистр)": "A104",
        "MBA": "A105",
        "Учёная степень (кандидат / доктор наук)": "A106",
    }
    selected_education = answers.get("education", "")
    for label, cell in education_rows.items():
        cell_values[cell] = "☑" if label == selected_education else "☐"

    for cell_ref, value in cell_values.items():
        _set_cell_value(worksheet, cell_ref, value)


def _table_rows(raw_value: str, limit: int, width: int) -> list[list[str]]:
    try:
        parsed = json.loads(raw_value) if raw_value else []
    except json.JSONDecodeError:
        parsed = []
    rows: list[list[str]] = []
    if isinstance(parsed, list):
        for item in parsed[:limit]:
            if isinstance(item, list):
                rows.append(
                    [
                        str(item[index]).strip() if index < len(item) and item[index] is not None else ""
                        for index in range(width)
                    ]
                )
    while len(rows) < limit:
        rows.append(["" for _ in range(width)])
    return rows


def _set_cell_value(worksheet, cell_ref: str, value: str) -> None:
    target = cell_ref
    for merged_range in worksheet.merged_cells.ranges:
        if cell_ref in merged_range:
            target = merged_range.start_cell.coordinate
            break
    worksheet[target] = value or ""

