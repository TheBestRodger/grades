from __future__ import annotations

WAVE_STATUS_DRAFT = "draft"
WAVE_STATUS_ACTIVE = "active"
WAVE_STATUS_EDITING = "editing"

WAVE_EDITABLE_STATUSES = {WAVE_STATUS_DRAFT, WAVE_STATUS_EDITING}


def is_wave_editable(status: str) -> bool:
    return status in WAVE_EDITABLE_STATUSES


def can_launch_wave(status: str, participants_expected: int) -> bool:
    return is_wave_editable(status) and participants_expected > 0


def wave_status_label(status: str) -> str:
    return {
        WAVE_STATUS_DRAFT: "Черновик",
        WAVE_STATUS_ACTIVE: "Запущена",
        WAVE_STATUS_EDITING: "Редакция",
    }.get(status, status)
