from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException

from ..features.profiles.errors import AiProfileCheckError
from ..features.auth.errors import AuthOperationError
from ..features.campaigns.errors import CampaignOperationError
from ..features.settings.demo_reset import DemoResetError
from ..features.hr_reviews.errors import HrReviewOperationError
from ..features.profiles.errors import ProfileOperationError
from ..features.manager_reviews.errors import ReviewOperationError
from ..features.documents.errors import DocumentOperationError
from ..features.exports.errors import ExportOperationError
from ..features.analytics.errors import ManagerOverviewError
from ..features.imports.work_employee import WorkEmployeeImportError
from ..features.structure.errors import StructureOperationError
from ..features.notifications.errors import NotificationOperationError

T = TypeVar("T")
OperationError = (
    ProfileOperationError
    | ReviewOperationError
    | HrReviewOperationError
    | ManagerOverviewError
    | ExportOperationError
    | DocumentOperationError
    | DemoResetError
    | WorkEmployeeImportError
    | StructureOperationError
    | AuthOperationError
    | AiProfileCheckError
    | CampaignOperationError
    | NotificationOperationError
)


def run_operation(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except (
        ProfileOperationError,
        ReviewOperationError,
        HrReviewOperationError,
        ManagerOverviewError,
        ExportOperationError,
        DocumentOperationError,
        DemoResetError,
        WorkEmployeeImportError,
        StructureOperationError,
        AuthOperationError,
        AiProfileCheckError,
        CampaignOperationError,
        NotificationOperationError,
    ) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
