from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...hr_operations import recent_audit_events
from ...models import Employee
from ..deps import current_hr, get_session

router = APIRouter()


@router.get("/api/hr/audit/recent")
def audit_events(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return recent_audit_events(session)


@router.get("/api/work/hr/audit/recent")
def work_audit_events(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return recent_audit_events(session, is_demo=False)
