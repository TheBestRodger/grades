from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    ProfileReviewEvent,
    StaffingLine,
)
from ..organization.service import visible_unit_ids
from ..profiles.document_anomalies import profile_document_signal
from ..profiles.routing import route_current, route_path, route_reason
from ..profiles.rules import PROFILE_QUESTIONS
from .errors import ManagerOverviewError
from .manager_overview_risk import (
    RISK_LABELS,
    STATUS_LABELS,
    combined_risk,
    heat_label,
    heat_level,
    revision_payload,
    workflow_risk,
)


def get_manager_overview(session: Session, actor: Employee) -> dict[str, object]:
    if actor.system_role != "manager":
        raise ManagerOverviewError("Обзор доступен только руководителю.", 403)

    visible_ids = visible_unit_ids(session, actor, actor.is_demo)
    campaign = _current_campaign(session, visible_ids, actor.id)
    if campaign is None:
        return {
            "scope": "manager_subtree",
            "campaign_id": None,
            "campaign_name": None,
            "total_profiles": 0,
            "risk_counts": {},
            "status_counts": {},
            "status_labels": STATUS_LABELS,
            "units": [],
        }

    profiles = session.scalars(
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .join(CampaignParticipant.campaign)
        .join(Assignment.staffing_line)
        .where(
            StaffingLine.org_unit_id.in_(visible_ids),
            Assignment.employee_id != actor.id,
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
            Campaign.status == "active",
            Campaign.id == campaign.id,
        )
        .options(
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.employee),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.campaign),
            selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.revision),
            selectinload(EmployeeProfile.revisions),
        )
        .order_by(EmployeeProfile.id)
    ).all()

    unit_profiles: dict[int, list[dict[str, object]]] = defaultdict(list)
    totals = Counter({"normal": 0, "attention": 0, "critical": 0})
    status_counts: Counter[str] = Counter()
    for profile in profiles:
        item = _profile_signal(session, profile)
        assignment = profile.participant.assignment
        unit_profiles[assignment.staffing_line.org_unit_id].append(item)
        totals[item["risk_level"]] += 1
        status_counts[profile.workflow_status] += 1

    units = []
    for unit_id, items in sorted(
        unit_profiles.items(),
        key=lambda pair: pair[1][0]["unit_name"] if pair[1] else "",
    ):
        risk_counts = Counter(item["risk_level"] for item in items)
        quality_score = round(risk_counts["normal"] / len(items), 2) if items else 0
        level = heat_level(quality_score)
        units.append(
            {
                "unit_id": unit_id,
                "unit_name": items[0]["unit_name"],
                "total": len(items),
                "quality_score": quality_score,
                "quality_percent": round(quality_score * 100),
                "heat_level": level,
                "heat_label": heat_label(level),
                "risk_counts": dict(risk_counts),
                "status_counts": dict(Counter(item["workflow_status"] for item in items)),
                "profiles": items,
            }
        )

    return {
        "scope": "manager_subtree",
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "total_profiles": len(profiles),
        "risk_counts": dict(totals),
        "status_counts": dict(status_counts),
        "status_labels": STATUS_LABELS,
        "units": units,
    }


def _current_campaign(
    session: Session,
    visible_unit_ids: set[int],
    actor_employee_id: int,
) -> Campaign | None:
    if not visible_unit_ids:
        return None
    return session.scalar(
        select(Campaign)
        .join(Campaign.participants)
        .join(CampaignParticipant.assignment)
        .join(Assignment.staffing_line)
        .where(
            StaffingLine.org_unit_id.in_(visible_unit_ids),
            Assignment.employee_id != actor_employee_id,
            Campaign.status == "active",
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
        )
        .order_by(Campaign.id.desc())
        .limit(1)
    )


def _profile_signal(session: Session, profile: EmployeeProfile) -> dict[str, object]:
    assignment = profile.participant.assignment
    latest_revision = max(profile.revisions, key=lambda item: item.revision_no, default=None)
    return_count = sum(
        1 for event in profile.review_events if event.action in {"returned", "hr_returned"}
    )
    workflow_risk_level, workflow_reason = workflow_risk(
        profile.workflow_status,
        profile.progress_percent,
        return_count,
    )
    document_signal = profile_document_signal(session, profile)
    risk_level, reason = combined_risk(workflow_risk_level, workflow_reason, document_signal)
    return {
        "profile_id": profile.id,
        "employee_name": assignment.employee.full_name,
        "position_title": assignment.staffing_line.title,
        "unit_name": assignment.staffing_line.org_unit.name,
        "campaign_name": profile.participant.campaign.name,
        "workflow_status": profile.workflow_status,
        "workflow_status_label": STATUS_LABELS.get(profile.workflow_status, profile.workflow_status),
        "progress_percent": profile.progress_percent,
        "route_path": route_path(profile),
        "route_current": route_current(profile),
        "route_reason": route_reason(profile),
        "return_count": return_count,
        "risk_level": risk_level,
        "risk_label": RISK_LABELS[risk_level],
        "risk_reason": reason,
        "workflow_risk_level": workflow_risk_level,
        "workflow_risk_reason": workflow_reason,
        "document_signal": document_signal,
        "questions": PROFILE_QUESTIONS,
        "latest_revision": revision_payload(latest_revision),
    }
