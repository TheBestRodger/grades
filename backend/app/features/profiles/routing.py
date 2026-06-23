from __future__ import annotations

from ...models import EmployeeProfile


def route_path(profile: EmployeeProfile) -> list[str]:
    if profile.participant.assignment.manager_assignment_id is None:
        return ["Сотрудник", "HR"]
    return ["Сотрудник", "Руководитель", "HR"]


def route_current(profile: EmployeeProfile) -> str:
    assignment = profile.participant.assignment
    direct_hr_route = assignment.manager_assignment_id is None
    if profile.workflow_status in {"not_started", "draft", "returned_for_revision"}:
        return "Сотрудник"
    if profile.workflow_status in {"submitted", "under_review"}:
        if direct_hr_route:
            return "HR"
        manager = assignment.manager.employee.full_name if assignment.manager is not None else "Руководитель"
        return f"Руководитель: {manager}"
    if profile.workflow_status in {"manager_verified", "returned_by_hr"}:
        return "HR"
    if profile.workflow_status == "hr_accepted":
        return "Маршрут завершен"
    return "Сотрудник"


def route_reason(profile: EmployeeProfile) -> str:
    assignment = profile.participant.assignment
    if (
        profile.workflow_status == "returned_for_revision"
        and assignment.manager_assignment_id is None
    ):
        return "HR вернул анкету сотруднику на доработку."
    if assignment.manager_assignment_id is None:
        return "Непосредственный руководитель не найден, анкета направлена сразу в HR."
    if profile.workflow_status in {"submitted", "under_review"}:
        return "Анкета находится у непосредственного руководителя."
    if profile.workflow_status in {"manager_verified", "returned_by_hr"}:
        return "Анкета находится на финальной проверке HR."
    if profile.workflow_status == "hr_accepted":
        return "Анкета завершена."
    return "Маршрут будет определён после отправки анкеты."


_route_path = route_path
_route_current = route_current
_route_reason = route_reason
