from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.deps import current_actor, get_session
from ...api.errors import run_operation
from ...models import Employee
from ..analytics.manager_overview import get_manager_overview
from .schemas import BulkReviewReturnRequest, ReviewReturnRequest, ReviewVerifyRequest
from .service import (
    bulk_return_for_revision,
    get_review_queue,
    return_for_revision,
    take_for_review,
    verify_profile,
)

router = APIRouter()


@router.get("/api/manager/reviews")
def manager_reviews(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return run_operation(lambda: get_review_queue(session, actor))


@router.get("/api/manager/overview")
def manager_overview(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return run_operation(lambda: get_manager_overview(session, actor))


@router.post("/api/manager/reviews/bulk-return")
def bulk_return_profiles_for_revision(
    request: BulkReviewReturnRequest,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: bulk_return_for_revision(session, actor, request))


@router.post("/api/manager/reviews/{profile_id}/take")
def take_profile_for_review(
    profile_id: int,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: take_for_review(session, actor, profile_id))


@router.post("/api/manager/reviews/{profile_id}/return")
def return_profile_for_revision(
    profile_id: int,
    request: ReviewReturnRequest,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: return_for_revision(session, actor, profile_id, request))


@router.post("/api/manager/reviews/{profile_id}/verify")
def manager_verify_profile(
    profile_id: int,
    request: ReviewVerifyRequest,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: verify_profile(session, actor, profile_id, request))
