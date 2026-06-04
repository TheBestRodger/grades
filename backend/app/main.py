from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .ai_gateway import build_ai_gateway
from .ai_gateway import build_local_gateway_from_configuration
from .ai_profile_checks import AiProfileCheckError, assess_profile_answer
from .auth_operations import (
    AuthOperationError,
    actor_from_authorization,
    consume_magic_link,
    employee_payload,
    ensure_bootstrap_hr_credentials,
    login_with_password,
    logout_session,
    request_magic_link,
)
from .config import PROJECT_ROOT, Settings
from .db import Database
from .demo_reset import DemoResetError, reset_demo_data
from .document_operations import (
    DocumentOperationError,
    get_document_registry,
    get_manager_document_registry,
    get_work_document_source,
    review_work_document_quality,
    set_work_document_link,
    upload_work_document,
)
from .export_operations import (
    CAMPAIGN_EXPORT_COLUMNS,
    ExportOperationError,
    PROFILE_EXPORT_COLUMNS,
    credentials_to_xlsx,
    export_campaigns,
    issue_credentials_for_new_wave_participants,
    export_owned_profile_template,
    export_profiles,
    rows_to_csv,
)
from .hr_operations import (
    HrOperationError,
    add_employees,
    create_work_staffing_line,
    create_campaign,
    create_campaign_wave,
    edit_campaign_wave,
    exclude_unit_from_campaign,
    get_campaigns,
    get_manager_options,
    include_unit_in_campaign,
    launch_campaign_wave,
    recent_audit_events,
    set_campaign_assignments,
)
from .hr_analytics import get_hr_analytics
from .import_grades_documents import (
    DOCUMENTS_DIR,
    _default_staffing_file,
    import_grades_documents,
)
from .hr_review_operations import (
    HrReviewOperationError,
    accept_profile,
    bulk_return_to_manager,
    get_hr_review_queue,
    return_to_manager,
)
from .manager_overview import ManagerOverviewError, get_manager_overview
from .models import Employee
from .organization import (
    get_demo_users,
    organization_summary,
    organization_tree,
    require_actor,
)
from .profile_operations import (
    ProfileOperationError,
    get_my_profiles,
    get_questionnaire_settings,
    save_draft,
    submit_profile,
    update_questionnaire_settings,
)
from .review_operations import (
    ReviewOperationError,
    bulk_return_for_revision,
    get_review_queue,
    return_for_revision,
    take_for_review,
    verify_profile,
)
from .seed import seed_demo_data
from .schemas import (
    AiConfigurationUpdate,
    AiProfileAnswerCheckRequest,
    BulkEmployeeCreate,
    BulkReviewReturnRequest,
    CampaignAssignmentsUpdate,
    CampaignCreate,
    CampaignWaveCreate,
    CredentialsExportRequest,
    MagicLinkConsumeRequest,
    MagicLinkRequest,
    PasswordLoginRequest,
    WorkDocumentLinkUpdate,
    WorkDocumentQualityUpdate,
    WorkStaffingLineCreate,
    ProfileAnswersRequest,
    QuestionnaireSettingsUpdate,
    ReviewReturnRequest,
    ReviewVerifyRequest,
)
from .settings_operations import (
    get_ai_configuration,
    update_ai_configuration,
)
from .work_employee_import import WorkEmployeeImportError, import_work_assignments


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.database_url)
    ai_gateway = build_ai_gateway(settings.ai_mode, settings.ai_provider)
    document_storage_dir = (
        settings.document_storage_dir or PROJECT_ROOT / "backend" / "data" / "documents"
    ).resolve()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.migrate()
        with database.session() as session:
            seed_demo_data(session, settings.work_staffing_file)
            ensure_bootstrap_hr_credentials(session, settings)
            if settings.auto_import_grades_documents:
                staffing_file = _default_staffing_file()
                if staffing_file.exists() and DOCUMENTS_DIR.exists():
                    import_grades_documents(
                        session,
                        staffing_file=staffing_file,
                        documents_dir=DOCUMENTS_DIR,
                        storage_dir=document_storage_dir,
                        apply_changes=True,
                    )
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.state.ai_gateway = ai_gateway
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_session() -> Iterator[Session]:
        with database.session() as session:
            yield session

    def current_actor(
        authorization: str | None = Header(default=None),
        x_demo_user_id: int | None = Header(default=None),
        session: Session = Depends(get_session),
    ) -> Employee:
        try:
            session_actor = actor_from_authorization(session, authorization)
        except AuthOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        if session_actor is not None:
            return session_actor
        if settings.app_env not in {"demo-local", "test"}:
            raise HTTPException(status_code=401, detail="Войдите по одноразовой ссылке.")
        if x_demo_user_id is None:
            raise HTTPException(status_code=401, detail="Войдите или выберите пользователя.")
        actor = require_actor(session, x_demo_user_id)
        if actor is None:
            raise HTTPException(status_code=403, detail="Пользователь не найден.")
        return actor

    def current_hr(actor: Employee = Depends(current_actor)) -> Employee:
        if actor.system_role != "hr":
            raise HTTPException(status_code=403, detail="HR access is required.")
        return actor

    def run_hr_operation(operation):
        try:
            return operation()
        except HrOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_profile_operation(operation):
        try:
            return operation()
        except ProfileOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_review_operation(operation):
        try:
            return operation()
        except ReviewOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_hr_review_operation(operation):
        try:
            return operation()
        except HrReviewOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_manager_overview_operation(operation):
        try:
            return operation()
        except ManagerOverviewError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_export_operation(operation):
        try:
            return operation()
        except ExportOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_document_operation(operation):
        try:
            return operation()
        except DocumentOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_demo_reset_operation(operation):
        try:
            return operation()
        except DemoResetError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_work_employee_import_operation(operation):
        try:
            return operation()
        except WorkEmployeeImportError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_auth_operation(operation):
        try:
            return operation()
        except AuthOperationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    def run_ai_profile_check_operation(operation):
        try:
            return operation()
        except AiProfileCheckError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    @app.get("/api/health")
    def health() -> dict[str, object]:
        with database.session() as session:
            ai_config = get_ai_configuration(session, settings)
            runtime_ai_config = get_ai_configuration(session, settings, include_secret=True)
        runtime_ai_gateway = build_local_gateway_from_configuration(runtime_ai_config)
        ai = runtime_ai_gateway.health_status()
        return {
            "status": "ok",
            "environment": settings.app_env,
            "ai": {
                "mode": ai.mode,
                "provider": ai.provider,
                "available": ai.available,
                "label": ai.label,
                "fallback_message": ai.fallback_message,
                "configuration": ai_config,
            },
        }

    @app.get("/api/demo/users")
    def demo_users(session: Session = Depends(get_session)) -> list[dict[str, object]]:
        if settings.app_env not in {"demo-local", "test"}:
            return []
        return get_demo_users(session)

    @app.post("/api/auth/magic-link/request")
    def auth_magic_link_request(
        payload: MagicLinkRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_auth_operation(lambda: request_magic_link(session, payload.email, settings))

    @app.post("/api/auth/magic-link/consume")
    def auth_magic_link_consume(
        payload: MagicLinkConsumeRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_auth_operation(lambda: consume_magic_link(session, payload.token))

    @app.post("/api/auth/login")
    def auth_password_login(
        payload: PasswordLoginRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_auth_operation(lambda: login_with_password(session, payload.username, payload.password))

    @app.post("/api/auth/logout")
    def auth_logout(
        authorization: str | None = Header(default=None),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return logout_session(session, authorization)

    @app.get("/api/me")
    def me(actor: Employee = Depends(current_actor)) -> dict[str, object]:
        return employee_payload(actor)

    @app.get("/api/hr/settings/ai")
    def hr_ai_settings(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_ai_configuration(session, settings)

    @app.put("/api/hr/settings/ai")
    def update_hr_ai_settings(
        request: AiConfigurationUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return update_ai_configuration(session, actor, settings, request)

    @app.get("/api/hr/settings/questionnaire")
    def hr_questionnaire_settings(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_questionnaire_settings(session)

    @app.put("/api/hr/settings/questionnaire")
    def update_hr_questionnaire_settings(
        request: QuestionnaireSettingsUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_profile_operation(
            lambda: update_questionnaire_settings(session, actor, request)
        )

    @app.post("/api/my/profiles/{profile_id}/ai-check")
    def ai_check_profile_answer(
        profile_id: int,
        request: AiProfileAnswerCheckRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        ai_config = get_ai_configuration(session, settings, include_secret=True)
        gateway = build_local_gateway_from_configuration(
            ai_config,
            generate=getattr(app.state, "ollama_generate", None),
        )
        return run_ai_profile_check_operation(
            lambda: assess_profile_answer(
                session,
                actor,
                profile_id,
                request,
                gateway,
                int(ai_config.get("clarity_threshold", 70)),
                str(ai_config.get("followup_strictness", "balanced")),
            )
        )

    @app.get("/api/organization/tree")
    def tree(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return organization_tree(session, actor, is_demo=actor.is_demo)

    @app.get("/api/organization/summary")
    def summary(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return organization_summary(session, actor, is_demo=actor.is_demo)

    @app.get("/api/work/organization/tree")
    def work_tree(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return organization_tree(session, actor, is_demo=False)

    @app.get("/api/work/organization/summary")
    def work_summary(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return organization_summary(session, actor, is_demo=False)

    @app.get("/api/hr/managers")
    def managers(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_manager_options(session)

    @app.get("/api/work/hr/managers")
    def work_managers(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_manager_options(session, is_demo=False)

    @app.post("/api/hr/staffing-lines/{staffing_line_id}/employees/bulk")
    def bulk_add_employees(
        staffing_line_id: int,
        request: BulkEmployeeCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: add_employees(session, actor, staffing_line_id, request))

    @app.get("/api/hr/campaigns")
    def campaigns(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_campaigns(session)

    @app.post("/api/hr/campaigns")
    def add_campaign(
        request: CampaignCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: create_campaign(session, actor, request))

    @app.post("/api/hr/campaigns/{campaign_id}/waves")
    def add_campaign_wave(
        campaign_id: int,
        request: CampaignWaveCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: create_campaign_wave(session, actor, campaign_id, request))

    @app.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/launch")
    def launch_demo_campaign_wave(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: launch_campaign_wave(session, actor, campaign_id, wave_id))

    @app.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/edit")
    def edit_demo_campaign_wave(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: edit_campaign_wave(session, actor, campaign_id, wave_id))

    @app.post("/api/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}")
    def include_branch(
        campaign_id: int,
        org_unit_id: int,
        wave_id: int | None = None,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: include_unit_in_campaign(session, actor, campaign_id, org_unit_id, wave_id)
        )

    @app.post("/api/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}")
    def exclude_branch(
        campaign_id: int,
        org_unit_id: int,
        wave_id: int | None = None,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: exclude_unit_from_campaign(session, actor, campaign_id, org_unit_id, wave_id)
        )

    @app.put("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments")
    def update_demo_campaign_assignments(
        campaign_id: int,
        wave_id: int,
        request: CampaignAssignmentsUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: set_campaign_assignments(session, actor, campaign_id, wave_id, request)
        )

    @app.get("/api/work/hr/campaigns")
    def work_campaigns(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_campaigns(session, is_demo=False)

    @app.post("/api/work/hr/campaigns")
    def add_work_campaign(
        request: CampaignCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: create_campaign(session, actor, request, is_demo=False))

    @app.post("/api/work/hr/campaigns/{campaign_id}/waves")
    def add_work_campaign_wave(
        campaign_id: int,
        request: CampaignWaveCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: create_campaign_wave(session, actor, campaign_id, request, is_demo=False)
        )

    @app.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/launch")
    def launch_work_campaign_wave(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: launch_campaign_wave(session, actor, campaign_id, wave_id, is_demo=False)
        )

    @app.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/edit")
    def edit_work_campaign_wave(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: edit_campaign_wave(session, actor, campaign_id, wave_id, is_demo=False)
        )

    @app.post("/api/work/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}")
    def include_work_branch(
        campaign_id: int,
        org_unit_id: int,
        wave_id: int | None = None,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: include_unit_in_campaign(
                session, actor, campaign_id, org_unit_id, wave_id, is_demo=False
            )
        )

    @app.post("/api/work/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}")
    def exclude_work_branch(
        campaign_id: int,
        org_unit_id: int,
        wave_id: int | None = None,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: exclude_unit_from_campaign(
                session, actor, campaign_id, org_unit_id, wave_id, is_demo=False
            )
        )

    @app.put("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments")
    def update_work_campaign_assignments(
        campaign_id: int,
        wave_id: int,
        request: CampaignAssignmentsUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: set_campaign_assignments(
                session, actor, campaign_id, wave_id, request, is_demo=False
            )
        )

    @app.post("/api/work/hr/employees/import")
    async def import_work_employees(
        request: Request,
        filename: str = "employees.csv",
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        content = await request.body()
        return run_work_employee_import_operation(
            lambda: import_work_assignments(session, actor, filename, content)
        )

    @app.post("/api/work/hr/org-units/{org_unit_id}/staffing-lines")
    def add_work_staffing_line(
        org_unit_id: int,
        request: WorkStaffingLineCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(lambda: create_work_staffing_line(session, actor, org_unit_id, request))

    @app.post("/api/work/hr/staffing-lines/{staffing_line_id}/employees/bulk")
    def bulk_add_work_employees(
        staffing_line_id: int,
        request: BulkEmployeeCreate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_operation(
            lambda: add_employees(session, actor, staffing_line_id, request, is_demo=False)
        )

    @app.get("/api/hr/audit/recent")
    def audit_events(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return recent_audit_events(session)

    @app.get("/api/hr/analytics")
    def hr_analytics(
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_hr_analytics(session, actor)

    @app.post("/api/hr/demo-reset")
    def reset_demo(
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_demo_reset_operation(
            lambda: reset_demo_data(session, actor, settings.work_staffing_file)
        )

    @app.get("/api/work/hr/audit/recent")
    def work_audit_events(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return recent_audit_events(session, is_demo=False)

    @app.get("/api/work/hr/analytics")
    def work_hr_analytics(
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_hr_analytics(session, actor, is_demo=False)

    @app.get("/api/hr/documents")
    def documents(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_document_registry(session)

    @app.get("/api/hr/exports/profiles.json")
    def export_profiles_json(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return export_profiles(session)

    @app.get("/api/hr/exports/profiles.csv")
    def export_profiles_csv(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> Response:
        return Response(
            content=rows_to_csv(export_profiles(session), PROFILE_EXPORT_COLUMNS),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="profiles_export.csv"'},
        )

    @app.get("/api/hr/exports/campaigns.json")
    def export_campaigns_json(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return export_campaigns(session)

    @app.get("/api/hr/exports/campaigns.csv")
    def export_campaigns_csv(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> Response:
        return Response(
            content=rows_to_csv(export_campaigns(session), CAMPAIGN_EXPORT_COLUMNS),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="campaigns_export.csv"'},
        )

    @app.post("/api/hr/exports/credentials.xlsx")
    def export_credentials_xlsx(
        payload: CredentialsExportRequest,
        _: Employee = Depends(current_hr),
    ) -> Response:
        rows = [row.model_dump() for row in payload.rows]
        return Response(
            content=credentials_to_xlsx(rows),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="credentials.xlsx"'},
        )

    @app.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx")
    def issue_demo_wave_credentials_xlsx(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> Response:
        return run_export_operation(
            lambda: Response(
                content=issue_credentials_for_new_wave_participants(
                    session,
                    actor,
                    campaign_id,
                    wave_id,
                    is_demo=True,
                ),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": 'attachment; filename="credentials_new_participants.xlsx"'},
            )
        )

    @app.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx")
    def issue_work_wave_credentials_xlsx(
        campaign_id: int,
        wave_id: int,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> Response:
        return run_export_operation(
            lambda: Response(
                content=issue_credentials_for_new_wave_participants(
                    session,
                    actor,
                    campaign_id,
                    wave_id,
                    is_demo=False,
                ),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": 'attachment; filename="credentials_new_participants.xlsx"'},
            )
        )

    @app.get("/api/work/hr/documents")
    def work_documents(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return get_document_registry(session, is_demo=False)

    @app.put("/api/work/hr/documents/link")
    def update_work_document_link(
        request: WorkDocumentLinkUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_document_operation(lambda: set_work_document_link(session, actor, request))

    @app.post("/api/work/hr/documents/upload")
    async def upload_work_document_file(
        request: Request,
        filename: str,
        document_code: str,
        document_type: str,
        title: str,
        version: str = "1.0",
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        content = await request.body()
        return run_document_operation(
            lambda: upload_work_document(
                session,
                actor,
                document_storage_dir,
                filename=filename,
                document_code=document_code,
                document_type=document_type,
                title=title,
                version=version,
                content=content,
            )
        )

    @app.put("/api/work/hr/documents/{document_id}/quality")
    def update_work_document_quality(
        document_id: int,
        request: WorkDocumentQualityUpdate,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_document_operation(
            lambda: review_work_document_quality(
                session, actor, document_storage_dir, document_id, request
            )
        )

    @app.get("/api/work/hr/documents/{document_id}/source")
    def download_work_document_source(
        document_id: int,
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> Response:
        content, filename, media_type = run_document_operation(
            lambda: get_work_document_source(session, document_storage_dir, document_id)
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/work/hr/profile-reviews")
    def work_hr_profile_reviews(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_hr_review_queue(session, is_demo=False)

    @app.post("/api/work/hr/profile-reviews/bulk-return")
    def bulk_return_work_profiles_by_hr(
        request: BulkReviewReturnRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(lambda: bulk_return_to_manager(session, actor, request, is_demo=False))

    @app.post("/api/work/hr/profile-reviews/{profile_id}/accept")
    def accept_work_profile_by_hr(
        profile_id: int,
        request: ReviewVerifyRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(lambda: accept_profile(session, actor, profile_id, request, is_demo=False))

    @app.post("/api/work/hr/profile-reviews/{profile_id}/return")
    def return_work_profile_by_hr(
        profile_id: int,
        request: ReviewReturnRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(
            lambda: return_to_manager(session, actor, profile_id, request, is_demo=False)
        )

    @app.get("/api/hr/profile-reviews")
    def hr_profile_reviews(
        _: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_hr_review_queue(session)

    @app.post("/api/hr/profile-reviews/bulk-return")
    def bulk_return_profiles_by_hr(
        request: BulkReviewReturnRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(lambda: bulk_return_to_manager(session, actor, request))

    @app.post("/api/hr/profile-reviews/{profile_id}/accept")
    def accept_profile_by_hr(
        profile_id: int,
        request: ReviewVerifyRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(lambda: accept_profile(session, actor, profile_id, request))

    @app.post("/api/hr/profile-reviews/{profile_id}/return")
    def return_profile_by_hr(
        profile_id: int,
        request: ReviewReturnRequest,
        actor: Employee = Depends(current_hr),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_hr_review_operation(
            lambda: return_to_manager(session, actor, profile_id, request)
        )

    @app.get("/api/my/profiles")
    def profiles(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return get_my_profiles(session, actor)

    @app.get("/api/my/profiles/{profile_id}/export.xlsx")
    def export_personal_profile_template(
        profile_id: int,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> Response:
        template_path = PROJECT_ROOT / "Изначальные документы_история" / "Шаблон профиля должности (1).xlsx"
        content = run_export_operation(
            lambda: export_owned_profile_template(session, actor, profile_id, template_path)
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="profile_template_export.xlsx"'},
        )

    @app.put("/api/my/profiles/{profile_id}/draft")
    def update_draft(
        profile_id: int,
        request: ProfileAnswersRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_profile_operation(
            lambda: save_draft(session, actor, profile_id, request, ai_gateway.health_status().mode)
        )

    @app.post("/api/my/profiles/{profile_id}/submit")
    def submit_personal_profile(
        profile_id: int,
        request: ProfileAnswersRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_profile_operation(
            lambda: submit_profile(
                session,
                actor,
                profile_id,
                request,
                ai_gateway.health_status().mode,
            )
        )

    @app.get("/api/manager/reviews")
    def manager_reviews(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> list[dict[str, object]]:
        return run_review_operation(lambda: get_review_queue(session, actor))

    @app.get("/api/manager/overview")
    def manager_overview(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_manager_overview_operation(lambda: get_manager_overview(session, actor))

    @app.get("/api/manager/documents")
    def manager_documents(
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_document_operation(lambda: get_manager_document_registry(session, actor))

    @app.post("/api/manager/reviews/bulk-return")
    def bulk_return_profiles_for_revision(
        request: BulkReviewReturnRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_review_operation(lambda: bulk_return_for_revision(session, actor, request))

    @app.post("/api/manager/reviews/{profile_id}/take")
    def take_profile_for_review(
        profile_id: int,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_review_operation(lambda: take_for_review(session, actor, profile_id))

    @app.post("/api/manager/reviews/{profile_id}/return")
    def return_profile_for_revision(
        profile_id: int,
        request: ReviewReturnRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_review_operation(
            lambda: return_for_revision(session, actor, profile_id, request)
        )

    @app.post("/api/manager/reviews/{profile_id}/verify")
    def manager_verify_profile(
        profile_id: int,
        request: ReviewVerifyRequest,
        actor: Employee = Depends(current_actor),
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return run_review_operation(lambda: verify_profile(session, actor, profile_id, request))

    if settings.frontend_dist.exists():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")

    return app


app = create_app()
