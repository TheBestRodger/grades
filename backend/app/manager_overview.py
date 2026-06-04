from __future__ import annotations

from collections import Counter, defaultdict
import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    ProfileReviewEvent,
    ProfileRevision,
    StaffingLine,
)
from .organization import _visible_unit_ids
from .profile_document_anomalies import profile_document_signal
from .profile_operations import PROFILE_QUESTIONS


class ManagerOverviewError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


RISK_LABELS = {
    "normal": "Норма",
    "attention": "Есть вопросы",
    "critical": "Красный сигнал",
}

STATUS_LABELS = {
    "not_started": "Не начат",
    "draft": "Черновик",
    "submitted": "Ожидает проверки",
    "under_review": "На проверке",
    "returned_for_revision": "На доработке",
    "manager_verified": "Подтвержден",
    "returned_by_hr": "Вернул HR",
    "hr_accepted": "Принят HR",
}


def get_manager_overview(session: Session, actor: Employee) -> dict[str, object]:
    if actor.system_role != "manager":
        raise ManagerOverviewError("Обзор доступен только руководителю.", 403)

    visible_unit_ids = _visible_unit_ids(session, actor, actor.is_demo)
    campaign = _current_campaign(session, visible_unit_ids, actor.id)
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
            StaffingLine.org_unit_id.in_(visible_unit_ids),
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
        heat_level = _heat_level(quality_score)
        units.append(
            {
                "unit_id": unit_id,
                "unit_name": items[0]["unit_name"],
                "total": len(items),
                "quality_score": quality_score,
                "quality_percent": round(quality_score * 100),
                "heat_level": heat_level,
                "heat_label": _heat_label(heat_level),
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
    workflow_risk_level, workflow_reason = _risk(
        profile.workflow_status,
        profile.progress_percent,
        return_count,
    )
    document_signal = profile_document_signal(session, profile)
    risk_level, reason = _combined_risk(workflow_risk_level, workflow_reason, document_signal)
    return {
        "profile_id": profile.id,
        "employee_name": assignment.employee.full_name,
        "position_title": assignment.staffing_line.title,
        "unit_name": assignment.staffing_line.org_unit.name,
        "campaign_name": profile.participant.campaign.name,
        "workflow_status": profile.workflow_status,
        "workflow_status_label": STATUS_LABELS.get(profile.workflow_status, profile.workflow_status),
        "progress_percent": profile.progress_percent,
        "return_count": return_count,
        "risk_level": risk_level,
        "risk_label": RISK_LABELS[risk_level],
        "risk_reason": reason,
        "workflow_risk_level": workflow_risk_level,
        "workflow_risk_reason": workflow_reason,
        "document_signal": document_signal,
        "questions": PROFILE_QUESTIONS,
        "latest_revision": _revision_payload(latest_revision),
    }


def _revision_payload(revision: ProfileRevision | None) -> dict[str, object] | None:
    if revision is None:
        return None
    try:
        answers = json.loads(revision.answers_json or "{}")
    except json.JSONDecodeError:
        answers = {}
    try:
        assisted = json.loads(revision.assisted_sections_json or "{}")
    except json.JSONDecodeError:
        assisted = {}
    if isinstance(assisted, list):
        assisted = {"checked_questions": assisted, "ignored_questions": [], "without_ai_questions": []}
    if not isinstance(assisted, dict):
        assisted = {"checked_questions": [], "ignored_questions": [], "without_ai_questions": []}
    return {
        "id": revision.id,
        "revision_no": revision.revision_no,
        "submitted_at": revision.submitted_at.isoformat(),
        "assistant_mode": revision.assistant_mode,
        "assistance_level": revision.assistance_level,
        "assisted_sections": {
            "checked_questions": assisted.get("checked_questions", []),
            "ignored_questions": assisted.get("ignored_questions", []),
            "without_ai_questions": assisted.get("without_ai_questions", []),
            "answer_statuses": assisted.get("answer_statuses", {}),
        },
        "answers": answers if isinstance(answers, dict) else {},
    }


def _combined_risk(
    workflow_risk_level: str,
    workflow_reason: str,
    document_signal: dict[str, object],
) -> tuple[str, str]:
    document_risk = str(document_signal["risk_level"])
    if document_risk == "critical":
        return "critical", f"Документы: {document_signal['risk_reason']}"
    if workflow_risk_level == "critical":
        return "critical", workflow_reason
    return workflow_risk_level, workflow_reason


def _risk(status: str, progress_percent: float, return_count: int) -> tuple[str, str]:
    if status == "returned_by_hr":
        return "critical", "HR вернул профиль руководителю."
    if return_count >= 2:
        return "critical", "Есть повторные возвраты, стоит разобрать причину."
    if status == "not_started":
        return "critical", "Профиль еще не начат в активной кампании."
    if progress_percent < 50:
        return "critical", "Заполнено меньше половины обязательных разделов."
    if status in {"draft", "submitted", "under_review", "returned_for_revision"}:
        return "attention", "Профиль требует внимания или решения руководителя."
    if return_count == 1:
        return "attention", "Был возврат на уточнение."
    return "normal", "Сильных сигналов нет."


def _heat_level(quality_score: float) -> str:
    if quality_score >= 1:
        return "green"
    if quality_score >= 0.5:
        return "yellow"
    return "red"


def _heat_label(heat_level: str) -> str:
    return {
        "green": "100% без сигналов",
        "yellow": "Есть вопросы",
        "red": "Требует разбора",
    }[heat_level]
