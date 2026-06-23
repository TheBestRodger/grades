from __future__ import annotations

from typing import Protocol


class AssignmentLike(Protocol):
    fte: float


class StaffingLineLike(Protocol):
    approved_fte: float
    assignments: list[AssignmentLike]


def effective_is_hr(system_role: str, is_hr: bool) -> bool:
    return is_hr or system_role == "hr"


def assigned_fte(line: StaffingLineLike) -> float:
    return round(sum(assignment.fte for assignment in line.assignments), 2)


def remaining_fte(line: StaffingLineLike) -> float:
    return round(line.approved_fte - assigned_fte(line), 2)


def requested_fte(items: list[AssignmentLike]) -> float:
    return round(sum(item.fte for item in items), 4)


def has_enough_fte(line: StaffingLineLike, requested: float) -> bool:
    return requested <= remaining_fte(line) + 1e-9
