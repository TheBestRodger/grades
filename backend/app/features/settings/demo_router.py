from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.deps import current_hr, get_session, get_settings
from ...api.errors import run_operation
from ...core.config import Settings
from ...models import Employee
from ..organization.service import get_demo_users
from .demo_reset import reset_demo_data

router = APIRouter()


@router.get("/api/demo/users")
def demo_users(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    if settings.app_env not in {"demo-local", "test"}:
        return []
    return get_demo_users(session)


@router.post("/api/hr/demo-reset")
def reset_demo(
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return run_operation(
        lambda: reset_demo_data(session, actor, settings.work_staffing_file)
    )
