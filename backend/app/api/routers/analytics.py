from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...hr_analytics import get_hr_analytics
from ...models import Employee
from ..deps import current_hr, get_session

router = APIRouter()


@router.get("/api/hr/analytics")
def hr_analytics(
    actor: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> dict[str, object]:
    return get_hr_analytics(session, actor)


@router.get("/api/work/hr/analytics")
def work_hr_analytics(
    actor: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> dict[str, object]:
    return get_hr_analytics(session, actor, is_demo=False)
