from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Document, DocumentLink, EmployeeProfile, ProfileRevision


LINK_COVERAGE_STATUSES = {"confirmed", "imported"}
DOCUMENT_COVERAGE_STATUSES = {"confirmed", "uploaded"}
CHECKED_TEXT_STATUSES = {"manual_demo", "good"}

RISK_ORDER = {"normal": 0, "attention": 1, "critical": 2}
RISK_LABELS = {
    "normal": "Совпадает с документами",
    "attention": "Нужно проверить документы",
    "critical": "Есть смысловое расхождение",
}

DOCUMENT_CHECKS = [
    {
        "document_type": "job_instruction",
        "target_type": "staffing_line",
        "label": "ДИ",
        "profile_keys": [
            "position_purpose",
            "duties_results",
        ],
        "attention_threshold": 0.25,
        "critical_threshold": 0.16,
    },
    {
        "document_type": "unit_regulation",
        "target_type": "org_unit",
        "label": "Положение",
        "profile_keys": [
            "org_structure",
            "position_purpose",
            "external_interactions",
            "internal_interactions",
            "government_interactions",
        ],
        "attention_threshold": 0.01,
        "critical_threshold": -1,
    },
    {
        "document_type": "professional_standard",
        "target_type": "staffing_line",
        "label": "Профстандарт",
        "profile_keys": [
            "duties_results",
            "education",
            "specialization",
            "certification",
            "legal_knowledge",
            "methods_knowledge",
            "technology_knowledge",
            "experience_requirements",
        ],
        "attention_threshold": 0.15,
        "critical_threshold": 0.08,
    },
]

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{4,}")
STOPWORDS = {
    "без",
    "более",
    "будет",
    "были",
    "ваша",
    "ваши",
    "весь",
    "всех",
    "если",
    "есть",
    "или",
    "как",
    "надо",
    "него",
    "нет",
    "нужно",
    "однако",
    "отдел",
    "очень",
    "при",
    "свои",
    "своих",
    "также",
    "тест",
    "тестов",
    "того",
    "только",
    "чтобы",
    "это",
    "этой",
    "этот",
    "для",
    "демо",
    "демонстрац",
    "демонстрационн",
    "что",
    "the",
    "and",
    "with",
}
ENDINGS = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ыми",
    "ими",
    "ых",
    "их",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ый",
    "ий",
    "ой",
    "ам",
    "ям",
    "ах",
    "ях",
    "ов",
    "ев",
    "ом",
    "ем",
    "ую",
    "юю",
    "ую",
    "ая",
    "яя",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
)


def profile_document_signal(session: Session, profile: EmployeeProfile) -> dict[str, object]:
    revision = max(profile.revisions, key=lambda item: item.revision_no, default=None)
    if revision is None:
        return _signal(
            "attention",
            "Профиль ещё не сдавался, сравнение с документами невозможно.",
            [],
        )

    answers = _revision_answers(revision)
    assignment = profile.participant.assignment
    checks = [
        _document_check(
            session,
            is_demo=profile.participant.campaign.is_demo,
            staffing_line_id=assignment.staffing_line_id,
            org_unit_id=assignment.staffing_line.org_unit_id,
            answers=answers,
            spec=spec,
        )
        for spec in DOCUMENT_CHECKS
    ]
    strongest = max((check["risk_level"] for check in checks), key=lambda level: RISK_ORDER[level])
    if strongest == "normal":
        reason = "Профиль достаточно пересекается с подтверждёнными документами."
    elif strongest == "critical":
        reason = "Есть слабое смысловое пересечение с одним или несколькими документами."
    else:
        reason = "Для части документов нужна ручная проверка покрытия или качества текста."
    return _signal(strongest, reason, checks)


def _document_check(
    session: Session,
    *,
    is_demo: bool,
    staffing_line_id: int,
    org_unit_id: int,
    answers: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, object]:
    target_id = org_unit_id if spec["target_type"] == "org_unit" else staffing_line_id
    documents = session.scalars(
        select(Document)
        .join(Document.links)
        .where(
            Document.is_demo.is_(is_demo),
            Document.document_type == spec["document_type"],
            Document.document_status.in_(DOCUMENT_COVERAGE_STATUSES),
            DocumentLink.target_type == spec["target_type"],
            DocumentLink.target_id == target_id,
            DocumentLink.link_status.in_(LINK_COVERAGE_STATUSES),
        )
        .order_by(Document.document_code)
    ).all()
    if not documents:
        return {
            "document_type": spec["document_type"],
            "label": spec["label"],
            "risk_level": "attention",
            "score": 0,
            "documents": [],
            "matched_terms": [],
            "reason": f"{spec['label']}: нет подтверждённой связи с документом.",
        }

    checked_documents = [
        document
        for document in documents
        if document.ocr_quality_status in CHECKED_TEXT_STATUSES and (document.content_text or "").strip()
    ]
    if not checked_documents:
        return {
            "document_type": spec["document_type"],
            "label": spec["label"],
            "risk_level": "attention",
            "score": 0,
            "documents": [_document_payload(document) for document in documents],
            "matched_terms": [],
            "reason": f"{spec['label']}: текст документа ещё не проверен HR.",
        }

    profile_tokens = _tokens(_answers_text(answers, spec["profile_keys"]))
    document_tokens = _tokens(" ".join(document.content_text or "" for document in checked_documents))
    if not profile_tokens:
        return {
            "document_type": spec["document_type"],
            "label": spec["label"],
            "risk_level": "attention",
            "score": 0,
            "documents": [_document_payload(document) for document in checked_documents],
            "matched_terms": [],
            "reason": f"{spec['label']}: в профиле нет достаточного текста для сравнения.",
        }

    overlap = sorted(profile_tokens & document_tokens)
    denominator = max(1, min(len(profile_tokens), len(document_tokens)))
    score = round(len(overlap) / denominator, 3)
    if score < spec["critical_threshold"]:
        risk_level = "critical"
        reason = f"{spec['label']}: слабое пересечение терминов с профилем."
    elif score < spec["attention_threshold"]:
        risk_level = "attention"
        reason = f"{spec['label']}: пересечение есть, но его стоит проверить вручную."
    else:
        risk_level = "normal"
        reason = f"{spec['label']}: ключевые темы профиля видны в документе."

    return {
        "document_type": spec["document_type"],
        "label": spec["label"],
        "risk_level": risk_level,
        "score": score,
        "documents": [_document_payload(document) for document in checked_documents],
        "matched_terms": overlap[:8],
        "reason": reason,
    }


def _signal(risk_level: str, reason: str, checks: list[dict[str, object]]) -> dict[str, object]:
    return {
        "risk_level": risk_level,
        "risk_label": RISK_LABELS[risk_level],
        "risk_reason": reason,
        "checks": checks,
    }


def _document_payload(document: Document) -> dict[str, object]:
    content = (document.content_text or "").strip()
    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "title": document.title,
        "ocr_quality_status": document.ocr_quality_status,
        "text_excerpt": content[:1200],
    }


def _revision_answers(revision: ProfileRevision) -> dict[str, Any]:
    try:
        loaded = json.loads(revision.answers_json or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _answers_text(answers: dict[str, Any], keys: list[str]) -> str:
    return " ".join(_flatten_answer(answers.get(key, "")) for key in keys)


def _flatten_answer(value: Any) -> str:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return _flatten_answer(decoded)
    if isinstance(value, list):
        return " ".join(_flatten_answer(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_answer(item) for item in value.values())
    if value is None:
        return ""
    return str(value)


def _tokens(text: str) -> set[str]:
    result = set()
    for raw in TOKEN_PATTERN.findall(text.replace("ё", "е").lower()):
        token = _stem(raw)
        if token and token not in STOPWORDS:
            result.add(token)
    return result


def _stem(token: str) -> str:
    for ending in ENDINGS:
        if len(token) > len(ending) + 4 and token.endswith(ending):
            return token[: -len(ending)]
    return token
