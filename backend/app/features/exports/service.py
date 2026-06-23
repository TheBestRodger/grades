from __future__ import annotations

import csv
import io
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..campaigns.credentials import (
    credentials_to_xlsx,
    issue_credentials_for_new_wave_participants,
)
from ...models import (
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
from .constants import CAMPAIGN_EXPORT_COLUMNS, PROFILE_EXPORT_COLUMNS
from .errors import ExportOperationError
from .profile_template import fill_profile_template


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

    return fill_profile_template(template_path, _template_answers(profile))


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
