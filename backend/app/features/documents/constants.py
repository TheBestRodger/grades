from __future__ import annotations

DOCUMENT_TYPE_LABELS = {
    "job_instruction": "Должностная инструкция",
    "unit_regulation": "Положение подразделения",
    "professional_standard": "Профстандарт",
}

OCR_QUALITY_LABELS = {
    "manual_demo": "Текст внесен вручную",
    "pending": "Текст ожидает проверки HR",
    "requires_text": "Нужно внести распознанный текст",
    "good": "Текст проверен HR",
    "warning": "Текст требует исправления",
}

DOCUMENT_COVERAGE_STATUSES = {"confirmed", "uploaded"}
LINK_COVERAGE_STATUSES = {"confirmed", "imported"}
UPLOAD_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
