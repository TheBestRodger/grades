from __future__ import annotations

from sqlalchemy.orm import Session

from ..organization.service import get_manager_options as organization_manager_options


def get_manager_options(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    return organization_manager_options(session, is_demo)
