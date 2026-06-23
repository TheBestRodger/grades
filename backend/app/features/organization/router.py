from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.deps import current_actor, get_session
from ...models import Employee
from .service import organization_summary, organization_tree

router = APIRouter()


@router.get("/api/organization/tree")
def tree(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return organization_tree(session, actor, is_demo=actor.is_demo)


@router.get("/api/organization/summary")
def summary(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return organization_summary(session, actor, is_demo=actor.is_demo)


@router.get("/api/work/organization/tree")
def work_tree(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return organization_tree(session, actor, is_demo=False)


@router.get("/api/work/organization/summary")
def work_summary(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return organization_summary(session, actor, is_demo=False)
