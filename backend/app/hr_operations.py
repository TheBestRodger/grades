from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth_operations import generate_temporary_password, hash_password
from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    CampaignWaveUnitSelection,
    Employee,
    EmployeeProfile,
    OrgUnit,
    StaffingLine,
)
from .organization import _unit_descendants
from .schemas import (
    BulkEmployeeCreate,
    CampaignAssignmentsUpdate,
    CampaignCreate,
    CampaignWaveCreate,
    WorkStaffingEmployeeCreate,
    WorkStaffingLineCreate,
)


class HrOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


WAVE_STATUS_DRAFT = "draft"
WAVE_STATUS_ACTIVE = "active"
WAVE_STATUS_EDITING = "editing"
WAVE_EDITABLE_STATUSES = {WAVE_STATUS_DRAFT, WAVE_STATUS_EDITING}


def _base_username(full_name: str, email: str) -> str:
    email_prefix = email.split("@", 1)[0].strip().lower()
    if email_prefix:
        base = email_prefix
    else:
        base = "".join(part[0].lower() for part in full_name.split() if part) or "user"
    base = re.sub(r"[^a-z0-9_.-]+", ".", base)
    return base.strip(".") or "user"


def _unique_username(session: Session, full_name: str, email: str) -> str:
    base = _base_username(full_name, email)
    existing = set(
        session.scalars(
            select(Employee.username).where(Employee.username.like(f"{base}%"))
        ).all()
    )
    username = base
    suffix = 2
    while username in existing:
        username = f"{base}{suffix}"
        suffix += 1
    return username


def _audit(
    session: Session,
    actor: Employee,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


def get_manager_options(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    assignments = session.scalars(
        select(Assignment)
        .join(Assignment.employee)
        .where(
            Assignment.is_demo.is_(is_demo),
            Employee.system_role.in_(["hr", "manager"]),
        )
        .options(
            selectinload(Assignment.employee),
            selectinload(Assignment.staffing_line).selectinload(StaffingLine.org_unit),
        )
        .order_by(Assignment.id)
    ).all()
    return [
        {
            "assignment_id": assignment.id,
            "employee_name": assignment.employee.full_name,
            "position_title": assignment.staffing_line.title,
            "unit_name": assignment.staffing_line.org_unit.name,
            "is_demo": assignment.is_demo,
        }
        for assignment in assignments
    ]


def add_employees(
    session: Session,
    actor: Employee,
    staffing_line_id: int,
    request: BulkEmployeeCreate,
    *,
    is_demo: bool = True,
) -> dict[str, object]:
    line = session.scalar(
        select(StaffingLine)
        .where(StaffingLine.id == staffing_line_id, StaffingLine.is_demo.is_(is_demo))
        .options(selectinload(StaffingLine.assignments))
    )
    if line is None:
        raise HrOperationError("Позиция не найдена.", 404)

    assigned_fte = sum(assignment.fte for assignment in line.assignments)
    requested_fte = sum(employee.fte for employee in request.employees)
    remaining_fte = round(line.approved_fte - assigned_fte, 2)
    if requested_fte > remaining_fte + 1e-9:
        raise HrOperationError(
            f"Недостаточно свободных ставок: доступно {remaining_fte}, запрошено {requested_fte}.",
            409,
        )

    emails = [employee.email for employee in request.employees]
    if len(emails) != len(set(emails)):
        raise HrOperationError("В списке добавления есть повторяющиеся email.")
    existing_email = session.scalar(select(Employee.email).where(Employee.email.in_(emails)))
    if existing_email is not None:
        raise HrOperationError(f"Сотрудник с email {existing_email} уже существует.", 409)

    missing_manager = [
        employee.full_name
        for employee in request.employees
        if employee.system_role == "employee" and employee.manager_assignment_id is None
    ]
    if missing_manager:
        raise HrOperationError("Для сотрудника нужно выбрать непосредственного руководителя.")

    manager_ids = {
        employee.manager_assignment_id
        for employee in request.employees
        if employee.manager_assignment_id is not None
    }
    managers = session.scalars(
        select(Assignment).where(
            Assignment.id.in_(manager_ids),
            Assignment.is_demo.is_(is_demo),
        )
    ).all() if manager_ids else []
    managers_by_id = {manager.id: manager for manager in managers}
    if set(managers_by_id) != manager_ids:
        raise HrOperationError("Выбранный руководитель не найден в структуре.")

    added: list[dict[str, object]] = []
    for item in request.employees:
        username = _unique_username(session, item.full_name, item.email)
        temporary_password = generate_temporary_password()
        employee = Employee(
            full_name=item.full_name,
            email=item.email,
            username=username,
            password_hash=hash_password(temporary_password),
            system_role=item.system_role,
            is_demo=is_demo,
        )
        session.add(employee)
        session.flush()
        assignment = Assignment(
            employee=employee,
            staffing_line=line,
            manager_assignment_id=managers_by_id[item.manager_assignment_id].id
            if item.manager_assignment_id is not None
            else None,
            fte=item.fte,
            is_demo=is_demo,
        )
        session.add(assignment)
        session.flush()
        added.append(
            {
                "employee_id": employee.id,
                "assignment_id": assignment.id,
                "full_name": employee.full_name,
                "email": employee.email,
                "username": employee.username,
                "password": temporary_password,
                "fte": assignment.fte,
                "system_role": employee.system_role,
                "manager_assignment_id": assignment.manager_assignment_id,
            }
        )

    audit_added = [
        {key: value for key, value in employee.items() if key != "password"}
        for employee in added
    ]
    _audit(
        session,
        actor,
        "employees.bulk_added",
        "staffing_line",
        line.id,
        {
            "scope": "demo" if is_demo else "work",
            "staffing_title": line.title,
            "count": len(added),
            "employees": audit_added,
        },
    )
    return {
        "staffing_line_id": line.id,
        "staffing_title": line.title,
        "added": added,
        "remaining_fte": round(remaining_fte - requested_fte, 2),
    }


def create_work_staffing_line(
    session: Session,
    actor: Employee,
    org_unit_id: int,
    request: WorkStaffingLineCreate,
) -> dict[str, object]:
    unit = session.scalar(
        select(OrgUnit).where(
            OrgUnit.id == org_unit_id,
            OrgUnit.is_demo.is_(False),
            OrgUnit.is_active.is_(True),
        )
    )
    if unit is None:
        raise HrOperationError("Рабочее подразделение не найдено.", 404)

    duplicate = session.scalar(
        select(StaffingLine).where(
            StaffingLine.org_unit_id == unit.id,
            StaffingLine.is_demo.is_(False),
            StaffingLine.is_active.is_(True),
            StaffingLine.title == request.title,
        )
    )
    if duplicate is not None:
        raise HrOperationError("В подразделении уже есть активная штатная строка с таким названием.", 409)

    requested_fte = round(sum(employee.fte for employee in request.employees), 4)
    if requested_fte > request.approved_fte + 1e-9:
        raise HrOperationError(
            f"Недостаточно ставок в новой строке: доступно {request.approved_fte}, запрошено {requested_fte}.",
            409,
        )
    _ensure_unique_new_emails(session, [employee.email for employee in request.employees])
    manager_ids = {
        employee.manager_assignment_id
        for employee in request.employees
        if employee.manager_assignment_id is not None
    }
    managers = _load_manager_assignments(session, manager_ids, is_demo=False)

    line = StaffingLine(
        org_unit=unit,
        title=request.title,
        approved_fte=round(request.approved_fte, 4),
        reported_occupied_fte=0,
        is_demo=False,
        is_active=True,
    )
    session.add(line)
    session.flush()

    added = [
        _create_work_assignment(session, line, employee, managers.get(employee.manager_assignment_id))
        for employee in request.employees
    ]
    _audit(
        session,
        actor,
        "staffing_line.work_created",
        "staffing_line",
        line.id,
        {
            "scope": "work",
            "org_unit_id": unit.id,
            "org_unit_name": unit.name,
            "staffing_title": line.title,
            "approved_fte": line.approved_fte,
            "employees_count": len(added),
            "employee_assignment_ids": [item["assignment_id"] for item in added],
        },
    )
    session.flush()
    return {
        "scope": "work",
        "org_unit_id": unit.id,
        "org_unit_name": unit.name,
        "staffing_line_id": line.id,
        "staffing_title": line.title,
        "approved_fte": line.approved_fte,
        "added": added,
        "remaining_fte": round(line.approved_fte - requested_fte, 2),
    }


def _ensure_unique_new_emails(session: Session, emails: list[str]) -> None:
    if len(emails) != len(set(emails)):
        raise HrOperationError("В списке добавления есть повторяющиеся email.")
    if not emails:
        return
    existing_email = session.scalar(select(Employee.email).where(Employee.email.in_(emails)))
    if existing_email is not None:
        raise HrOperationError(f"Сотрудник с email {existing_email} уже существует.", 409)


def _load_manager_assignments(
    session: Session,
    manager_ids: set[int],
    *,
    is_demo: bool,
) -> dict[int | None, Assignment]:
    if not manager_ids:
        return {}
    managers = session.scalars(
        select(Assignment).where(
            Assignment.id.in_(manager_ids),
            Assignment.is_demo.is_(is_demo),
        )
    ).all()
    if {manager.id for manager in managers} != manager_ids:
        raise HrOperationError("Выбранный руководитель не найден в рабочей структуре.")
    return {manager.id: manager for manager in managers}


def _create_work_assignment(
    session: Session,
    line: StaffingLine,
    item: WorkStaffingEmployeeCreate,
    manager: Assignment | None,
) -> dict[str, object]:
    employee = Employee(
        full_name=item.full_name,
        email=item.email,
        system_role=item.system_role,
        is_demo=False,
    )
    session.add(employee)
    session.flush()
    assignment = Assignment(
        employee=employee,
        staffing_line=line,
        manager_assignment_id=manager.id if manager else None,
        fte=item.fte,
        assignment_role="primary",
        is_demo=False,
    )
    session.add(assignment)
    session.flush()
    return {
        "employee_id": employee.id,
        "assignment_id": assignment.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "fte": assignment.fte,
        "system_role": employee.system_role,
        "manager_assignment_id": assignment.manager_assignment_id,
    }


def _participants_for_wave(campaign: Campaign, wave: CampaignWave | None) -> list[CampaignParticipant]:
    return [
        participant
        for participant in campaign.participants
        if participant.campaign_wave_id == (wave.id if wave else None)
    ]


def _included_participants(participants: list[CampaignParticipant]) -> list[CampaignParticipant]:
    return [participant for participant in participants if participant.expected_to_submit]


def _status_counts(participants: list[CampaignParticipant]) -> dict[str, int]:
    status_counts: dict[str, int] = {}
    for participant in _included_participants(participants):
        status = participant.profile.workflow_status if participant.profile else "not_started"
        status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts


def _wave_status_label(status: str) -> str:
    return {
        WAVE_STATUS_DRAFT: "Черновик",
        WAVE_STATUS_ACTIVE: "Запущена",
        WAVE_STATUS_EDITING: "Редакция",
    }.get(status, status)


def _ensure_wave_is_editable(wave: CampaignWave) -> None:
    if wave.status not in WAVE_EDITABLE_STATUSES:
        raise HrOperationError(
            "Волна запущена. Чтобы изменить участников, сначала возьмите волну в редакцию.",
            409,
        )


def _selected_unit_ids(wave: CampaignWave) -> list[int]:
    return sorted(
        selection.org_unit_id
        for selection in wave.unit_selections
        if selection.inclusion_status == "included"
    )


def _wave_scope_metrics(session: Session, wave: CampaignWave) -> dict[str, object]:
    selected_unit_ids = _selected_unit_ids(wave)
    if not selected_unit_ids:
        return {
            "selected_org_unit_ids": [],
            "selected_units_count": 0,
            "selected_staffing_lines": 0,
            "selected_approved_fte": 0.0,
        }
    lines = session.scalars(
        select(StaffingLine).where(StaffingLine.org_unit_id.in_(selected_unit_ids))
    ).all()
    return {
        "selected_org_unit_ids": selected_unit_ids,
        "selected_units_count": len(selected_unit_ids),
        "selected_staffing_lines": len(lines),
        "selected_approved_fte": round(sum(line.approved_fte for line in lines), 2),
    }


def _wave_summary(session: Session, campaign: Campaign, wave: CampaignWave) -> dict[str, object]:
    participants = _participants_for_wave(campaign, wave)
    included = _included_participants(participants)
    return {
        "id": wave.id,
        "campaign_id": campaign.id,
        "name": wave.name,
        "status": wave.status,
        "status_label": _wave_status_label(wave.status),
        "can_edit": wave.status in WAVE_EDITABLE_STATUSES,
        "can_launch": wave.status in WAVE_EDITABLE_STATUSES,
        "due_at": wave.due_at.isoformat() if wave.due_at else None,
        "participants_expected": len(included),
        "participant_assignment_ids": [participant.assignment_id for participant in included],
        "status_counts": _status_counts(participants),
        "created_at": wave.created_at.isoformat() if wave.created_at else None,
        **_wave_scope_metrics(session, wave),
    }


def _default_wave(session: Session, actor: Employee, campaign: Campaign) -> CampaignWave:
    active_waves = [wave for wave in campaign.waves if wave.status == "active"]
    if active_waves:
        return active_waves[-1]
    if campaign.waves:
        return campaign.waves[-1]
    wave = CampaignWave(
        campaign=campaign,
        name="Волна 1",
        status=WAVE_STATUS_DRAFT,
        due_at=campaign.due_at,
        created_by_id=actor.id,
        is_demo=campaign.is_demo,
    )
    session.add(wave)
    session.flush()
    session.expire(campaign, ["waves", "participants"])
    return wave


def _resolve_wave(
    session: Session,
    actor: Employee,
    campaign: Campaign,
    wave_id: int | None,
) -> CampaignWave:
    if wave_id is None:
        return _default_wave(session, actor, campaign)
    wave = session.scalar(
        select(CampaignWave).where(
            CampaignWave.id == wave_id,
            CampaignWave.campaign_id == campaign.id,
            CampaignWave.is_demo.is_(campaign.is_demo),
        )
    )
    if wave is None:
        raise HrOperationError("Волна кампании не найдена.", 404)
    return wave


def campaign_summary(session: Session, campaign: Campaign) -> dict[str, object]:
    waves = [_wave_summary(session, campaign, wave) for wave in campaign.waves]
    active_wave = next((wave for wave in reversed(waves) if wave["status"] == "active"), None)
    if active_wave is None and waves:
        active_wave = waves[-1]
    all_included = _included_participants(list(campaign.participants))
    return {
        "id": campaign.id,
        "scope": "demo" if campaign.is_demo else "work",
        "is_demo": campaign.is_demo,
        "name": campaign.name,
        "status": campaign.status,
        "due_at": campaign.due_at.isoformat() if campaign.due_at else None,
        "participants_expected": active_wave["participants_expected"] if active_wave else 0,
        "participant_assignment_ids": active_wave["participant_assignment_ids"] if active_wave else [],
        "status_counts": active_wave["status_counts"] if active_wave else {},
        "selected_org_unit_ids": active_wave["selected_org_unit_ids"] if active_wave else [],
        "selected_units_count": active_wave["selected_units_count"] if active_wave else 0,
        "selected_staffing_lines": active_wave["selected_staffing_lines"] if active_wave else 0,
        "selected_approved_fte": active_wave["selected_approved_fte"] if active_wave else 0.0,
        "total_participants_expected": len(all_included),
        "active_wave_id": active_wave["id"] if active_wave else None,
        "active_wave_name": active_wave["name"] if active_wave else None,
        "waves": waves,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


def get_campaigns(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    campaigns = session.scalars(
        select(Campaign)
        .where(Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
        )
        .order_by(Campaign.id.desc())
    ).all()
    return [campaign_summary(session, campaign) for campaign in campaigns]


def create_campaign(
    session: Session,
    actor: Employee,
    request: CampaignCreate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = Campaign(
        name=request.name,
        status="active",
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(campaign)
    session.flush()
    wave = CampaignWave(
        campaign=campaign,
        name="Волна 1",
        status=WAVE_STATUS_DRAFT,
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(wave)
    session.flush()
    session.expire(campaign, ["waves", "participants"])
    _audit(
        session,
        actor,
        "campaign.created",
        "campaign",
        campaign.id,
        {
            "name": campaign.name,
            "due_at": request.due_at.isoformat() if request.due_at else None,
            "initial_wave_id": wave.id,
            "initial_wave_name": wave.name,
            "scope": "demo" if is_demo else "work",
        },
    )
    return campaign_summary(session, campaign)


def create_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    request: CampaignWaveCreate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
        )
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    wave = CampaignWave(
        campaign=campaign,
        name=request.name,
        status=WAVE_STATUS_DRAFT,
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(wave)
    session.flush()
    _audit(
        session,
        actor,
        "campaign.wave_created",
        "campaign_wave",
        wave.id,
        {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_name": wave.name,
            "due_at": request.due_at.isoformat() if request.due_at else None,
            "scope": "demo" if is_demo else "work",
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"new_wave_id": wave.id, "new_wave_name": wave.name})
    return result


def launch_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
        )
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    wave = _resolve_wave(session, actor, campaign, wave_id)
    if wave.status not in WAVE_EDITABLE_STATUSES:
        raise HrOperationError("Волна уже запущена.", 409)

    participants = _included_participants(_participants_for_wave(campaign, wave))
    selected_unit_ids = _selected_unit_ids(wave)
    if not participants:
        raise HrOperationError("Для запуска волны выберите минимум одного участника.", 422)
    if not is_demo and not selected_unit_ids:
        raise HrOperationError("Для запуска волны выберите минимум одно подразделение.", 422)

    previous_status = wave.status
    wave.status = WAVE_STATUS_ACTIVE
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    _audit(
        session,
        actor,
        "campaign.wave_launched",
        "campaign_wave",
        wave.id,
        {
            "scope": "demo" if is_demo else "work",
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
            "previous_status": previous_status,
            "participants_expected": len(participants),
            "selected_units_count": len(selected_unit_ids),
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"launched_wave_id": wave.id, "launched_wave_name": wave.name})
    return result


def edit_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
        )
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    wave = _resolve_wave(session, actor, campaign, wave_id)
    if wave.status == WAVE_STATUS_DRAFT:
        raise HrOperationError("Волна уже находится в черновике и доступна для редактирования.", 409)
    if wave.status == WAVE_STATUS_EDITING:
        raise HrOperationError("Волна уже находится в редакции.", 409)
    if wave.status != WAVE_STATUS_ACTIVE:
        raise HrOperationError("Волну в текущем статусе нельзя взять в редакцию.", 409)

    wave.status = WAVE_STATUS_EDITING
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    _audit(
        session,
        actor,
        "campaign.wave_editing_started",
        "campaign_wave",
        wave.id,
        {
            "scope": "demo" if is_demo else "work",
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"editing_wave_id": wave.id, "editing_wave_name": wave.name})
    return result


def _set_work_scope(
    session: Session,
    actor: Employee,
    wave: CampaignWave,
    unit_ids: set[int],
    included: bool,
) -> int:
    existing = {selection.org_unit_id: selection for selection in wave.unit_selections}
    next_status = "included" if included else "excluded"
    changed = 0
    for unit_id in unit_ids:
        selection = existing.get(unit_id)
        if selection is None:
            selection = CampaignWaveUnitSelection(
                wave=wave,
                org_unit_id=unit_id,
                inclusion_status=next_status,
                selected_by_id=actor.id,
                is_demo=False,
            )
            session.add(selection)
            changed += 1
            continue
        if selection.inclusion_status != next_status:
            selection.inclusion_status = next_status
            selection.selected_by_id = actor.id
            changed += 1
    return changed


def _set_participation(
    session: Session,
    actor: Employee,
    campaign: Campaign,
    wave: CampaignWave,
    assignments: list[Assignment],
    included: bool,
) -> int:
    existing = {participant.assignment_id: participant for participant in campaign.participants}
    changed = 0
    for assignment in assignments:
        participant = existing.get(assignment.id)
        if participant is None:
            if not included:
                continue
            participant = CampaignParticipant(
                campaign=campaign,
                wave=wave,
                assignment_id=assignment.id,
                participation_status="included",
                expected_to_submit=True,
                included_by_id=actor.id,
            )
            participant.profile = EmployeeProfile()
            session.add(participant)
            changed += 1
            continue
        if participant.campaign_wave_id != wave.id:
            continue
        next_status = "included" if included else "excluded"
        if (
            participant.expected_to_submit == included
            and participant.participation_status == next_status
        ):
            continue
        participant.expected_to_submit = included
        participant.participation_status = next_status
        changed += 1
    return changed


def include_unit_in_campaign(
    session: Session,
    actor: Employee,
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.participants),
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
        )
    )
    unit = session.scalar(
        select(OrgUnit).where(OrgUnit.id == org_unit_id, OrgUnit.is_demo.is_(is_demo))
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    if unit is None:
        raise HrOperationError("Ветка структуры не найдена.", 404)
    wave = _resolve_wave(session, actor, campaign, wave_id)
    _ensure_wave_is_editable(wave)

    units = session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()
    unit_ids = _unit_descendants(units, {unit.id})
    if not is_demo:
        changed_units = _set_work_scope(session, actor, wave, unit_ids, included=True)
        assignments = session.scalars(
            select(Assignment).where(
                Assignment.is_demo.is_(False),
                Assignment.staffing_line_id.in_(
                    select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
                ),
            )
        ).all()
        created = _set_participation(session, actor, campaign, wave, assignments, included=True)
        session.flush()
        session.expire(campaign, ["participants", "waves"])
        _audit(
            session,
            actor,
            "campaign.branch_included",
            "campaign",
            campaign.id,
            {
                "scope": "work",
                "org_unit_id": unit.id,
                "org_unit_name": unit.name,
                "wave_id": wave.id,
                "wave_name": wave.name,
                "selected_units_changed": changed_units,
                "new_participants": created,
            },
        )
        result = campaign_summary(session, campaign)
        result.update(
            {
                "included_unit_name": unit.name,
                "included_wave_id": wave.id,
                "included_wave_name": wave.name,
                "new_participants": created,
                "selected_units_changed": changed_units,
            }
        )
        return result

    assignments = session.scalars(
        select(Assignment).where(
            Assignment.is_demo.is_(True),
            Assignment.staffing_line_id.in_(
                select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
            ),
        )
    ).all()
    created = _set_participation(session, actor, campaign, wave, assignments, included=True)
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    _audit(
        session,
        actor,
        "campaign.branch_included",
        "campaign",
        campaign.id,
        {
            "org_unit_id": unit.id,
            "org_unit_name": unit.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
            "new_participants": created,
            "scope": "demo",
        },
    )
    result = campaign_summary(session, campaign)
    result.update(
        {
            "included_unit_name": unit.name,
            "included_wave_id": wave.id,
            "included_wave_name": wave.name,
            "new_participants": created,
        }
    )
    return result


def exclude_unit_from_campaign(
    session: Session,
    actor: Employee,
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
        )
    )
    unit = session.scalar(
        select(OrgUnit).where(OrgUnit.id == org_unit_id, OrgUnit.is_demo.is_(is_demo))
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    if unit is None:
        raise HrOperationError("Ветка структуры не найдена.", 404)
    wave = _resolve_wave(session, actor, campaign, wave_id)
    _ensure_wave_is_editable(wave)

    units = session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()
    unit_ids = _unit_descendants(units, {unit.id})
    if not is_demo:
        changed_units = _set_work_scope(session, actor, wave, unit_ids, included=False)
        assignments = session.scalars(
            select(Assignment).where(
                Assignment.is_demo.is_(False),
                Assignment.staffing_line_id.in_(
                    select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
                ),
            )
        ).all()
        excluded = _set_participation(session, actor, campaign, wave, assignments, included=False)
        session.flush()
        session.expire(campaign, ["participants", "waves"])
        _audit(
            session,
            actor,
            "campaign.branch_excluded",
            "campaign",
            campaign.id,
            {
                "scope": "work",
                "org_unit_id": unit.id,
                "org_unit_name": unit.name,
                "wave_id": wave.id,
                "wave_name": wave.name,
                "selected_units_changed": changed_units,
                "excluded_participants": excluded,
            },
        )
        result = campaign_summary(session, campaign)
        result.update(
            {
                "excluded_unit_name": unit.name,
                "excluded_wave_id": wave.id,
                "excluded_wave_name": wave.name,
                "excluded_participants": excluded,
                "selected_units_changed": changed_units,
            }
        )
        return result

    assignment_ids = set(
        session.scalars(
            select(Assignment.id).where(
                Assignment.is_demo.is_(True),
                Assignment.staffing_line_id.in_(
                    select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
                ),
            )
        ).all()
    )
    excluded = 0
    for participant in campaign.participants:
        if participant.campaign_wave_id != wave.id:
            continue
        if participant.assignment_id not in assignment_ids:
            continue
        if not participant.expected_to_submit and participant.participation_status == "excluded":
            continue
        participant.expected_to_submit = False
        participant.participation_status = "excluded"
        excluded += 1

    session.flush()
    session.expire(campaign, ["participants", "waves"])
    _audit(
        session,
        actor,
        "campaign.branch_excluded",
        "campaign",
        campaign.id,
        {
            "org_unit_id": unit.id,
            "org_unit_name": unit.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
            "excluded_participants": excluded,
            "scope": "demo",
        },
    )
    result = campaign_summary(session, campaign)
    result.update(
        {
            "excluded_unit_name": unit.name,
            "excluded_wave_id": wave.id,
            "excluded_wave_name": wave.name,
            "excluded_participants": excluded,
        }
    )
    return result


def set_campaign_assignments(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    request: CampaignAssignmentsUpdate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
        )
    )
    if campaign is None:
        raise HrOperationError("Кампания не найдена.", 404)
    wave = _resolve_wave(session, actor, campaign, wave_id)
    _ensure_wave_is_editable(wave)
    assignments = session.scalars(
        select(Assignment).where(
            Assignment.id.in_(request.assignment_ids),
            Assignment.is_demo.is_(is_demo),
        )
    ).all()
    if {assignment.id for assignment in assignments} != set(request.assignment_ids):
        raise HrOperationError("Одно или несколько назначений не найдены в выбранном контуре.", 404)
    included = request.action == "include"
    changed = _set_participation(session, actor, campaign, wave, assignments, included)
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    action = "campaign.assignments_included" if included else "campaign.assignments_excluded"
    _audit(
        session,
        actor,
        action,
        "campaign",
        campaign.id,
        {
            "scope": "demo" if is_demo else "work",
            "wave_id": wave.id,
            "wave_name": wave.name,
            "assignment_ids": request.assignment_ids,
            "changed_participants": changed,
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"changed_participants": changed, "participant_action": request.action})
    return result


def recent_audit_events(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    events = session.scalars(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)
    ).all()
    results: list[dict[str, object]] = []
    for event in events:
        details = json.loads(event.details_json) if event.details_json else {}
        scope = details.get("scope", "demo")
        if scope != ("demo" if is_demo else "work"):
            continue
        results.append({
            "id": event.id,
            "action": event.action,
            "entity_type": event.entity_type,
            "details": details,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        })
        if len(results) == 12:
            break
    return results
