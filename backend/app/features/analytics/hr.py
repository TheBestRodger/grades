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
from ..campaigns.service import get_campaigns
from ..documents.service import get_document_registry
from ..organization.service import organization_summary


STATUS_LABELS = {
    "not_started": "Не начато",
    "draft": "Черновик",
    "submitted": "Сдано",
    "under_review": "На проверке руководителя",
    "returned_for_revision": "Возвращено сотруднику",
    "manager_verified": "Подтверждено руководителем",
    "returned_by_hr": "Возвращено HR",
    "hr_accepted": "Принято HR",
}
STATUS_ORDER = tuple(STATUS_LABELS)
RETURN_ACTIONS = {"returned", "hr_returned"}


def get_hr_analytics(session: Session, actor: Employee, is_demo: bool = True) -> dict[str, object]:
    participants = session.scalars(
        select(CampaignParticipant)
        .join(CampaignParticipant.campaign)
        .where(
            Campaign.is_demo.is_(is_demo),
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
        )
        .options(
            selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(CampaignParticipant.profile).selectinload(EmployeeProfile.revisions),
            selectinload(CampaignParticipant.profile)
            .selectinload(EmployeeProfile.review_events)
            .selectinload(ProfileReviewEvent.revision),
        )
        .order_by(CampaignParticipant.id)
    ).all()
    campaigns = get_campaigns(session, is_demo=is_demo)
    registry = get_document_registry(session, is_demo=is_demo)
    structure = organization_summary(session, actor, is_demo=is_demo)

    status_counts: Counter[str] = Counter()
    progress_total = 0.0
    revision_count = 0
    return_events = 0
    returned_profiles = 0
    resubmitted_profiles = 0
    units: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "unit_name": "",
            "profiles_expected": 0,
            "progress_total": 0.0,
            "accepted": 0,
            "returned": 0,
        }
    )
    for participant in participants:
        profile = participant.profile
        status = profile.workflow_status if profile is not None else "not_started"
        progress = profile.progress_percent if profile is not None else 0.0
        events = profile.review_events if profile is not None else []
        profile_returns = sum(1 for event in events if event.action in RETURN_ACTIONS)
        revisions = profile.revisions if profile is not None else []
        status_counts[status] += 1
        progress_total += progress
        revision_count += len(revisions)
        return_events += profile_returns
        returned_profiles += int(profile_returns > 0)
        resubmitted_profiles += int(len(revisions) > 1)

        assignment = participant.assignment
        unit = units[assignment.staffing_line.org_unit_id]
        unit["unit_name"] = assignment.staffing_line.org_unit.name
        unit["profiles_expected"] += 1
        unit["progress_total"] += progress
        unit["accepted"] += int(status == "hr_accepted")
        unit["returned"] += int(profile_returns > 0)

    expected = len(participants)
    unit_rows = [
        {
            "unit_id": unit_id,
            "unit_name": str(values["unit_name"]),
            "profiles_expected": int(values["profiles_expected"]),
            "average_progress_percent": _percent(
                float(values["progress_total"]),
                int(values["profiles_expected"]),
            ),
            "accepted": int(values["accepted"]),
            "returned": int(values["returned"]),
        }
        for unit_id, values in units.items()
    ]
    unit_rows.sort(key=lambda item: (-item["profiles_expected"], item["unit_name"]))

    return {
        "scope": "demo" if is_demo else "work",
        "note": (
            "Аналитика рассчитана по данным выбранного контура."
            if is_demo
            else "Рабочая аналитика рассчитана без включения данных другого контура."
        ),
        "structure": structure,
        "campaigns_total": len(campaigns),
        "active_campaigns": sum(1 for campaign in campaigns if campaign["status"] == "active"),
        "profiles_expected": expected,
        "average_progress_percent": _percent(progress_total, expected),
        "profiles_with_revisions": sum(
            1 for participant in participants if participant.profile and participant.profile.revisions
        ),
        "revision_count": revision_count,
        "resubmitted_profiles": resubmitted_profiles,
        "returned_profiles": returned_profiles,
        "return_events": return_events,
        "accepted_profiles": status_counts["hr_accepted"],
        "funnel": [
            {
                "status": status,
                "label": STATUS_LABELS[status],
                "count": status_counts[status],
                "percent": _percent(status_counts[status] * 100, expected),
            }
            for status in STATUS_ORDER
        ],
        "units": unit_rows,
        "campaigns": [
            {
                "id": campaign["id"],
                "name": campaign["name"],
                "status": campaign["status"],
                "participants_expected": campaign["total_participants_expected"],
                "active_wave_name": campaign["active_wave_name"],
                "status_counts": campaign["status_counts"],
            }
            for campaign in campaigns
        ],
        "documents": {
            "documents_total": registry["documents_total"],
            "confirmed_documents": registry["confirmed_documents"],
            "ocr_quality_counts": registry["ocr_quality_counts"],
            "coverage": {
                key: {
                    "label": value["label"],
                    "total": value["total"],
                    "covered": value["covered"],
                    "missing": value["missing"],
                    "percent": value["percent"],
                }
                for key, value in registry["coverage"].items()
            },
        },
    }


def _percent(value: float, total: int) -> float:
    return round(value / total, 2) if total else 0
