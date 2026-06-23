from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Document, DocumentLink, EmployeeProfile
from .document_anomaly_specs import (
    CHECKED_TEXT_STATUSES,
    DOCUMENT_CHECKS,
    DOCUMENT_COVERAGE_STATUSES,
    LINK_COVERAGE_STATUSES,
    RISK_LABELS,
    RISK_ORDER,
)
from .document_anomaly_text import answers_text, revision_answers, tokens


def profile_document_signal(session: Session, profile: EmployeeProfile) -> dict[str, object]:
    revision = max(profile.revisions, key=lambda item: item.revision_no, default=None)
    if revision is None:
        return _signal(
            "attention",
            "Профиль ещё не сдавался, сравнение с документами невозможно.",
            [],
        )

    answers = revision_answers(revision)
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
    documents = _load_documents(session, is_demo, staffing_line_id, org_unit_id, spec)
    if not documents:
        return _check_result(spec, "attention", 0, [], [], f"{spec['label']}: нет подтверждённой связи с документом.")

    checked_documents = [
        document
        for document in documents
        if document.ocr_quality_status in CHECKED_TEXT_STATUSES and (document.content_text or "").strip()
    ]
    if not checked_documents:
        return _check_result(
            spec,
            "attention",
            0,
            documents,
            [],
            f"{spec['label']}: текст документа ещё не проверен HR.",
        )

    profile_tokens = tokens(answers_text(answers, spec["profile_keys"]))
    document_tokens = tokens(" ".join(document.content_text or "" for document in checked_documents))
    if not profile_tokens:
        return _check_result(
            spec,
            "attention",
            0,
            checked_documents,
            [],
            f"{spec['label']}: в профиле нет достаточного текста для сравнения.",
        )

    overlap = sorted(profile_tokens & document_tokens)
    denominator = max(1, min(len(profile_tokens), len(document_tokens)))
    score = round(len(overlap) / denominator, 3)
    risk_level, reason = _risk_for_score(spec, score)
    return _check_result(spec, risk_level, score, checked_documents, overlap[:8], reason)


def _load_documents(
    session: Session,
    is_demo: bool,
    staffing_line_id: int,
    org_unit_id: int,
    spec: dict[str, Any],
) -> list[Document]:
    target_id = org_unit_id if spec["target_type"] == "org_unit" else staffing_line_id
    return session.scalars(
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


def _risk_for_score(spec: dict[str, Any], score: float) -> tuple[str, str]:
    if score < spec["critical_threshold"]:
        return "critical", f"{spec['label']}: слабое пересечение терминов с профилем."
    if score < spec["attention_threshold"]:
        return "attention", f"{spec['label']}: пересечение есть, но его стоит проверить вручную."
    return "normal", f"{spec['label']}: ключевые темы профиля видны в документе."


def _check_result(
    spec: dict[str, Any],
    risk_level: str,
    score: float,
    documents: list[Document],
    matched_terms: list[str],
    reason: str,
) -> dict[str, object]:
    return {
        "document_type": spec["document_type"],
        "label": spec["label"],
        "risk_level": risk_level,
        "score": score,
        "documents": [_document_payload(document) for document in documents],
        "matched_terms": matched_terms,
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
