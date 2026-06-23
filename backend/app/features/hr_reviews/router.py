from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.deps import current_hr, get_session
from ...api.errors import run_operation
from ...models import Employee
from .schemas import BulkReviewReturnRequest, ReviewReturnRequest, ReviewVerifyRequest
from .service import (
    accept_profile,
    bulk_return_to_manager,
    get_hr_review_queue,
    return_to_manager,
)

router = APIRouter()


@router.get("/api/work/hr/profile-reviews")
def work_hr_profile_reviews(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_hr_review_queue(session, is_demo=False)


@router.post("/api/work/hr/profile-reviews/bulk-return")
def bulk_return_work_profiles_by_hr(
    request: BulkReviewReturnRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: bulk_return_to_manager(session, actor, request, is_demo=False))


@router.post("/api/work/hr/profile-reviews/{profile_id}/accept")
def accept_work_profile_by_hr(
    profile_id: int,
    request: ReviewVerifyRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: accept_profile(session, actor, profile_id, request, is_demo=False))


@router.post("/api/work/hr/profile-reviews/{profile_id}/return")
def return_work_profile_by_hr(
    profile_id: int,
    request: ReviewReturnRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: return_to_manager(session, actor, profile_id, request, is_demo=False))


@router.get("/api/hr/profile-reviews")
def hr_profile_reviews(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_hr_review_queue(session)


@router.post("/api/hr/profile-reviews/bulk-return")
def bulk_return_profiles_by_hr(
    request: BulkReviewReturnRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: bulk_return_to_manager(session, actor, request))


@router.post("/api/hr/profile-reviews/{profile_id}/accept")
def accept_profile_by_hr(
    profile_id: int,
    request: ReviewVerifyRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: accept_profile(session, actor, profile_id, request))


@router.post("/api/hr/profile-reviews/{profile_id}/return")
def return_profile_by_hr(
    profile_id: int,
    request: ReviewReturnRequest,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: return_to_manager(session, actor, profile_id, request))
