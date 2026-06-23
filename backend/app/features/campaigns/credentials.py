from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...features.auth.passwords import generate_temporary_password, hash_password
from ...infrastructure.xlsx.credentials import credentials_to_xlsx
from ...models import AuditEvent, Campaign, CampaignWave, Employee
from . import repository
from .errors import CampaignOperationError


def issue_credentials_for_new_wave_participants(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    *,
    is_demo: bool,
) -> bytes:
    campaign = repository.load_campaign(session, campaign_id, is_demo)
    if campaign is None:
        raise CampaignOperationError("Кампания не найдена.", 404)
    wave = repository.load_wave(session, campaign, wave_id)
    if wave is None:
        raise CampaignOperationError("Волна кампании не найдена.", 404)

    participants = repository.load_new_wave_participants(session, campaign, wave, is_demo)
    if not participants:
        raise CampaignOperationError("В выбранной волне нет новых участников для выдачи доступов.", 422)

    issued_passwords: dict[int, str] = {}
    rows: list[dict[str, object]] = []
    for participant in participants:
        assignment = participant.assignment
        employee = assignment.employee
        employee.username = employee.email.strip().lower()
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


def campaign_wave_for_credentials(
    session: Session,
    campaign_id: int,
    wave_id: int,
    *,
    is_demo: bool,
) -> tuple[Campaign, CampaignWave]:
    campaign = repository.load_campaign(session, campaign_id, is_demo)
    if campaign is None:
        raise CampaignOperationError("Кампания не найдена.", 404)
    wave = repository.load_wave(session, campaign, wave_id)
    if wave is None:
        raise CampaignOperationError("Волна кампании не найдена.", 404)
    return campaign, wave
