from __future__ import annotations


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
        "profile_keys": ["position_purpose", "duties_results"],
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
