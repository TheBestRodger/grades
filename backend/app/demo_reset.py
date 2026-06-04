from __future__ import annotations

import json

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    CampaignWaveUnitSelection,
    Document,
    DocumentLink,
    Employee,
    EmployeeProfile,
    OrgUnit,
    ProfileDraft,
    ProfileReviewEvent,
    ProfileRevision,
    StaffingLine,
)
from .seed import seed_demo_data


class DemoResetError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def reset_demo_data(session: Session, actor: Employee, work_staffing_file) -> dict[str, object]:
    if actor.system_role != "hr":
        raise DemoResetError("Сброс данных доступен только HR.", 403)

    before = _scope_counts(session)
    demo_employee_ids = list(session.scalars(select(Employee.id).where(Employee.is_demo.is_(True))).all())
    demo_profile_ids = _demo_profile_ids(session)
    demo_revision_ids = _demo_revision_ids(session, demo_profile_ids)
    demo_participant_ids = _demo_participant_ids(session)
    demo_campaign_ids = list(session.scalars(select(Campaign.id).where(Campaign.is_demo.is_(True))).all())
    demo_wave_ids = list(
        session.scalars(select(CampaignWave.id).where(CampaignWave.is_demo.is_(True))).all()
    )
    demo_document_ids = list(session.scalars(select(Document.id).where(Document.is_demo.is_(True))).all())
    demo_assignment_ids = list(
        session.scalars(select(Assignment.id).where(Assignment.is_demo.is_(True))).all()
    )
    demo_staffing_line_ids = list(
        session.scalars(select(StaffingLine.id).where(StaffingLine.is_demo.is_(True))).all()
    )
    demo_org_unit_ids = list(session.scalars(select(OrgUnit.id).where(OrgUnit.is_demo.is_(True))).all())

    session.execute(update(AuditEvent).where(AuditEvent.actor_employee_id.in_(demo_employee_ids)).values(actor_employee_id=None))
    _delete_by_ids(session, ProfileReviewEvent, ProfileReviewEvent.revision_id, demo_revision_ids)
    _delete_by_ids(session, ProfileReviewEvent, ProfileReviewEvent.employee_profile_id, demo_profile_ids)
    _delete_by_ids(session, ProfileDraft, ProfileDraft.employee_profile_id, demo_profile_ids)
    _delete_by_ids(session, ProfileRevision, ProfileRevision.id, demo_revision_ids)
    _delete_by_ids(session, EmployeeProfile, EmployeeProfile.id, demo_profile_ids)
    _delete_by_ids(session, CampaignParticipant, CampaignParticipant.id, demo_participant_ids)
    _delete_by_ids(session, CampaignWaveUnitSelection, CampaignWaveUnitSelection.campaign_wave_id, demo_wave_ids)
    _delete_by_ids(session, CampaignWave, CampaignWave.id, demo_wave_ids)
    _delete_by_ids(session, Campaign, Campaign.id, demo_campaign_ids)
    _delete_by_ids(session, DocumentLink, DocumentLink.document_id, demo_document_ids)
    _delete_by_ids(session, DocumentLink, DocumentLink.confirmed_by_id, demo_employee_ids)
    _delete_by_ids(session, Document, Document.id, demo_document_ids)
    session.execute(
        update(Assignment)
        .where(Assignment.manager_assignment_id.in_(demo_assignment_ids), Assignment.is_demo.is_(False))
        .values(manager_assignment_id=None)
    )
    _delete_by_ids(session, Assignment, Assignment.id, demo_assignment_ids)
    _delete_by_ids(session, Employee, Employee.id, demo_employee_ids)
    _delete_by_ids(session, StaffingLine, StaffingLine.id, demo_staffing_line_ids)
    _delete_by_ids(session, OrgUnit, OrgUnit.id, demo_org_unit_ids)
    session.flush()

    seed_demo_data(session, work_staffing_file)
    after = _scope_counts(session)
    hr = session.scalar(select(Employee).where(Employee.email == "hr@profile.local", Employee.is_demo.is_(True)))
    session.add(
        AuditEvent(
            actor_employee_id=hr.id if hr else None,
            action="demo.reset_completed",
            entity_type="demo_scope",
            entity_id="demo",
            details_json=json.dumps(
                {
                    "scope": "demo",
                    "requested_by_employee_id": actor.id,
                    "before": before,
                    "after": after,
                    "work_unchanged": before["work"] == after["work"],
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return {
        "scope": "demo",
        "before": before,
        "after": after,
        "work_unchanged": before["work"] == after["work"],
    }


def _scope_counts(session: Session) -> dict[str, dict[str, int]]:
    return {
        "demo": {
            "org_units": _count(session, OrgUnit, True),
            "staffing_lines": _count(session, StaffingLine, True),
            "employees": _count(session, Employee, True),
            "assignments": _count(session, Assignment, True),
            "campaigns": _count(session, Campaign, True),
            "documents": _count(session, Document, True),
        },
        "work": {
            "org_units": _count(session, OrgUnit, False),
            "staffing_lines": _count(session, StaffingLine, False),
            "employees": _count(session, Employee, False),
            "assignments": _count(session, Assignment, False),
            "campaigns": _count(session, Campaign, False),
            "documents": _count(session, Document, False),
        },
    }


def _count(session: Session, model, is_demo: bool) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(model.is_demo.is_(is_demo))) or 0)


def _demo_participant_ids(session: Session) -> list[int]:
    return list(
        session.scalars(
            select(CampaignParticipant.id)
            .join(CampaignParticipant.campaign)
            .where(Campaign.is_demo.is_(True))
        ).all()
    )


def _demo_profile_ids(session: Session) -> list[int]:
    return list(
        session.scalars(
            select(EmployeeProfile.id)
            .join(EmployeeProfile.participant)
            .join(CampaignParticipant.campaign)
            .where(Campaign.is_demo.is_(True))
        ).all()
    )


def _demo_revision_ids(session: Session, demo_profile_ids: list[int]) -> list[int]:
    if not demo_profile_ids:
        return []
    return list(
        session.scalars(
            select(ProfileRevision.id).where(ProfileRevision.employee_profile_id.in_(demo_profile_ids))
        ).all()
    )


def _delete_by_ids(session: Session, model, column, ids: list[int]) -> None:
    if ids:
        session.execute(delete(model).where(column.in_(ids)))
