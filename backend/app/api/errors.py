from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias, TypeVar

from fastapi import HTTPException

from ..features.analytics.errors import ManagerOverviewError
from ..features.auth.errors import AuthOperationError
from ..features.campaigns.errors import CampaignOperationError
from ..features.documents.errors import DocumentOperationError
from ..features.exports.errors import ExportOperationError
from ..features.hr_reviews.errors import HrReviewOperationError
from ..features.imports.work_employee import WorkEmployeeImportError
from ..features.manager_reviews.errors import ReviewOperationError
from ..features.notifications.errors import NotificationOperationError
from ..features.profiles.errors import AiProfileCheckError, ProfileOperationError
from ..features.settings.demo_reset import DemoResetError
from ..features.structure.errors import StructureOperationError

T = TypeVar("T")
OperationError: TypeAlias = (
    ProfileOperationError
    | ReviewOperationError
    | HrReviewOperationError
    | ManagerOverviewError
    | ExportOperationError
    | DocumentOperationError
    | DemoResetError
    | WorkEmployeeImportError
    | AuthOperationError
    | AiProfileCheckError
    | CampaignOperationError
    | NotificationOperationError
    | StructureOperationError
)
_OPERATION_ERROR_TYPES = (
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
    CampaignOperationError,
    NotificationOperationError,
    StructureOperationError,
)


def run_operation(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except _OPERATION_ERROR_TYPES as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
