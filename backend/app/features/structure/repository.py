from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import (
    Assignment,
    CampaignParticipant,
    DocumentLink,
    Employee,
    OrgUnit,
    StaffingLine,
)


def load_assignment(
    session: Session,
    assignment_id: int,
    *,
    is_demo: bool,
) -> Assignment | None:
    return session.scalar(
        select(Assignment)
        .where(
            Assignment.id == assignment_id,
            Assignment.is_demo.is_(is_demo),
        )
        .options(
            selectinload(Assignment.employee),
            selectinload(Assignment.staffing_line).selectinload(StaffingLine.org_unit),
        )
    )


def load_staffing_line(
    session: Session,
    staffing_line_id: int,
    *,
    is_demo: bool,
) -> StaffingLine | None:
    return session.scalar(
        select(StaffingLine)
        .where(
            StaffingLine.id == staffing_line_id,
            StaffingLine.is_demo.is_(is_demo),
            StaffingLine.is_active.is_(True),
        )
        .options(
            selectinload(StaffingLine.org_unit),
            selectinload(StaffingLine.assignments).selectinload(Assignment.employee),
        )
    )


def load_manager_assignments(
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
    return {manager.id: manager for manager in managers}


def find_existing_email(session: Session, emails: list[str]) -> str | None:
    if not emails:
        return None
    return session.scalar(select(Employee.email).where(Employee.email.in_(emails)))


def find_duplicate_employee_email(
    session: Session,
    email: str,
    *,
    exclude_employee_id: int,
) -> int | None:
    return session.scalar(
        select(Employee.id).where(
            Employee.email == email,
            Employee.id != exclude_employee_id,
        )
    )


def load_work_unit(session: Session, org_unit_id: int) -> OrgUnit | None:
    return session.scalar(
        select(OrgUnit).where(
            OrgUnit.id == org_unit_id,
            OrgUnit.is_demo.is_(False),
            OrgUnit.is_active.is_(True),
        )
    )


def find_duplicate_active_work_line(
    session: Session,
    *,
    org_unit_id: int,
    title: str,
) -> StaffingLine | None:
    return session.scalar(
        select(StaffingLine).where(
            StaffingLine.org_unit_id == org_unit_id,
            StaffingLine.is_demo.is_(False),
            StaffingLine.is_active.is_(True),
            StaffingLine.title == title,
        )
    )


def load_document_links_for_work_line(
    session: Session,
    staffing_line_id: int,
) -> list[DocumentLink]:
    return session.scalars(
        select(DocumentLink).where(
            DocumentLink.target_type == "staffing_line",
            DocumentLink.target_id == staffing_line_id,
            DocumentLink.is_demo.is_(False),
        )
    ).all()


def load_assignments_for_delete(
    session: Session,
    assignment_ids: set[int],
) -> list[Assignment]:
    return session.scalars(
        select(Assignment)
        .where(Assignment.id.in_(assignment_ids), Assignment.is_demo.is_(False))
        .options(selectinload(Assignment.employee))
    ).all()


def load_participants_for_assignments(
    session: Session,
    assignment_ids: set[int],
) -> list[CampaignParticipant]:
    return session.scalars(
        select(CampaignParticipant)
        .where(CampaignParticipant.assignment_id.in_(assignment_ids))
        .options(selectinload(CampaignParticipant.profile))
    ).all()


def load_active_wave_participants(
    session: Session,
    assignment_ids: set[int],
) -> list[CampaignParticipant]:
    return session.scalars(
        select(CampaignParticipant)
        .where(
            CampaignParticipant.assignment_id.in_(assignment_ids),
            CampaignParticipant.expected_to_submit.is_(True),
        )
        .options(
            selectinload(CampaignParticipant.campaign),
            selectinload(CampaignParticipant.wave),
            selectinload(CampaignParticipant.assignment).selectinload(Assignment.employee),
            selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
        )
    ).all()


def load_reports_for_managers(
    session: Session,
    assignment_ids: set[int],
) -> list[Assignment]:
    return session.scalars(
        select(Assignment).where(Assignment.manager_assignment_id.in_(assignment_ids))
    ).all()


def load_other_assignments_for_employees(
    session: Session,
    employee_ids: set[int],
    *,
    excluded_assignment_ids: set[int],
) -> list[Assignment]:
    return session.scalars(
        select(Assignment).where(
            Assignment.employee_id.in_(employee_ids),
            ~Assignment.id.in_(excluded_assignment_ids),
        )
    ).all()
