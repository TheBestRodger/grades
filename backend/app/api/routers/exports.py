from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ...config import PROJECT_ROOT
from ...export_operations import (
    CAMPAIGN_EXPORT_COLUMNS,
    PROFILE_EXPORT_COLUMNS,
    credentials_to_xlsx,
    export_campaigns,
    export_owned_profile_template,
    export_profiles,
    issue_credentials_for_new_wave_participants,
    rows_to_csv,
)
from ...models import Employee
from ...schemas import CredentialsExportRequest
from ..deps import current_actor, current_hr, get_session
from ..errors import run_operation

router = APIRouter()


@router.get("/api/hr/exports/profiles.json")
def export_profiles_json(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return export_profiles(session)


@router.get("/api/hr/exports/profiles.csv")
def export_profiles_csv(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> Response:
    return Response(
        content=rows_to_csv(export_profiles(session), PROFILE_EXPORT_COLUMNS),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="profiles_export.csv"'},
    )


@router.get("/api/hr/exports/campaigns.json")
def export_campaigns_json(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return export_campaigns(session)


@router.get("/api/hr/exports/campaigns.csv")
def export_campaigns_csv(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> Response:
    return Response(
        content=rows_to_csv(export_campaigns(session), CAMPAIGN_EXPORT_COLUMNS),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="campaigns_export.csv"'},
    )


@router.post("/api/hr/exports/credentials.xlsx")
def export_credentials_xlsx(
    payload: CredentialsExportRequest, _: Employee = Depends(current_hr)
) -> Response:
    rows = [row.model_dump() for row in payload.rows]
    return Response(
        content=credentials_to_xlsx(rows),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="credentials.xlsx"'},
    )


@router.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx")
def issue_demo_wave_credentials_xlsx(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> Response:
    return run_operation(
        lambda: Response(
            content=issue_credentials_for_new_wave_participants(
                session, actor, campaign_id, wave_id, is_demo=True
            ),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="credentials_new_participants.xlsx"'
            },
        )
    )


@router.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx")
def issue_work_wave_credentials_xlsx(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> Response:
    return run_operation(
        lambda: Response(
            content=issue_credentials_for_new_wave_participants(
                session, actor, campaign_id, wave_id, is_demo=False
            ),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="credentials_new_participants.xlsx"'
            },
        )
    )


@router.get("/api/my/profiles/{profile_id}/export.xlsx")
def export_personal_profile_template(
    profile_id: int,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> Response:
    template_path = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "Шаблон профиля должности (1).xlsx"
    )
    content = run_operation(
        lambda: export_owned_profile_template(session, actor, profile_id, template_path)
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="profile_template_export.xlsx"'
        },
    )
