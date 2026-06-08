from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth_operations import generate_temporary_password, hash_password
from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    Employee,
    EmployeeProfile,
    ProfileRevision,
    StaffingLine,
)


PROFILE_EXPORT_COLUMNS = [
    "campaign_name",
    "wave_name",
    "employee_name",
    "email",
    "position_title",
    "unit_name",
    "workflow_status",
    "progress_percent",
    "revision_count",
    "latest_revision_no",
    "assistant_mode",
    "assistance_level",
    "position_purpose",
    "submitted_at",
]

CAMPAIGN_EXPORT_COLUMNS = [
    "campaign_name",
    "campaign_status",
    "wave_name",
    "wave_status",
    "participants_expected",
    "status_counts",
    "due_at",
    "created_at",
]

class ExportOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def issue_credentials_for_new_wave_participants(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    *,
    is_demo: bool,
) -> bytes:
    campaign = session.scalar(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
    )
    if campaign is None:
        raise ExportOperationError("Кампания не найдена.", 404)
    wave = session.scalar(
        select(CampaignWave).where(
            CampaignWave.id == wave_id,
            CampaignWave.campaign_id == campaign.id,
            CampaignWave.is_demo.is_(is_demo),
        )
    )
    if wave is None:
        raise ExportOperationError("Волна кампании не найдена.", 404)

    participants = session.scalars(
        select(CampaignParticipant)
        .join(CampaignParticipant.assignment)
        .join(Assignment.employee)
        .join(Assignment.staffing_line)
        .where(
            CampaignParticipant.campaign_id == campaign.id,
            CampaignParticipant.campaign_wave_id == wave.id,
            CampaignParticipant.participation_status == "included",
            CampaignParticipant.expected_to_submit.is_(True),
            Assignment.is_demo.is_(is_demo),
            Employee.is_active.is_(True),
            Employee.first_login_at.is_(None),
        )
        .options(
            selectinload(CampaignParticipant.assignment).selectinload(Assignment.employee),
            selectinload(CampaignParticipant.assignment).selectinload(Assignment.staffing_line),
        )
        .order_by(Employee.full_name, StaffingLine.title)
    ).all()
    if not participants:
        raise ExportOperationError("В выбранной волне нет новых участников для выдачи доступов.", 422)

    issued_passwords: dict[int, str] = {}
    rows: list[dict[str, object]] = []
    for participant in participants:
        assignment = participant.assignment
        employee = assignment.employee
        if not employee.username:
            employee.username = _unique_username(session, employee.full_name, employee.email, employee.id)
        password = issued_passwords.get(employee.id)
        if password is None:
            password = generate_temporary_password()
            employee.password_hash = hash_password(password)
            issued_passwords[employee.id] = password
        rows.append(
            {
                "full_name": employee.full_name,
                "email": employee.email,
                "username": employee.username,
                "password": password,
                "role": "Руководитель" if employee.system_role == "manager" else "Сотрудник",
                "position": assignment.staffing_line.title,
            }
        )

    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="auth.credentials_issued_for_new_participants",
            entity_type="campaign_wave",
            entity_id=str(wave.id),
            details_json=json.dumps(
                {
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "wave_name": wave.name,
                    "rows": len(rows),
                    "unique_users": len(issued_passwords),
                    "is_demo": is_demo,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return credentials_to_xlsx(rows)


def _base_username(full_name: str, email: str) -> str:
    email_prefix = email.split("@", 1)[0].strip().lower()
    base = email_prefix or "".join(part[0].lower() for part in full_name.split() if part) or "user"
    base = re.sub(r"[^a-z0-9_.-]+", ".", base)
    return base.strip(".") or "user"


def _unique_username(session: Session, full_name: str, email: str, employee_id: int) -> str:
    base = _base_username(full_name, email)
    existing = set(
        session.scalars(
            select(Employee.username).where(
                Employee.username.like(f"{base}%"),
                Employee.id != employee_id,
            )
        ).all()
    )
    username = base
    suffix = 2
    while username in existing:
        username = f"{base}{suffix}"
        suffix += 1
    return username


def credentials_to_xlsx(rows: list[dict[str, object]]) -> bytes:
    headers = ["ФИО", "Email", "Логин", "Пароль", "Роль", "Должность"]
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


def export_profiles(session: Session) -> list[dict[str, object]]:
    profiles = session.scalars(
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(
            Campaign.is_demo.is_(True),
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
        )
        .options(
            selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.campaign),
            selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.wave),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.employee),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(EmployeeProfile.revisions),
        )
        .order_by(EmployeeProfile.id)
    ).all()
    return [_profile_row(profile) for profile in profiles]


def export_campaigns(session: Session) -> list[dict[str, object]]:
    campaigns = session.scalars(
        select(Campaign)
        .where(Campaign.is_demo.is_(True))
        .options(
            selectinload(Campaign.waves),
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
        )
        .order_by(Campaign.id)
    ).all()
    rows: list[dict[str, object]] = []
    for campaign in campaigns:
        waves = campaign.waves or [
            CampaignWave(
                campaign_id=campaign.id,
                name="Без волны",
                status=campaign.status,
                created_by_id=campaign.created_by_id,
                is_demo=campaign.is_demo,
            )
        ]
        for wave in waves:
            participants = [
                participant
                for participant in campaign.participants
                if participant.campaign_wave_id == wave.id
                and participant.expected_to_submit
                and participant.participation_status == "included"
            ]
            status_counts = Counter(
                participant.profile.workflow_status if participant.profile else "not_started"
                for participant in participants
            )
            rows.append(
                {
                    "campaign_name": campaign.name,
                    "campaign_status": campaign.status,
                    "wave_name": wave.name,
                    "wave_status": wave.status,
                    "participants_expected": len(participants),
                    "status_counts": json.dumps(dict(status_counts), ensure_ascii=False),
                    "due_at": wave.due_at.isoformat() if wave.due_at else None,
                    "created_at": wave.created_at.isoformat() if wave.created_at else None,
                }
            )
    return rows


def rows_to_csv(rows: list[dict[str, object]], columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, delimiter=";", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_value(row.get(column)) for column in columns})
    return "\ufeff" + buffer.getvalue()


def export_owned_profile_template(
    session: Session,
    actor: Employee,
    profile_id: int,
    template_path: Path,
) -> bytes:
    profile = session.scalar(
        select(EmployeeProfile)
        .where(EmployeeProfile.id == profile_id)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .where(Assignment.employee_id == actor.id)
        .options(
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.employee),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(EmployeeProfile.draft),
            selectinload(EmployeeProfile.revisions),
        )
    )
    if profile is None:
        raise ExportOperationError("Профиль не найден или недоступен.", 404)
    if not template_path.exists():
        raise ExportOperationError("Excel-шаблон профиля не найден.", 500)

    return _fill_profile_template(template_path, _template_answers(profile))


def _profile_row(profile: EmployeeProfile) -> dict[str, object]:
    participant = profile.participant
    assignment = participant.assignment
    line = assignment.staffing_line
    latest = _latest_revision(profile)
    answers = json.loads(latest.answers_json) if latest else {}
    return {
        "campaign_name": participant.campaign.name,
        "wave_name": participant.wave.name if participant.wave else None,
        "employee_name": assignment.employee.full_name,
        "email": assignment.employee.email,
        "position_title": line.title,
        "unit_name": line.org_unit.name,
        "workflow_status": profile.workflow_status,
        "progress_percent": profile.progress_percent,
        "revision_count": len(profile.revisions),
        "latest_revision_no": latest.revision_no if latest else None,
        "assistant_mode": latest.assistant_mode if latest else None,
        "assistance_level": latest.assistance_level if latest else None,
        "position_purpose": answers.get("position_purpose") if latest else None,
        "submitted_at": latest.submitted_at.isoformat() if latest else None,
    }


def _latest_revision(profile: EmployeeProfile) -> ProfileRevision | None:
    return max(profile.revisions, key=lambda item: item.revision_no, default=None)


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(value).replace(".", ",")
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _template_answers(profile: EmployeeProfile) -> dict[str, str]:
    participant = profile.participant
    assignment = participant.assignment
    line = assignment.staffing_line
    latest = _latest_revision(profile)
    if latest is not None:
        answers = json.loads(latest.answers_json)
    elif profile.draft is not None:
        answers = json.loads(profile.draft.answers_json)
    else:
        answers = {}

    defaults = {
        "position_name": line.title,
        "org_structure": _visible_org_path(line.org_unit.path),
        "completion_date": "",
    }
    return {key: str(value) for key, value in {**defaults, **answers}.items()}


def _visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def _fill_profile_template(template_path: Path, answers: dict[str, str]) -> bytes:
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
