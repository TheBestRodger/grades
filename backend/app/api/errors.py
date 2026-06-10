from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException

from ..ai_profile_checks import AiProfileCheckError
from ..auth_operations import AuthOperationError
from ..demo_reset import DemoResetError
from ..document_operations import DocumentOperationError
from ..export_operations import ExportOperationError
from ..hr_operations import HrOperationError
from ..hr_review_operations import HrReviewOperationError
from ..manager_overview import ManagerOverviewError
from ..profile_operations import ProfileOperationError
from ..review_operations import ReviewOperationError
from ..work_employee_import import WorkEmployeeImportError

T = TypeVar("T")
OperationError = (
    HrOperationError
    | ProfileOperationError
    | ReviewOperationError
    | HrReviewOperationError
    | ManagerOverviewError
    | ExportOperationError
    | DocumentOperationError
    | DemoResetError
    | WorkEmployeeImportError
    | AuthOperationError
    | AiProfileCheckError
)


def run_operation(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except (
        HrOperationError,
        ProfileOperationError,
        ReviewOperationError,
        HrReviewOperationError,
        ManagerOverviewError,
        ExportOperationError,
        DocumentOperationError,
        DemoResetError,
        WorkEmployeeImportError,
        AuthOperationError,
        AiProfileCheckError,
    ) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
