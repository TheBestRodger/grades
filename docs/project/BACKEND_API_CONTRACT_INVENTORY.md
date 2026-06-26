# Backend API Contract Inventory

Актуальная инвентаризация backend API по router-модулям `backend/app/features/**/router.py`, `backend/app/core/health_router.py` и подключению роутеров в `backend/app/main.py`. Документ создан как read-only карта контрактов; production-код и тесты не менялись.

**Всего найдено endpoints:** 88.

**Feature-зоны:** Observability, Auth, Organization, Structure, Campaigns, Profiles, Manager reviews, HR reviews, Documents, Settings, Exports, Analytics, Audit, Notifications, Demo settings.

## Endpoint inventory

| Feature | Method | Path | Access | Request schema | Response schema | Handler | Source | Tests | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Observability | GET | `/api/health/live` | anonymous/system | — | dict | `liveness` | `backend/app/core/health_router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Observability | GET | `/api/health` | anonymous/system | — | dict | `health` | `backend/app/core/health_router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Observability | GET | `/api/health/ready` | anonymous/system | — | dict | `readiness` | `backend/app/core/health_router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Observability | GET | `/api/readiness` | anonymous/system | — | dict | `legacy_readiness` | `backend/app/core/health_router.py` | backend/tests/api/test_api_smoke_baseline.py | legacy compatibility |
| Auth | POST | `/api/auth/magic-link/request` | anonymous | MagicLinkRequest | dict[str, object] | `auth_magic_link_request` | `backend/app/features/auth/router.py` | backend/tests/api/test_auth_api_integration.py |  |
| Auth | POST | `/api/auth/magic-link/consume` | anonymous | MagicLinkConsumeRequest | dict[str, object] | `auth_magic_link_consume` | `backend/app/features/auth/router.py` | backend/tests/api/test_auth_api_integration.py |  |
| Auth | POST | `/api/auth/login` | anonymous | PasswordLoginRequest | dict[str, object] | `auth_password_login` | `backend/app/features/auth/router.py` | backend/tests/api/test_auth_api_integration.py |  |
| Auth | POST | `/api/auth/logout` | authenticated/session | Authorization header | dict[str, object] | `auth_logout` | `backend/app/features/auth/router.py` | backend/tests/api/test_auth_api_integration.py |  |
| Auth | GET | `/api/me` | authenticated/session | Authorization header | dict[str, object] | `me` | `backend/app/features/auth/router.py` | backend/tests/api/test_auth_api_integration.py |  |
| Analytics | GET | `/api/hr/analytics` | HR | — | dict[str, object] | `hr_analytics` | `backend/app/features/analytics/router.py` | backend/tests/api/test_api_smoke_baseline.py | demo/current HR scope |
| Analytics | GET | `/api/work/hr/analytics` | HR | — | dict[str, object] | `work_hr_analytics` | `backend/app/features/analytics/router.py` | не найдено | work = non-demo |
| Audit | GET | `/api/hr/audit/recent` | HR | — | list[dict[str, object]] | `audit_events` | `backend/app/features/analytics/audit_router.py` | не найдено |  |
| Audit | GET | `/api/work/hr/audit/recent` | HR | — | list[dict[str, object]] | `work_audit_events` | `backend/app/features/analytics/audit_router.py` | не найдено |  |
| Campaigns | GET | `/api/hr/campaigns` | HR | — | list[dict] | `campaigns` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns` | HR | CampaignCreate | dict | `add_campaign` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns/{campaign_id}/waves` | HR | CampaignWaveCreate | dict | `add_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns/{campaign_id}/waves/{wave_id}/launch` | HR | path params | dict | `launch_demo_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns/{campaign_id}/waves/{wave_id}/edit` | HR | path params | dict | `edit_demo_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}` | HR | path params + wave_id? query | dict | `include_branch` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | POST | `/api/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}` | HR | path params + wave_id? query | dict | `exclude_branch` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | PUT | `/api/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments` | HR | CampaignAssignmentsUpdate | dict | `update_demo_campaign_assignments` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | demo |
| Campaigns | GET | `/api/work/hr/campaigns` | HR | — | list[dict] | `work_campaigns` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns` | HR | CampaignCreate | dict | `add_work_campaign` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns/{campaign_id}/waves` | HR | CampaignWaveCreate | dict | `add_work_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/launch` | HR | path params | dict | `launch_work_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/edit` | HR | path params | dict | `edit_work_campaign_wave` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}` | HR | path params + wave_id? query | dict | `include_work_branch` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | POST | `/api/work/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}` | HR | path params + wave_id? query | dict | `exclude_work_branch` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Campaigns | PUT | `/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments` | HR | CampaignAssignmentsUpdate | dict | `update_work_campaign_assignments` | `backend/app/features/campaigns/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Documents | GET | `/api/hr/documents` | HR | — | dict | `documents` | `backend/app/features/documents/router.py` | backend/tests/api/test_api_smoke_baseline.py | demo |
| Documents | GET | `/api/work/hr/documents` | HR | — | dict | `work_documents` | `backend/app/features/documents/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Documents | PUT | `/api/work/hr/documents/link` | HR | WorkDocumentLinkUpdate | dict | `update_work_document_link` | `backend/app/features/documents/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Documents | POST | `/api/work/hr/documents/upload` | HR | raw body + query metadata | dict | `upload_work_document_file` | `backend/app/features/documents/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py | async upload |
| Documents | PUT | `/api/work/hr/documents/{document_id}/quality` | HR | WorkDocumentQualityUpdate | dict | `update_work_document_quality` | `backend/app/features/documents/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Documents | GET | `/api/work/hr/documents/{document_id}/source` | HR | path param | Response/file | `download_work_document_source` | `backend/app/features/documents/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Documents | GET | `/api/manager/documents` | manager | — | dict | `manager_documents` | `backend/app/features/documents/router.py` | не найдено | service filters access |
| Exports | GET | `/api/hr/exports/profiles.json` | HR | — | list[dict] | `export_profiles_json` | `backend/app/features/exports/router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Exports | GET | `/api/hr/exports/profiles.csv` | HR | — | Response/csv | `export_profiles_csv` | `backend/app/features/exports/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Exports | GET | `/api/hr/exports/campaigns.json` | HR | — | list[dict] | `export_campaigns_json` | `backend/app/features/exports/router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Exports | GET | `/api/hr/exports/campaigns.csv` | HR | — | Response/csv | `export_campaigns_csv` | `backend/app/features/exports/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Exports | POST | `/api/hr/exports/credentials.xlsx` | HR | CredentialsExportRequest | Response/xlsx | `export_credentials_xlsx` | `backend/app/features/exports/router.py` | не найдено |  |
| Exports | POST | `/api/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx` | HR | — | Response/xlsx | `issue_demo_wave_credentials_xlsx` | `backend/app/features/exports/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Exports | POST | `/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/credentials.xlsx` | HR | — | Response/xlsx | `issue_work_wave_credentials_xlsx` | `backend/app/features/exports/router.py` | не найдено |  |
| Exports | GET | `/api/my/profiles/{profile_id}/export.xlsx` | employee owner | path param | Response/xlsx | `export_personal_profile_template` | `backend/app/features/exports/router.py` | не найдено |  |
| HR reviews | GET | `/api/work/hr/profile-reviews` | HR | — | list[dict] | `work_hr_profile_reviews` | `backend/app/features/hr_reviews/router.py` | не найдено | work |
| HR reviews | POST | `/api/work/hr/profile-reviews/bulk-return` | HR | BulkReviewReturnRequest | dict | `bulk_return_work_profiles_by_hr` | `backend/app/features/hr_reviews/router.py` | не найдено |  |
| HR reviews | POST | `/api/work/hr/profile-reviews/{profile_id}/accept` | HR | ReviewVerifyRequest | dict | `accept_work_profile_by_hr` | `backend/app/features/hr_reviews/router.py` | не найдено |  |
| HR reviews | POST | `/api/work/hr/profile-reviews/{profile_id}/return` | HR | ReviewReturnRequest | dict | `return_work_profile_by_hr` | `backend/app/features/hr_reviews/router.py` | не найдено |  |
| HR reviews | GET | `/api/hr/profile-reviews` | HR | — | list[dict] | `hr_profile_reviews` | `backend/app/features/hr_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| HR reviews | POST | `/api/hr/profile-reviews/bulk-return` | HR | BulkReviewReturnRequest | dict | `bulk_return_profiles_by_hr` | `backend/app/features/hr_reviews/router.py` | не найдено |  |
| HR reviews | POST | `/api/hr/profile-reviews/{profile_id}/accept` | HR | ReviewVerifyRequest | dict | `accept_profile_by_hr` | `backend/app/features/hr_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| HR reviews | POST | `/api/hr/profile-reviews/{profile_id}/return` | HR | ReviewReturnRequest | dict | `return_profile_by_hr` | `backend/app/features/hr_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Manager reviews | GET | `/api/manager/reviews` | manager | — | dict/list[dict] | `manager_reviews` | `backend/app/features/manager_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Manager reviews | GET | `/api/manager/overview` | manager | — | dict/list[dict] | `manager_overview` | `backend/app/features/manager_reviews/router.py` | не найдено |  |
| Manager reviews | POST | `/api/manager/reviews/bulk-return` | manager | BulkReviewReturnRequest | dict/list[dict] | `bulk_return_profiles_for_revision` | `backend/app/features/manager_reviews/router.py` | не найдено |  |
| Manager reviews | POST | `/api/manager/reviews/{profile_id}/take` | manager | path param | dict/list[dict] | `take_profile_for_review` | `backend/app/features/manager_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Manager reviews | POST | `/api/manager/reviews/{profile_id}/return` | manager | ReviewReturnRequest | dict/list[dict] | `return_profile_for_revision` | `backend/app/features/manager_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Manager reviews | POST | `/api/manager/reviews/{profile_id}/verify` | manager | ReviewVerifyRequest | dict/list[dict] | `manager_verify_profile` | `backend/app/features/manager_reviews/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Notifications | GET | `/api/notifications` | authenticated | limit query | dict | `notifications` | `backend/app/features/notifications/router.py` | backend/tests/api/test_notifications_api_integration.py |  |
| Notifications | GET | `/api/notifications/unread-count` | authenticated | — | dict[str,int] | `notification_unread_count` | `backend/app/features/notifications/router.py` | backend/tests/api/test_notifications_api_integration.py |  |
| Notifications | POST | `/api/notifications/read-all` | authenticated | — | dict[str,int] | `read_all_notifications` | `backend/app/features/notifications/router.py` | backend/tests/api/test_notifications_api_integration.py |  |
| Notifications | POST | `/api/notifications/{notification_id}/read` | authenticated | path param | dict | `read_notification` | `backend/app/features/notifications/router.py` | backend/tests/api/test_notifications_api_integration.py |  |
| Organization | GET | `/api/organization/tree` | authenticated | — | dict | `tree` | `backend/app/features/organization/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | actor demo scope |
| Organization | GET | `/api/organization/summary` | authenticated | — | dict | `summary` | `backend/app/features/organization/router.py` | backend/tests/api/test_api_smoke_baseline.py | actor demo scope |
| Organization | GET | `/api/work/organization/tree` | authenticated | — | dict | `work_tree` | `backend/app/features/organization/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | non-demo |
| Organization | GET | `/api/work/organization/summary` | authenticated | — | dict | `work_summary` | `backend/app/features/organization/router.py` | не найдено | non-demo |
| Profiles | POST | `/api/my/profiles/{profile_id}/ai-check` | employee owner | AiProfileAnswerCheckRequest | dict/list[dict] | `ai_check_profile_answer` | `backend/app/features/profiles/router.py` | не найдено |  |
| Profiles | GET | `/api/my/profiles` | employee owner | — | dict/list[dict] | `profiles` | `backend/app/features/profiles/router.py` | backend/tests/integration/test_profile_workflow_critical.py, backend/tests/api/test_api_smoke_baseline.py |  |
| Profiles | PUT | `/api/my/profiles/{profile_id}/draft` | employee owner | ProfileAnswersRequest | dict/list[dict] | `update_draft` | `backend/app/features/profiles/router.py` | backend/tests/integration/test_profile_workflow_critical.py, backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Profiles | POST | `/api/my/profiles/{profile_id}/submit` | employee owner | ProfileAnswersRequest | dict/list[dict] | `submit_personal_profile` | `backend/app/features/profiles/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py |  |
| Settings/demo | GET | `/api/demo/users` | anonymous | — | list/dict | `demo_users` | `backend/app/features/settings/demo_router.py` | backend/tests/api/test_api_smoke_baseline.py |  |
| Settings/demo | POST | `/api/hr/demo-reset` | HR | — | list/dict | `reset_demo` | `backend/app/features/settings/demo_router.py` | не найдено |  |
| Settings | GET | `/api/hr/settings/ai` | HR | — | dict | `hr_ai_settings` | `backend/app/features/settings/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Settings | PUT | `/api/hr/settings/ai` | HR | AiConfigurationUpdate | dict | `update_hr_ai_settings` | `backend/app/features/settings/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Settings | GET | `/api/hr/settings/questionnaire` | HR | — | dict | `hr_questionnaire_settings` | `backend/app/features/settings/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Settings | PUT | `/api/hr/settings/questionnaire` | HR | QuestionnaireSettingsUpdate | dict | `update_hr_questionnaire_settings` | `backend/app/features/settings/router.py` | backend/tests/api/test_documents_settings_exports_api_integration.py |  |
| Structure | GET | `/api/hr/managers` | HR | — | dict/list[dict] | `managers` | `backend/app/features/structure/router.py` | backend/tests/api/test_api_smoke_baseline.py | demo |
| Structure | GET | `/api/work/hr/managers` | HR | — | dict/list[dict] | `work_managers` | `backend/app/features/structure/router.py` | не найдено | work |
| Structure | POST | `/api/hr/staffing-lines/{staffing_line_id}/employees/bulk` | HR | BulkEmployeeCreate | dict/list[dict] | `bulk_add_employees` | `backend/app/features/structure/router.py` | не найдено | demo |
| Structure | PUT | `/api/hr/assignments/{assignment_id}/employee` | HR | EmployeeAssignmentUpdate | dict/list[dict] | `update_demo_employee_assignment` | `backend/app/features/structure/router.py` | не найдено | demo |
| Structure | POST | `/api/hr/assignments/{assignment_id}/password/reset` | HR | path param | dict/list[dict] | `reset_demo_employee_password` | `backend/app/features/structure/router.py` | не найдено | demo |
| Structure | POST | `/api/work/hr/employees/import` | HR | raw body + filename query | dict/list[dict] | `import_work_employees` | `backend/app/features/structure/router.py` | не найдено | CSV import |
| Structure | POST | `/api/work/hr/org-units/{org_unit_id}/staffing-lines` | HR | WorkStaffingLineCreate | dict/list[dict] | `add_work_staffing_line` | `backend/app/features/structure/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py, backend/tests/api/test_documents_settings_exports_api_integration.py | work |
| Structure | POST | `/api/work/hr/staffing-lines/{staffing_line_id}/employees/bulk` | HR | BulkEmployeeCreate | dict/list[dict] | `bulk_add_work_employees` | `backend/app/features/structure/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py, backend/tests/api/test_documents_settings_exports_api_integration.py | work |
| Structure | PUT | `/api/work/hr/assignments/{assignment_id}/employee` | HR | EmployeeAssignmentUpdate | dict/list[dict] | `update_work_employee_assignment` | `backend/app/features/structure/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Structure | POST | `/api/work/hr/assignments/{assignment_id}/password/reset` | HR | path param | dict/list[dict] | `reset_work_employee_password` | `backend/app/features/structure/router.py` | не найдено | work |
| Structure | DELETE | `/api/work/hr/assignments/{assignment_id}` | HR | path param + force query | dict/list[dict] | `remove_work_assignment` | `backend/app/features/structure/router.py` | backend/tests/api/test_campaign_profile_review_api_integration.py | work |
| Structure | DELETE | `/api/work/hr/staffing-lines/{staffing_line_id}` | HR | path param + force query | dict/list[dict] | `remove_work_staffing_line` | `backend/app/features/structure/router.py` | не найдено | work |

## Gaps / вопросы

- Для части endpoints явные API-тесты не найдены: audit (`/api/*/audit/recent`), work analytics, manager documents, часть exports XLSX, work HR reviews, manager overview/bulk-return, AI-check профиля, demo-reset, часть structure demo/work операций.
- Многие handlers возвращают `dict[str, object]` / `list[dict[str, object]]` без `response_model`; точная response schema определяется service-слоем.
- Access для endpoints на `current_actor` дополнительно уточняется в service-логике: manager documents/reviews, organization scope, personal profile export.
- `/api/readiness` выглядит legacy/compatibility alias для `/api/health/ready`.
- Work/demo пары endpoints дублируют контракты, но покрытие тестами не всегда симметрично.

## Источники проверки

- Router declarations: `backend/app/features/**/router.py`, `backend/app/core/health_router.py`.
- Router registration: `backend/app/main.py`.
- Test search areas: `backend/tests/api/`, `backend/tests/integration/`, `backend/tests/service/`.
