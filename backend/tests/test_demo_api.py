import io
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import PROJECT_ROOT, Settings
from app.main import create_app
from app.models import Assignment, CampaignParticipant, Document, DocumentLink, Employee, EmployeeProfile, OrgUnit, ProfileRevision, StaffingLine


def app_for_test(tmp_path: Path, work_staffing_file: Path | None = None, app_env: str = "test"):
    settings = Settings(
        app_name="Test app",
        app_env=app_env,
        ai_mode="off",
        ai_provider="off",
        database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}",
        frontend_dist=tmp_path / "missing-dist",
        work_staffing_file=work_staffing_file,
        document_storage_dir=tmp_path / "document_storage",
    )
    return create_app(settings)


def find_user(users, role: str) -> dict:
    return next(user for user in users if user["role"] == role)


XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _xlsx_values(content: bytes, refs: set[str]) -> dict[str, str]:
    with ZipFile(io.BytesIO(content)) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", XLSX_NS):
                shared_strings.append("".join(text.text or "" for text in item.findall(".//a:t", XLSX_NS)))
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    values: dict[str, str] = {}
    for cell in sheet.findall(".//a:sheetData/a:row/a:c", XLSX_NS):
        ref = cell.attrib.get("r")
        if ref not in refs:
            continue
        inline = cell.find("a:is", XLSX_NS)
        if inline is not None:
            values[ref] = "".join(text.text or "" for text in inline.findall(".//a:t", XLSX_NS))
            continue
        raw = cell.find("a:v", XLSX_NS)
        if raw is not None:
            value = raw.text or ""
            values[ref] = shared_strings[int(value)] if cell.attrib.get("t") == "s" else value
    return values


def _import_xlsx(headers: list[str], rows: list[list[str]]) -> bytes:
    def column(index: int) -> str:
        result = ""
        value = index + 1
        while value:
            value, remainder = divmod(value - 1, 26)
            result = chr(65 + remainder) + result
        return result

    all_rows = [headers, *rows]
    sheet_rows = "".join(
        f'<row r="{row_index}">'
        + "".join(
            f'<c r="{column(col_index)}{row_index}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            for col_index, value in enumerate(row)
        )
        + "</row>"
        for row_index, row in enumerate(all_rows, start=1)
    )
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Лист1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{sheet_rows}</sheetData></worksheet>",
        )
    return buffer.getvalue()


def _work_import_position(app) -> tuple[str, str, int]:
    with app.state.database.session() as session:
        line = session.scalar(
            select(StaffingLine)
            .where(StaffingLine.is_demo.is_(False), StaffingLine.approved_fte >= 1)
            .order_by(StaffingLine.id)
        )
        assert line is not None
        return line.org_unit.path.removeprefix("WORK/"), line.title, line.org_unit_id


def test_health_reports_ai_is_off(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["ai"]["mode"] == "off"
        assert response.json()["ai"]["available"] is False


def test_magic_link_login_creates_session_and_preserves_demo_selector(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app) as client:
        with app.state.database.session() as session:
            work_hr = Employee(
                full_name="Рабочий HR",
                email="work.hr@example.local",
                system_role="hr",
                is_demo=False,
                is_active=True,
            )
            session.add(work_hr)
            session.flush()
            work_hr_id = work_hr.id

        requested = client.post(
            "/api/auth/magic-link/request",
            json={"email": "WORK.HR@example.local"},
        )
        assert requested.status_code == 200
        requested_payload = requested.json()
        assert requested_payload["delivery_mode"] == "local_link"
        assert requested_payload["login_token"]
        assert requested_payload["login_url"].startswith("/?auth_token=")

        consumed = client.post(
            "/api/auth/magic-link/consume",
            json={"token": requested_payload["login_token"]},
        )
        assert consumed.status_code == 200
        session_token = consumed.json()["token"]
        assert consumed.json()["user"]["id"] == work_hr_id
        assert consumed.json()["user"]["is_demo"] is False

        auth_headers = {"Authorization": f"Bearer {session_token}"}
        me = client.get("/api/me", headers=auth_headers)
        assert me.status_code == 200
        assert me.json()["email"] == "work.hr@example.local"

        work_summary = client.get("/api/work/organization/summary", headers=auth_headers)
        assert work_summary.status_code == 200

        reused = client.post(
            "/api/auth/magic-link/consume",
            json={"token": requested_payload["login_token"]},
        )
        assert reused.status_code == 409

        demo_hr = find_user(client.get("/api/demo/users").json(), "hr")
        demo_me = client.get("/api/me", headers={"X-Demo-User-Id": str(demo_hr["id"])})
        assert demo_me.status_code == 200
        assert demo_me.json()["is_demo"] is True

        logged_out = client.post("/api/auth/logout", headers=auth_headers)
        assert logged_out.status_code == 200
        assert logged_out.json()["revoked"] is True
        assert client.get("/api/me", headers=auth_headers).status_code == 401


def test_demo_selector_is_disabled_outside_local_demo_env(tmp_path: Path) -> None:
    app = app_for_test(tmp_path, app_env="pilot")
    with TestClient(app) as client:
        demo_users = client.get("/api/demo/users")
        assert demo_users.status_code == 200
        assert demo_users.json() == []

        demo_header = client.get("/api/me", headers={"X-Demo-User-Id": "1"})
        assert demo_header.status_code == 401

        requested = client.post(
            "/api/auth/magic-link/request",
            json={"email": "hr@demo.local"},
        )
        assert requested.status_code == 200
        assert requested.json()["delivery_mode"] == "email"
        assert requested.json()["login_token"] is None


def test_hr_can_manage_ai_configuration_without_exposing_token(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}

        default_config = client.get("/api/hr/settings/ai", headers=hr_headers)
        assert default_config.status_code == 200
        assert default_config.json()["mode"] == "default"
        assert default_config.json()["available"] is False

        forbidden = client.get("/api/hr/settings/ai", headers=employee_headers)
        assert forbidden.status_code == 403

        updated = client.put(
            "/api/hr/settings/ai",
            headers=hr_headers,
            json={
                "mode": "local",
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "model_name": "llama3.1",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["mode"] == "local"
        assert updated.json()["provider"] == "ollama"
        assert updated.json()["api_token_configured"] is False
        assert updated.json()["connection_status"] == "configured_not_connected"

        token_mode = client.put(
            "/api/hr/settings/ai",
            headers=hr_headers,
            json={
                "mode": "token",
                "provider": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model_name": "local-model",
                "api_token": "secret-test-token",
            },
        )
        assert token_mode.status_code == 200
        token_payload = token_mode.json()
        assert token_payload["api_token_configured"] is True
        assert "secret-test-token" not in json.dumps(token_payload)

        health = client.get("/api/health")
        assert health.status_code == 200
        health_ai_config = health.json()["ai"]["configuration"]
        assert health_ai_config["mode"] == "token"
        assert health_ai_config["api_token_configured"] is True
        assert "secret-test-token" not in json.dumps(health.json())


def test_hr_can_manage_open_answer_questionnaire_settings(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}

        default_settings = client.get("/api/hr/settings/questionnaire", headers=hr_headers)
        assert default_settings.status_code == 200
        purpose = next(
            item for item in default_settings.json()["questions"] if item["question_key"] == "position_purpose"
        )
        assert purpose["ai_check_enabled"] is True
        assert purpose["good_example"]

        forbidden = client.get("/api/hr/settings/questionnaire", headers=employee_headers)
        assert forbidden.status_code == 403

        updated = client.put(
            "/api/hr/settings/questionnaire",
            headers=hr_headers,
            json={
                "questions": [
                    {
                        "question_key": "position_purpose",
                        "ai_check_enabled": False,
                        "good_example": "Показывает назначение должности через результат для университета.",
                        "bad_example": "Занимаюсь задачами отдела.",
                        "requirements": "Нужны объект ответственности и последствие отсутствия должности.",
                    }
                ]
            },
        )
        assert updated.status_code == 200
        updated_purpose = next(
            item for item in updated.json()["questions"] if item["question_key"] == "position_purpose"
        )
        assert updated_purpose["ai_check_enabled"] is False
        assert updated_purpose["bad_example"] == "Занимаюсь задачами отдела."

        invalid = client.put(
            "/api/hr/settings/questionnaire",
            headers=hr_headers,
            json={"questions": [{"question_key": "education", "ai_check_enabled": True}]},
        )
        assert invalid.status_code == 422

        profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        profile_purpose = next(
            item for item in profile["questions"] if item["key"] == "position_purpose"
        )
        assert profile_purpose["ai_check_enabled"] is False
        assert profile_purpose["requirements"] == "Нужны объект ответственности и последствие отсутствия должности."


def test_local_ai_interviewer_checks_open_answer_with_structured_text(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    captured_prompts: list[str] = []

    def fake_ollama_generate(base_url: str, model_name: str, prompt: str) -> str:
        captured_prompts.append(prompt)
        assert base_url == "http://localhost:11434"
        assert model_name == "qwen2.5:27b"
        return (
            "ПОНЯТНОСТЬ: 55%\n"
            "СТАТУС: уточнить\n"
            "ПОЯСНЕНИЕ: Ответ говорит о цели, но не показывает конкретный результат для университета.\n"
            "УТОЧНЯЮЩИЙ ВОПРОС: Что именно ухудшится в работе подразделения, если этой должности не будет?\n"
        )

    app.state.ollama_generate = fake_ollama_generate
    with TestClient(app) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}

        configured = client.put(
            "/api/hr/settings/ai",
            headers=hr_headers,
            json={
                "mode": "local",
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "model_name": "qwen2.5:27b",
                "clarity_threshold": 80,
                "followup_strictness": "strict",
            },
        )
        assert configured.status_code == 200
        questionnaire = client.put(
            "/api/hr/settings/questionnaire",
            headers=hr_headers,
            json={
                "questions": [
                    {
                        "question_key": "position_purpose",
                        "ai_check_enabled": True,
                        "good_example": "Должность нужна, чтобы обеспечить измеримый результат для подразделения.",
                        "bad_example": "Должность просто нужна.",
                        "requirements": "Уточнить результат, масштаб и что ухудшится без роли.",
                    }
                ]
            },
        )
        assert questionnaire.status_code == 200

        profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        answer = "Должность нужна для организации тестирования."
        checked = client.post(
            f"/api/my/profiles/{profile['id']}/ai-check",
            headers=employee_headers,
            json={"question_key": "position_purpose", "answers": {"position_purpose": answer}},
        )
        assert checked.status_code == 200
        payload = checked.json()
        assert payload["clarity_percent"] == 55
        assert payload["clarity_threshold"] == 80
        assert payload["accepted"] is False
        assert payload["status"] == "needs_clarification"
        assert "Что именно ухудшится" in payload["followup_question"]
        assert captured_prompts
        assert "Текущий ответ: Должность нужна для организации тестирования." in captured_prompts[0]
        assert "Пример слабого ответа: Должность просто нужна." in captured_prompts[0]
        assert "Требования к ответу: Уточнить результат, масштаб" in captured_prompts[0]
        assert employee["email"] not in captured_prompts[0]
        assert employee["full_name"] not in captured_prompts[0]

        single_choice = client.post(
            f"/api/my/profiles/{profile['id']}/ai-check",
            headers=employee_headers,
            json={"question_key": "education", "answers": {"education": "Высшее"}},
        )
        assert single_choice.status_code == 422


def test_hr_sees_calculated_demo_structure_summary(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        summary = client.get("/api/organization/summary", headers=headers).json()
        tree = client.get("/api/organization/tree", headers=headers).json()

        assert summary["staffing_lines"] == 5
        assert summary["approved_fte"] == 16
        assert summary["assigned_fte"] == 12
        assert summary["vacancy_fte"] == 4
        assert tree["nodes"][0]["name"] == "Ректорат"


def test_employee_does_not_receive_branch_capacity_metrics(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        employee = find_user(client.get("/api/demo/users").json(), "employee")
        headers = {"X-Demo-User-Id": str(employee["id"])}
        summary = client.get("/api/organization/summary", headers=headers).json()
        tree = client.get("/api/organization/tree", headers=headers).json()
        position = tree["nodes"][0]["positions"][0]

        assert summary["approved_fte"] is None
        assert position["approved_fte"] is None
        assert position["assignments"][0]["employee_name"] == "Тестов Тест Тестович"


def test_department_manager_sees_only_own_subtree(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        manager = next(user for user in users if user["email"] == "head.test@demo.local")
        headers = {"X-Demo-User-Id": str(manager["id"])}
        summary = client.get("/api/organization/summary", headers=headers).json()
        tree = client.get("/api/organization/tree", headers=headers).json()

        assert summary["staffing_lines"] == 2
        assert summary["approved_fte"] == 13
        assert summary["assigned_fte"] == 9
        assert tree["nodes"][0]["name"] == "Тестовый отдел"
        assert {position["title"] for position in tree["nodes"][0]["positions"]} == {
            "Начальник тестового отдела",
            "Тестировщик",
        }


def test_hr_sees_work_structure_imported_from_staffing_file(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    with TestClient(app_for_test(tmp_path, work_staffing_file=source)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}

        summary = client.get("/api/work/organization/summary", headers=headers).json()
        assert summary["scope"] == "work"
        assert summary["employees"] == 0
        assert summary["staffing_lines"] > 4000
        assert summary["approved_fte"] > 0
        assert summary["assigned_fte"] > 0

        tree = client.get("/api/work/organization/tree", headers=headers).json()
        assert tree["scope"] == "work"
        assert tree["nodes"]
        assert tree["nodes"][0]["positions"] or tree["nodes"][0]["children"]

        documents = client.get("/api/work/hr/documents", headers=headers).json()
        assert documents["scope"] == "work"
        assert documents["documents_total"] > 0
        assert documents["coverage"]["job_instruction"]["total"] == summary["staffing_lines"]
        assert documents["coverage"]["job_instruction"]["covered"] > 0
        assert documents["coverage"]["job_instruction"]["missing"] < summary["staffing_lines"]
        assert documents["coverage"]["unit_regulation"]["covered"] > 0


def test_hr_plans_work_campaign_waves_by_staffing_structure_without_people(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    with TestClient(app_for_test(tmp_path, work_staffing_file=source)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/work/organization/tree", headers=headers).json()
        pending = list(tree["nodes"])
        branch = None
        while pending:
            candidate = pending.pop()
            if candidate["positions"]:
                branch = candidate
                break
            pending.extend(candidate["children"])
        assert branch is not None

        created = client.post(
            "/api/work/hr/campaigns",
            headers=headers,
            json={"name": "Рабочее профилирование подразделений"},
        ).json()
        assert created["scope"] == "work"
        assert created["selected_units_count"] == 0
        assert created["participants_expected"] == 0

        next_wave = client.post(
            f"/api/work/hr/campaigns/{created['id']}/waves",
            headers=headers,
            json={"name": "Волна 2: выбранные подразделения"},
        ).json()
        wave_id = next_wave["new_wave_id"]
        included = client.post(
            f"/api/work/hr/campaigns/{created['id']}/include-unit/{branch['id']}?wave_id={wave_id}",
            headers=headers,
        ).json()
        assert included["scope"] == "work"
        assert included["active_wave_id"] == wave_id
        assert included["selected_units_count"] >= 1
        assert included["selected_staffing_lines"] >= len(branch["positions"])
        assert included["selected_approved_fte"] > 0
        assert included["participants_expected"] == 0
        assert branch["id"] in included["selected_org_unit_ids"]

        excluded = client.post(
            f"/api/work/hr/campaigns/{created['id']}/exclude-unit/{branch['id']}?wave_id={wave_id}",
            headers=headers,
        ).json()
        assert excluded["selected_units_count"] == 0
        assert excluded["selected_staffing_lines"] == 0

        work_campaigns = client.get("/api/work/hr/campaigns", headers=headers).json()
        demo_campaigns = client.get("/api/hr/campaigns", headers=headers).json()
        assert any(campaign["id"] == created["id"] for campaign in work_campaigns)
        assert all(campaign["id"] != created["id"] for campaign in demo_campaigns)
        audit = client.get("/api/work/hr/audit/recent", headers=headers).json()
        assert audit[0]["action"] == "campaign.branch_excluded"
        assert audit[0]["details"]["scope"] == "work"
        assert all(event["details"].get("scope") == "work" for event in audit)
        demo_audit = client.get("/api/hr/audit/recent", headers=headers).json()
        assert all(event["details"].get("scope", "demo") == "demo" for event in demo_audit)


def test_hr_assigns_and_removes_imported_work_document_link_with_audit(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    with TestClient(app_for_test(tmp_path, work_staffing_file=source)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        registry = client.get("/api/work/hr/documents", headers=headers).json()
        document = next(
            item for item in registry["documents"] if item["document_type"] == "job_instruction"
        )
        gap = registry["coverage"]["job_instruction"]["gaps"][0]
        line_id = gap["target_id"]

        assigned = client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": line_id,
                "document_type": "job_instruction",
                "document_id": document["id"],
            },
        )
        assert assigned.status_code == 200
        assigned_row = next(
            row for row in assigned.json()["position_matrix"] if row["staffing_line_id"] == line_id
        )
        assert assigned_row["job_instruction"]["covered"] is True
        assert assigned_row["job_instruction"]["documents"][0]["document_id"] == document["id"]
        assert assigned_row["job_instruction"]["documents"][0]["link_status"] == "confirmed"

        removed = client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": line_id,
                "document_type": "job_instruction",
                "document_id": None,
            },
        )
        assert removed.status_code == 200
        removed_row = next(
            row for row in removed.json()["position_matrix"] if row["staffing_line_id"] == line_id
        )
        assert removed_row["job_instruction"]["covered"] is False
        audit = client.get("/api/work/hr/audit/recent", headers=headers).json()
        assert audit[0]["action"] == "document.link_updated"
        assert audit[0]["details"]["document_type"] == "job_instruction"
        assert audit[0]["details"]["after_document_codes"] == []
        assert audit[1]["details"]["after_document_codes"] == [document["document_code"]]


def test_hr_uploads_reviews_and_links_new_work_document_with_original_and_audit(
    tmp_path: Path,
) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    with TestClient(app_for_test(tmp_path, work_staffing_file=source)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        manager = find_user(users, "manager")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        content = "Обязанности специалиста\nПроверенный исходный текст.".encode("utf-8")
        params = {
            "filename": "new_instruction.txt",
            "document_code": "WORK-DI-UPLOADED-001",
            "document_type": "job_instruction",
            "title": "Новая должностная инструкция",
            "version": "1.0",
        }

        forbidden = client.post(
            "/api/work/hr/documents/upload",
            params=params,
            headers={"X-Demo-User-Id": str(manager["id"])},
            content=content,
        )
        assert forbidden.status_code == 403

        uploaded = client.post(
            "/api/work/hr/documents/upload",
            params=params,
            headers=headers,
            content=content,
        )
        assert uploaded.status_code == 200
        document = next(
            item
            for item in uploaded.json()["documents"]
            if item["document_code"] == "WORK-DI-UPLOADED-001"
        )
        assert document["ocr_quality_status"] == "pending"
        assert document["has_stored_original"] is True
        assert document["content_text"].startswith("Обязанности специалиста")
        gap = uploaded.json()["coverage"]["job_instruction"]["gaps"][0]

        before_review = client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": gap["target_id"],
                "document_type": "job_instruction",
                "document_id": document["id"],
            },
        )
        assert before_review.status_code == 409

        reviewed = client.put(
            f"/api/work/hr/documents/{document['id']}/quality",
            headers=headers,
            json={
                "ocr_quality_status": "good",
                "extracted_text": "Обязанности специалиста\nТекст проверен HR.",
            },
        )
        assert reviewed.status_code == 200
        reviewed_document = next(
            item for item in reviewed.json()["documents"] if item["id"] == document["id"]
        )
        assert reviewed_document["ocr_quality_status"] == "good"

        assigned = client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": gap["target_id"],
                "document_type": "job_instruction",
                "document_id": document["id"],
            },
        )
        assert assigned.status_code == 200
        source_response = client.get(
            f"/api/work/hr/documents/{document['id']}/source", headers=headers
        )
        assert source_response.status_code == 200
        assert source_response.content == content

        audit = client.get("/api/work/hr/audit/recent", headers=headers).json()
        actions = [event["action"] for event in audit[:3]]
        assert actions == [
            "document.link_updated",
            "document.quality_reviewed",
            "document.uploaded",
        ]
        assert audit[1]["details"]["after_quality_status"] == "good"
        assert audit[2]["details"]["checksum_sha256"]


def test_hr_imports_work_assignments_and_selects_people_for_campaign(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    app = app_for_test(tmp_path, work_staffing_file=source)
    with TestClient(app) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        unit_path, title, unit_id = _work_import_position(app)
        payload = (
            "ID назначения;ID сотрудника;ФИО;Email;Путь подразделения;Должность;Ставка;"
            "ID назначения руководителя;Роль\n"
            f"WORK-A-001;WORK-E-001;Рабочий Руководитель;work.manager@example.test;{unit_path};{title};0,1;;manager\n"
            f"WORK-A-002;WORK-E-002;Рабочий Сотрудник;work.employee@example.test;{unit_path};{title};0,1;WORK-A-001;employee\n"
        ).encode("utf-8")
        imported = client.post(
            "/api/work/hr/employees/import?filename=%D0%A1%D0%BE%D1%82%D1%80%D1%83%D0%B4%D0%BD%D0%B8%D0%BA%D0%B8.csv",
            headers=headers,
            content=payload,
        )
        assert imported.status_code == 200
        assert imported.json()["filename"] == "Сотрудники.csv"
        assert imported.json()["created_employees"] == 2
        assert imported.json()["created_assignments"] == 2
        assert client.get("/api/work/organization/summary", headers=headers).json()["employees"] == 2
        manager = find_user(client.get("/api/demo/users").json(), "manager")
        forbidden = client.post(
            "/api/work/hr/employees/import?filename=employees.csv",
            headers={"X-Demo-User-Id": str(manager["id"])},
            content=payload,
        )
        assert forbidden.status_code == 403

        with app.state.database.session() as session:
            employee_assignment = session.scalar(
                select(Assignment).where(Assignment.external_assignment_id == "WORK-A-002")
            )
            assert employee_assignment is not None
            employee_assignment_id = employee_assignment.id

        campaign = client.post(
            "/api/work/hr/campaigns",
            headers=headers,
            json={"name": "Рабочая выборочная кампания"},
        ).json()
        wave_id = campaign["active_wave_id"]
        included_person = client.put(
            f"/api/work/hr/campaigns/{campaign['id']}/waves/{wave_id}/assignments",
            headers=headers,
            json={"assignment_ids": [employee_assignment_id], "action": "include"},
        ).json()
        assert included_person["participants_expected"] == 1
        assert included_person["participant_assignment_ids"] == [employee_assignment_id]

        included_branch = client.post(
            f"/api/work/hr/campaigns/{campaign['id']}/include-unit/{unit_id}?wave_id={wave_id}",
            headers=headers,
        ).json()
        assert included_branch["participants_expected"] == 2
        assert included_branch["new_participants"] == 1

        excluded_person = client.put(
            f"/api/work/hr/campaigns/{campaign['id']}/waves/{wave_id}/assignments",
            headers=headers,
            json={"assignment_ids": [employee_assignment_id], "action": "exclude"},
        ).json()
        assert excluded_person["participants_expected"] == 1
        assert employee_assignment_id not in excluded_person["participant_assignment_ids"]

        audit = client.get("/api/work/hr/audit/recent", headers=headers).json()
        assert audit[0]["action"] == "campaign.assignments_excluded"
        assert any(event["action"] == "employees.work_imported" for event in audit)
        assert all(event["details"]["scope"] == "work" for event in audit)


def test_hr_imports_work_assignments_from_xlsx(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    app = app_for_test(tmp_path, work_staffing_file=source)
    with TestClient(app) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        unit_path, title, _ = _work_import_position(app)
        content = _import_xlsx(
            [
                "ID назначения",
                "ID сотрудника",
                "ФИО",
                "Email",
                "Путь подразделения",
                "Должность",
                "Ставка",
                "ID назначения руководителя",
                "Роль",
            ],
            [
                [
                    "XLSX-A-001",
                    "XLSX-E-001",
                    "Импортированный Сотрудник",
                    "xlsx.employee@example.test",
                    unit_path,
                    title,
                    "0.1",
                    "",
                    "employee",
                ]
            ],
        )
        response = client.post(
            "/api/work/hr/employees/import?filename=employees.xlsx",
            headers=headers,
            content=content,
        )
        assert response.status_code == 200
        assert response.json()["filename"] == "employees.xlsx"
        assert response.json()["created_assignments"] == 1


def test_hr_creates_work_staffing_line_with_people_and_manager_assignment(
    tmp_path: Path,
) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    app = app_for_test(tmp_path, work_staffing_file=source)
    with TestClient(app) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        _, _, unit_id = _work_import_position(app)

        manager_line = client.post(
            f"/api/work/hr/org-units/{unit_id}/staffing-lines",
            headers=headers,
            json={
                "title": "Руководитель пилотной группы",
                "approved_fte": 1,
                "employees": [
                    {
                        "full_name": "Рабочий Руководитель Пилота",
                        "email": "pilot.manager@example.local",
                        "fte": 1,
                        "system_role": "manager",
                    }
                ],
            },
        )
        assert manager_line.status_code == 200
        manager_assignment_id = manager_line.json()["added"][0]["assignment_id"]
        assert manager_line.json()["scope"] == "work"

        managers = client.get("/api/work/hr/managers", headers=headers).json()
        assert any(item["assignment_id"] == manager_assignment_id for item in managers)

        employee_line = client.post(
            f"/api/work/hr/org-units/{unit_id}/staffing-lines",
            headers=headers,
            json={
                "title": "Специалист пилотной группы",
                "approved_fte": 2,
                "employees": [
                    {
                        "full_name": "Рабочий Специалист Пилота",
                        "email": "pilot.specialist@example.local",
                        "fte": 1,
                        "system_role": "employee",
                        "manager_assignment_id": manager_assignment_id,
                    }
                ],
            },
        )
        assert employee_line.status_code == 200
        assert employee_line.json()["remaining_fte"] == 1
        assert employee_line.json()["added"][0]["manager_assignment_id"] == manager_assignment_id

        work_tree = client.get("/api/work/organization/tree", headers=headers).json()
        created_position = _staffing_line(work_tree, "Специалист пилотной группы")
        assert created_position["approved_fte"] == 2
        assert created_position["assigned_fte"] == 1
        assert created_position["vacancy_fte"] == 1
        assert created_position["assignments"][0]["employee_name"] == "Рабочий Специалист Пилота"

        duplicate = client.post(
            f"/api/work/hr/org-units/{unit_id}/staffing-lines",
            headers=headers,
            json={"title": "Специалист пилотной группы", "approved_fte": 1, "employees": []},
        )
        assert duplicate.status_code == 409

        audit = client.get("/api/work/hr/audit/recent", headers=headers).json()
        assert audit[0]["action"] == "staffing_line.work_created"
        assert audit[0]["details"]["scope"] == "work"
        assert audit[0]["details"]["staffing_title"] == "Специалист пилотной группы"


def test_hr_resets_only_demo_scope_and_keeps_work_data(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    app = app_for_test(tmp_path, work_staffing_file=source)
    with TestClient(app) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        _, _, unit_id = _work_import_position(app)

        work_line = client.post(
            f"/api/work/hr/org-units/{unit_id}/staffing-lines",
            headers=headers,
            json={
                "title": "Строка до сброса демо",
                "approved_fte": 1,
                "employees": [
                    {
                        "full_name": "Рабочий До Сброса",
                        "email": "work.before.reset@example.local",
                        "fte": 1,
                        "system_role": "employee",
                    }
                ],
            },
        )
        assert work_line.status_code == 200
        work_summary_before = client.get("/api/work/organization/summary", headers=headers).json()

        demo_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        client.put(
            f"/api/my/profiles/{demo_profile['id']}/draft",
            headers=employee_headers,
            json={"answers": {"position_name": "Испорченный демо-черновик"}},
        )
        demo_summary_before = client.get("/api/organization/summary", headers=headers).json()
        assert demo_summary_before["employees"] == 12

        reset = client.post("/api/hr/demo-reset", headers=headers)
        assert reset.status_code == 200
        assert reset.json()["scope"] == "demo"
        assert reset.json()["work_unchanged"] is True
        assert reset.json()["before"]["work"] == reset.json()["after"]["work"]

        users_after = client.get("/api/demo/users").json()
        hr_after = find_user(users_after, "hr")
        headers_after = {"X-Demo-User-Id": str(hr_after["id"])}
        work_summary_after = client.get("/api/work/organization/summary", headers=headers_after).json()
        assert work_summary_after == work_summary_before
        work_tree = client.get("/api/work/organization/tree", headers=headers_after).json()
        assert _staffing_line(work_tree, "Строка до сброса демо")["assignments"][0]["employee_name"] == "Рабочий До Сброса"

        employee_after = find_user(users_after, "employee")
        profile_after = client.get(
            "/api/my/profiles",
            headers={"X-Demo-User-Id": str(employee_after["id"])},
        ).json()[0]
        assert profile_after["answers"]["position_name"] == "Тестировщик"
        demo_summary_after = client.get("/api/organization/summary", headers=headers_after).json()
        assert demo_summary_after["employees"] == demo_summary_before["employees"]
        audit = client.get("/api/hr/audit/recent", headers=headers_after).json()
        assert audit[0]["action"] == "demo.reset_completed"
        assert audit[0]["details"]["work_unchanged"] is True

        manager = find_user(users_after, "manager")
        forbidden = client.post(
            "/api/hr/demo-reset",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert forbidden.status_code == 403


def _staffing_line(tree: dict, title: str) -> dict:
    pending = list(tree["nodes"])
    while pending:
        node = pending.pop()
        for position in node["positions"]:
            if position["title"] == title:
                return position
        pending.extend(node["children"])
    raise AssertionError(f"Position not found: {title}")


def _org_unit(tree: dict, name: str) -> dict:
    pending = list(tree["nodes"])
    while pending:
        node = pending.pop()
        if node["name"] == name:
            return node
        pending.extend(node["children"])
    raise AssertionError(f"Org unit not found: {name}")


def test_hr_adds_multiple_employees_to_available_position_and_writes_audit(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=headers).json()
        tester_line = _staffing_line(tree, "Тестировщик")
        managers = client.get("/api/hr/managers", headers=headers).json()
        head = next(item for item in managers if item["position_title"] == "Начальник тестового отдела")

        response = client.post(
            f"/api/hr/staffing-lines/{tester_line['id']}/employees/bulk",
            headers=headers,
            json={
                "employees": [
                    {
                        "full_name": "Тестов Пятый Тестович",
                        "email": "tester5@demo.local",
                        "fte": 1,
                        "manager_assignment_id": head["assignment_id"],
                    },
                    {
                        "full_name": "Тестова Шестая Тестовна",
                        "email": "tester6@demo.local",
                        "fte": 1,
                        "manager_assignment_id": head["assignment_id"],
                    },
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["remaining_fte"] == 2

        summary = client.get("/api/organization/summary", headers=headers).json()
        audit = client.get("/api/hr/audit/recent", headers=headers).json()
        assert summary["employees"] == 14
        assert summary["assigned_fte"] == 14
        assert audit[0]["action"] == "employees.bulk_added"
        assert audit[0]["details"]["count"] == 2


def test_hr_cannot_add_more_than_remaining_fte(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=headers).json()
        tester_line = _staffing_line(tree, "Тестировщик")
        manager = next(
            item
            for item in client.get("/api/hr/managers", headers=headers).json()
            if item["position_title"] == "Начальник тестового отдела"
        )
        response = client.post(
            f"/api/hr/staffing-lines/{tester_line['id']}/employees/bulk",
            headers=headers,
            json={
                "employees": [
                    {
                        "full_name": "Лишний Тестовый Сотрудник",
                        "email": "overflow@demo.local",
                        "fte": 8,
                        "manager_assignment_id": manager["assignment_id"],
                    }
                ]
            },
        )
        assert response.status_code == 409
        assert "Недостаточно свободных ставок" in response.json()["detail"]


def test_hr_creates_campaign_and_includes_unit_branch_once(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=headers).json()
        department = tree["nodes"][0]["children"][0]["children"][0]["children"][0]

        campaign = client.post(
            "/api/hr/campaigns",
            headers=headers,
            json={"name": "Демо-волна тестового отдела"},
        ).json()
        assert campaign["active_wave_name"] == "Волна 1"
        assert len(campaign["waves"]) == 1
        included = client.post(
            f"/api/hr/campaigns/{campaign['id']}/include-unit/{department['id']}",
            headers=headers,
        ).json()
        included_again = client.post(
            f"/api/hr/campaigns/{campaign['id']}/include-unit/{department['id']}",
            headers=headers,
        ).json()

        assert included["new_participants"] == 9
        assert included["participants_expected"] == 9
        assert len(included["participant_assignment_ids"]) == 9
        assert included["waves"][0]["participants_expected"] == 9
        assert included_again["new_participants"] == 0
        assert included_again["participants_expected"] == 9


def test_campaign_has_waves_for_staged_branch_profiling(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=headers).json()
        direction = _org_unit(tree, "Тестовое направление")
        department = _org_unit(tree, "Тестовый отдел")

        campaign = client.post(
            "/api/hr/campaigns",
            headers=headers,
            json={"name": "Профилирование по волнам"},
        ).json()
        first_wave_id = campaign["active_wave_id"]
        first = client.post(
            f"/api/hr/campaigns/{campaign['id']}/include-unit/{department['id']}?wave_id={first_wave_id}",
            headers=headers,
        ).json()
        assert first["included_wave_name"] == "Волна 1"
        assert first["waves"][0]["participants_expected"] == 9

        second = client.post(
            f"/api/hr/campaigns/{campaign['id']}/waves",
            headers=headers,
            json={"name": "Волна 2: тестовое направление"},
        ).json()
        second_wave_id = second["new_wave_id"]
        included = client.post(
            f"/api/hr/campaigns/{campaign['id']}/include-unit/{direction['id']}?wave_id={second_wave_id}",
            headers=headers,
        ).json()

        assert included["included_wave_id"] == second_wave_id
        assert included["participants_expected"] == 1
        assert included["total_participants_expected"] == 10
        assert [wave["participants_expected"] for wave in included["waves"]] == [9, 1]


def test_hr_can_exclude_unit_branch_from_campaign_without_deleting_history(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=headers).json()
        department = tree["nodes"][0]["children"][0]["children"][0]["children"][0]
        campaign = client.post(
            "/api/hr/campaigns",
            headers=headers,
            json={"name": "Ветка с возможностью выключения"},
        ).json()
        client.post(
            f"/api/hr/campaigns/{campaign['id']}/include-unit/{department['id']}",
            headers=headers,
        )

        excluded = client.post(
            f"/api/hr/campaigns/{campaign['id']}/exclude-unit/{department['id']}",
            headers=headers,
        )
        assert excluded.status_code == 200
        payload = excluded.json()
        assert payload["excluded_participants"] == 9
        assert payload["participants_expected"] == 0
        assert payload["participant_assignment_ids"] == []

        audit = client.get("/api/hr/audit/recent", headers=headers).json()
        assert audit[0]["action"] == "campaign.branch_excluded"


def test_manager_cannot_use_hr_operations(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        manager = find_user(client.get("/api/demo/users").json(), "manager")
        headers = {"X-Demo-User-Id": str(manager["id"])}
        response = client.post(
            "/api/hr/campaigns",
            headers=headers,
            json={"name": "Нельзя создать"},
        )
        assert response.status_code == 403


def test_hr_document_registry_reports_demo_document_coverage(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        manager = find_user(users, "manager")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}

        response = client.get("/api/hr/documents", headers=hr_headers)
        assert response.status_code == 200
        registry = response.json()

        assert registry["documents_total"] == 4
        assert registry["confirmed_documents"] == 4
        assert registry["coverage"]["job_instruction"]["total"] == 5
        assert registry["coverage"]["job_instruction"]["covered"] == 2
        assert registry["coverage"]["job_instruction"]["missing"] == 3
        assert registry["coverage"]["unit_regulation"]["total"] == 4
        assert registry["coverage"]["unit_regulation"]["covered"] == 1
        assert registry["coverage"]["professional_standard"]["total"] == 5
        assert registry["coverage"]["professional_standard"]["covered"] == 1
        tester_matrix = next(
            item for item in registry["position_matrix"] if item["position_title"] == "Тестировщик"
        )
        assert tester_matrix["covered_count"] == 3
        assert tester_matrix["job_instruction"]["covered"] is True
        assert tester_matrix["unit_regulation"]["covered"] is True
        assert tester_matrix["professional_standard"]["covered"] is True
        rector_matrix = next(
            item for item in registry["position_matrix"] if item["position_title"] == "Ректор"
        )
        assert rector_matrix["covered_count"] == 0
        assert {item["document_code"] for item in registry["documents"]} == {
            "ДИ-ДЕМО-НАЧ-ТО-001",
            "ДИ-ДЕМО-ТЕСТ-001",
            "ПОЛ-ДЕМО-ТО-001",
            "ПС-ДЕМО-ТЕСТ-001",
        }
        assert all(item["is_demo"] for item in registry["documents"])

        forbidden = client.get(
            "/api/hr/documents",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert forbidden.status_code == 403


def test_manager_document_registry_is_read_only_and_limited_to_subtree(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app) as client:
        users = client.get("/api/demo/users").json()
        manager = next(user for user in users if user["email"] == "head.test@demo.local")
        employee = find_user(users, "employee")

        with app.state.database.session() as session:
            rector_line = session.scalar(
                select(StaffingLine)
                .join(StaffingLine.org_unit)
                .where(StaffingLine.title == "Ректор", OrgUnit.is_demo.is_(True))
            )
            assert rector_line is not None
            outside_document = Document(
                document_code="ДИ-ДЕМО-РЕКТОР-СКРЫТА",
                document_type="job_instruction",
                title="Должностная инструкция ректора вне зоны отдела",
                version="1.0-demo",
                document_status="confirmed",
                ocr_quality_status="manual_demo",
                is_demo=True,
            )
            session.add(outside_document)
            session.flush()
            session.add(
                DocumentLink(
                    document_id=outside_document.id,
                    target_type="staffing_line",
                    target_id=rector_line.id,
                    link_status="confirmed",
                    is_demo=True,
                )
            )

        response = client.get(
            "/api/manager/documents",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert response.status_code == 200
        registry = response.json()
        assert registry["documents_total"] == 4
        assert "доступной зоне руководителя" in registry["note"]
        assert registry["coverage"]["job_instruction"]["total"] == 2
        assert registry["coverage"]["job_instruction"]["covered"] == 2
        assert registry["coverage"]["unit_regulation"]["total"] == 1
        assert registry["coverage"]["unit_regulation"]["covered"] == 1
        assert {row["position_title"] for row in registry["position_matrix"]} == {
            "Начальник тестового отдела",
            "Тестировщик",
        }
        assert "ДИ-ДЕМО-РЕКТОР-СКРЫТА" not in {
            item["document_code"] for item in registry["documents"]
        }

        forbidden = client.get(
            "/api/manager/documents",
            headers={"X-Demo-User-Id": str(employee["id"])},
        )
        assert forbidden.status_code == 403


def test_hr_exports_demo_profiles_and_campaigns(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}

        profiles_json = client.get("/api/hr/exports/profiles.json", headers=hr_headers)
        profiles_csv = client.get("/api/hr/exports/profiles.csv", headers=hr_headers)
        campaigns_json = client.get("/api/hr/exports/campaigns.json", headers=hr_headers)
        campaigns_csv = client.get("/api/hr/exports/campaigns.csv", headers=hr_headers)

        assert profiles_json.status_code == 200
        assert profiles_csv.status_code == 200
        assert campaigns_json.status_code == 200
        assert campaigns_csv.status_code == 200
        profile_rows = profiles_json.json()
        assert len(profile_rows) == 8
        assert any(row["employee_name"] == "Тестов Восьмой Аномальный" for row in profile_rows)
        assert {row["assistant_mode"] for row in profile_rows} == {"off"}
        assert "campaign_name;wave_name;employee_name" in profiles_csv.text

        campaign_rows = campaigns_json.json()
        showcase = next(row for row in campaign_rows if row["campaign_name"] == "Демо-сценарий тепловой карты")
        assert showcase["participants_expected"] == 8
        assert "Демо-сценарий тепловой карты" in campaigns_csv.text

        forbidden = client.get(
            "/api/hr/exports/profiles.json",
            headers={"X-Demo-User-Id": str(employee["id"])},
        )
        assert forbidden.status_code == 403


def test_hr_analytics_dashboard_calculates_demo_funnel_and_document_coverage(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        employee = find_user(users, "employee")
        response = client.get(
            "/api/hr/analytics",
            headers={"X-Demo-User-Id": str(hr["id"])},
        )
        assert response.status_code == 200
        analytics = response.json()
        assert analytics["scope"] == "demo"
        assert analytics["profiles_expected"] == 8
        assert analytics["accepted_profiles"] == 6
        assert analytics["returned_profiles"] == 2
        assert analytics["revision_count"] == 8
        status_counts = {row["status"]: row["count"] for row in analytics["funnel"]}
        assert status_counts["hr_accepted"] == 6
        assert status_counts["returned_for_revision"] == 1
        assert status_counts["returned_by_hr"] == 1
        assert analytics["units"][0]["unit_name"] == "Тестовый отдел"
        assert analytics["documents"]["coverage"]["job_instruction"]["covered"] > 0

        forbidden = client.get(
            "/api/hr/analytics",
            headers={"X-Demo-User-Id": str(employee["id"])},
        )
        assert forbidden.status_code == 403


def test_work_hr_analytics_excludes_demo_profiles_and_uses_work_documents(tmp_path: Path) -> None:
    source = (
        PROJECT_ROOT
        / "Изначальные документы_история"
        / "ШР по уровням на 15.05.26_размечено.xlsx"
    )
    with TestClient(app_for_test(tmp_path, work_staffing_file=source)) as client:
        hr = find_user(client.get("/api/demo/users").json(), "hr")
        headers = {"X-Demo-User-Id": str(hr["id"])}
        demo = client.get("/api/hr/analytics", headers=headers).json()
        work = client.get("/api/work/hr/analytics", headers=headers).json()
        assert demo["profiles_expected"] == 8
        assert work["scope"] == "work"
        assert work["profiles_expected"] == 0
        assert work["accepted_profiles"] == 0
        assert work["structure"]["staffing_lines"] > 4000
        assert work["documents"]["documents_total"] > 0
        assert work["documents"]["coverage"]["job_instruction"]["covered"] > 0


def _activate_department_campaign(client: TestClient) -> tuple[dict, dict]:
    users = client.get("/api/demo/users").json()
    hr = find_user(users, "hr")
    employee = next(user for user in users if user["email"] == "tester@demo.local")
    hr_headers = {"X-Demo-User-Id": str(hr["id"])}
    tree = client.get("/api/organization/tree", headers=hr_headers).json()
    department = tree["nodes"][0]["children"][0]["children"][0]["children"][0]
    campaign = client.post(
        "/api/hr/campaigns",
        headers=hr_headers,
        json={"name": "Анкеты тестового отдела"},
    ).json()
    client.post(
        f"/api/hr/campaigns/{campaign['id']}/include-unit/{department['id']}",
        headers=hr_headers,
    )
    return hr, employee


def test_manager_overview_groups_subtree_profiles_by_signal(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        manager = next(user for user in users if user["email"] == "head.test@demo.local")

        response = client.get(
            "/api/manager/overview",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert response.status_code == 200
        overview = response.json()
        assert overview["total_profiles"] == 8
        assert overview["risk_counts"]["normal"] == 6
        assert overview["risk_counts"]["attention"] == 1
        assert overview["risk_counts"]["critical"] == 1
        assert overview["units"][0]["unit_name"] == "Тестовый отдел"
        assert overview["units"][0]["quality_score"] == 0.75
        assert overview["units"][0]["quality_percent"] == 75
        assert overview["units"][0]["heat_level"] == "yellow"
        assert overview["units"][0]["risk_counts"]["normal"] == 6
        assert overview["units"][0]["risk_counts"]["attention"] == 1
        assert overview["units"][0]["risk_counts"]["critical"] == 1
        assert any(
            profile["employee_name"] == "Тестов Восьмой Аномальный"
            and profile["risk_level"] == "critical"
            and profile["document_signal"]["risk_level"] == "critical"
            for profile in overview["units"][0]["profiles"]
        )
        normal_profile = next(
            profile
            for profile in overview["units"][0]["profiles"]
            if profile["employee_name"] == "Тестов Тест Тестович"
        )
        assert normal_profile["document_signal"]["checks"][0]["risk_level"] == "normal"
        assert normal_profile["document_signal"]["checks"][0]["matched_terms"]

        employee = next(user for user in users if user["email"] == "tester@demo.local")
        forbidden = client.get(
            "/api/manager/overview",
            headers={"X-Demo-User-Id": str(employee["id"])},
        )
        assert forbidden.status_code == 403


def test_manager_overview_flags_profile_document_semantic_anomaly(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app) as client:
        users = client.get("/api/demo/users").json()
        manager = next(user for user in users if user["email"] == "head.test@demo.local")
        with app.state.database.session() as session:
            profile = session.scalar(
                select(EmployeeProfile)
                .join(EmployeeProfile.participant)
                .join(CampaignParticipant.assignment)
                .join(Assignment.employee)
                .where(Employee.email == "tester@demo.local")
            )
            assert profile is not None
            revision = session.scalar(
                select(ProfileRevision)
                .where(ProfileRevision.employee_profile_id == profile.id)
                .order_by(ProfileRevision.revision_no.desc())
                .limit(1)
            )
            assert revision is not None
            answers = _complete_answers()
            answers["position_purpose"] = "Организация питания и хозяйственного оформления стенда."
            answers["duties_results"] = json.dumps(
                [
                    ["Готовит обеды", "Участники вовремя возвращаются к демонстрации."],
                    ["Оформляет кабинет", "Стенд выглядит аккуратно."],
                    ["Закупает расходные материалы", "Мероприятие проходит без пауз."],
                ],
                ensure_ascii=False,
            )
            answers["methods_knowledge"] = "Кейтеринг, хозяйственная подготовка, складской учет."
            answers["technology_knowledge"] = "Кассовые приложения и таблицы закупок."
            revision.answers_json = json.dumps(answers, ensure_ascii=False)

        overview = client.get(
            "/api/manager/overview",
            headers={"X-Demo-User-Id": str(manager["id"])},
        ).json()
        profile_signal = next(
            profile
            for profile in overview["units"][0]["profiles"]
            if profile["employee_name"] == "Тестов Тест Тестович"
        )
        assert profile_signal["workflow_risk_level"] == "normal"
        assert profile_signal["risk_level"] == "critical"
        assert profile_signal["risk_reason"].startswith("Документы:")
        assert profile_signal["document_signal"]["risk_level"] == "critical"
        assert any(
            check["document_type"] == "job_instruction" and check["risk_level"] == "critical"
            for check in profile_signal["document_signal"]["checks"]
        )


def _complete_answers() -> dict[str, str]:
    duties = json.dumps(
        [
            ["Проверяет тестовые сценарии", "Критичные дефекты выявляются до релиза."],
            ["Фиксирует дефекты", "Команда разработки получает воспроизводимые описания."],
            ["Готовит отчет о проверке", "Руководитель видит готовность тестового выпуска."],
        ],
        ensure_ascii=False,
    )
    external = json.dumps([["Тестовый подрядчик", "Тестовая среда", "Согласована готовность стенда."]], ensure_ascii=False)
    internal = json.dumps([["Разработчики", "Дефекты", "Исправления проверены до выпуска."]], ensure_ascii=False)
    experience = json.dumps(
        [
            ["Профессиональный", "2", "Тестирование информационных систем."],
            ["Управленческий", "0", "Не требуется для должности."],
        ],
        ensure_ascii=False,
    )
    return {
        "position_name": "Тестировщик",
        "org_structure": "Ректорат / Проректор по тестовым делам / Тестовое направление / Тестовый отдел",
        "administrative_manager": "Начальник тестового отдела / Тестовый отдел",
        "functional_manager": "Совпадает.",
        "direct_admin_reports": "Нет.",
        "total_reports": "0",
        "functional_reports": "Нет.",
        "completion_date": "26.05.2026",
        "position_purpose": "Помогает выпускать изменения без критичных дефектов.",
        "duties_results": duties,
        "income_responsibility": "Не применимо.",
        "expense_budget_type": "Не применимо.",
        "expense_budget_volume": "Не применимо.",
        "expense_budget_management": "Не применимо.",
        "task_typicality": "Типовые с вариациями",
        "complex_task_example": "При ограниченном времени выбирает критичные сценарии проверки и объясняет риск руководителю.",
        "external_interactions": external,
        "internal_interactions": internal,
        "government_interactions": "Не применимо.",
        "independent_decisions": "Самостоятельно оформляет дефекты и выбирает порядок проверки типовых сценариев.",
        "approval_decisions": "Выпуск и приоритеты согласует руководитель.",
        "education": "Высшее (бакалавр / специалист / магистр)",
        "specialization": "Информационные системы или смежное направление.",
        "certification": "Не требуется.",
        "legal_knowledge": "Не требуется.",
        "methods_knowledge": "Тест-дизайн, чек-листы, регрессионное тестирование.",
        "technology_knowledge": "Баг-трекер, офисные приложения, базовые SQL-запросы.",
        "domain_context_knowledge": "Понимание жизненного цикла внутренних информационных систем.",
        "experience_requirements": experience,
        "comments": "Дополнений нет.",
    }


def test_profile_is_available_only_after_campaign_inclusion_and_saves_draft(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        users = client.get("/api/demo/users").json()
        hr = find_user(users, "hr")
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        tree = client.get("/api/organization/tree", headers=hr_headers).json()
        tester_line = _staffing_line(tree, "Тестировщик")
        head = next(
            item
            for item in client.get("/api/hr/managers", headers=hr_headers).json()
            if item["position_title"] == "Начальник тестового отдела"
        )
        added = client.post(
            f"/api/hr/staffing-lines/{tester_line['id']}/employees/bulk",
            headers=hr_headers,
            json={
                "employees": [
                    {
                        "full_name": "Тестов Новый Без Кампании",
                        "email": "new.tester@demo.local",
                        "fte": 1,
                        "manager_assignment_id": head["assignment_id"],
                    }
                ]
            },
        )
        assert added.status_code == 200
        employee = next(
            user for user in client.get("/api/demo/users").json() if user["email"] == "new.tester@demo.local"
        )
        headers = {"X-Demo-User-Id": str(employee["id"])}
        assert client.get("/api/my/profiles", headers=headers).json() == []

        _activate_department_campaign(client)
        profile = client.get("/api/my/profiles", headers=headers).json()[0]
        assert profile["workflow_status"] == "not_started"
        assert len(profile["questions"]) == 30
        assert profile["questions"][9]["input_type"] == "table"
        assert profile["questions"][14]["input_type"] == "single_choice"

        saved = client.put(
            f"/api/my/profiles/{profile['id']}/draft",
            headers=headers,
            json={"answers": {"position_purpose": "Не допускаю критические дефекты до релиза."}},
        )
        assert saved.status_code == 200
        assert saved.json()["workflow_status"] == "draft"
        assert saved.json()["progress_percent"] == 3.33


def test_budget_fields_are_closed_choices(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        _, employee = _activate_department_campaign(client)
        headers = {"X-Demo-User-Id": str(employee["id"])}
        profile = client.get("/api/my/profiles", headers=headers).json()[0]

        budget_type = next(item for item in profile["questions"] if item["key"] == "expense_budget_type")
        budget_volume = next(item for item in profile["questions"] if item["key"] == "expense_budget_volume")
        budget_management = next(item for item in profile["questions"] if item["key"] == "expense_budget_management")

        assert budget_type["input_type"] == "single_choice"
        assert budget_volume["input_type"] == "single_choice"
        assert budget_management["input_type"] == "single_choice"
        assert [option["label"] for option in budget_volume["options"]] == [
            "До 10 млн",
            "10-100 млн",
            "100 млн - 1 млрд",
            "Свыше 1 млрд",
            "Не применимо.",
        ]

        invalid = client.put(
            f"/api/my/profiles/{profile['id']}/draft",
            headers=headers,
            json={"answers": {"expense_budget_type": "Инвестиционный", "expense_budget_volume": "квартира"}},
        )
        assert invalid.status_code == 422
        assert "Объем бюджета" in invalid.json()["detail"]

        valid = client.put(
            f"/api/my/profiles/{profile['id']}/draft",
            headers=headers,
            json={
                "answers": {
                    "expense_budget_type": "Инвестиционный",
                    "expense_budget_volume": "10-100 млн",
                    "expense_budget_management": "Участие в формировании и согласовании",
                }
            },
        )
        assert valid.status_code == 200
        assert valid.json()["answers"]["expense_budget_volume"] == "10-100 млн"


def test_manager_has_own_profile_separate_from_review_queue(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        _activate_department_campaign(client)
        manager = next(
            user for user in client.get("/api/demo/users").json() if user["email"] == "head.test@demo.local"
        )
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}

        own_profiles = client.get("/api/my/profiles", headers=manager_headers).json()
        assert len(own_profiles) == 1
        assert own_profiles[0]["position_title"] == "Начальник тестового отдела"

        review_queue = client.get("/api/manager/reviews", headers=manager_headers).json()
        assert all(item["employee_name"] != manager["full_name"] for item in review_queue)
        assert any(item["employee_name"] == "Тестов Тест Тестович" for item in review_queue)


def test_profile_submit_requires_all_sections_and_preserves_revisions_without_ai(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, employee = _activate_department_campaign(client)
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        profile_id = client.get("/api/my/profiles", headers=employee_headers).json()[0]["id"]

        incomplete = client.post(
            f"/api/my/profiles/{profile_id}/submit",
            headers=employee_headers,
            json={"answers": {"position_purpose": "Проверяю качество."}},
        )
        assert incomplete.status_code == 422

        answers = _complete_answers()
        first = client.post(
            f"/api/my/profiles/{profile_id}/submit",
            headers=employee_headers,
            json={"answers": answers},
        ).json()
        assert first["workflow_status"] == "submitted"
        assert first["revisions"][0]["revision_no"] == 1
        assert first["revisions"][0]["assistant_mode"] == "off"
        assert first["revisions"][0]["assistance_level"] == "none"

        revised_answers = {**answers, "position_purpose": "Защищаю пользователей от ошибок в выпусках."}
        second = client.post(
            f"/api/my/profiles/{profile_id}/submit",
            headers=employee_headers,
            json={"answers": revised_answers},
        ).json()
        assert [item["revision_no"] for item in second["revisions"]] == [2, 1]
        assert second["revisions"][1]["answers"]["position_purpose"] == answers["position_purpose"]
        assert second["revisions"][0]["answers"]["position_purpose"] == revised_answers["position_purpose"]

        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        audit = client.get("/api/hr/audit/recent", headers=hr_headers).json()
        submitted = [event for event in audit if event["action"] == "profile.submitted"]
        assert len(submitted) == 2
        assert submitted[0]["details"]["assistant_mode"] == "off"


def test_user_exports_submitted_profile_to_excel_template(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        employee, manager, profile_id = _submitted_tester_profile(client)
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        response = client.get(
            f"/api/my/profiles/{profile_id}/export.xlsx",
            headers=employee_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        values = _xlsx_values(
            response.content,
            {"C11", "B24", "B31", "C31", "A56", "A104", "C119", "D119"},
        )
        assert values["C11"] == "Тестировщик"
        assert values["B24"] == "Помогает выпускать изменения без критичных дефектов."
        assert values["B31"] == "Проверяет тестовые сценарии"
        assert values["C31"] == "Критичные дефекты выявляются до релиза."
        assert values["A56"] == "X"
        assert values["A104"] == "☑"
        assert values["C119"] == "2"
        assert values["D119"] == "Тестирование информационных систем."

        forbidden = client.get(
            f"/api/my/profiles/{profile_id}/export.xlsx",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert forbidden.status_code == 404


def test_user_cannot_edit_another_employees_profile(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        _, employee = _activate_department_campaign(client)
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        profile_id = client.get("/api/my/profiles", headers=employee_headers).json()[0]["id"]
        manager = next(
            user for user in client.get("/api/demo/users").json() if user["email"] == "head.test@demo.local"
        )
        response = client.put(
            f"/api/my/profiles/{profile_id}/draft",
            headers={"X-Demo-User-Id": str(manager["id"])},
            json={"answers": {"position_purpose": "Чужой ответ."}},
        )
        assert response.status_code == 404


def _submitted_tester_profile(client: TestClient) -> tuple[dict, dict, int]:
    _, employee = _activate_department_campaign(client)
    users = client.get("/api/demo/users").json()
    manager = next(user for user in users if user["email"] == "head.test@demo.local")
    employee_headers = {"X-Demo-User-Id": str(employee["id"])}
    profile_id = client.get("/api/my/profiles", headers=employee_headers).json()[0]["id"]
    submitted = client.post(
        f"/api/my/profiles/{profile_id}/submit",
        headers=employee_headers,
        json={"answers": _complete_answers()},
    )
    assert submitted.status_code == 200
    return employee, manager, profile_id


def _submitted_profiles(
    client: TestClient,
    emails: list[str],
) -> tuple[dict, dict, list[int]]:
    hr, _ = _activate_department_campaign(client)
    users = client.get("/api/demo/users").json()
    manager = next(user for user in users if user["email"] == "head.test@demo.local")
    profile_ids: list[int] = []
    for email in emails:
        employee = next(user for user in users if user["email"] == email)
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        submitted = client.post(
            f"/api/my/profiles/{profile['id']}/submit",
            headers=employee_headers,
            json={"answers": _complete_answers()},
        )
        assert submitted.status_code == 200
        profile_ids.append(profile["id"])
    return hr, manager, profile_ids


def test_manager_takes_submitted_profile_and_locks_employee_editing(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        employee, manager, profile_id = _submitted_tester_profile(client)
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}

        queue = client.get("/api/manager/reviews", headers=manager_headers).json()
        tester_review = next(item for item in queue if item["id"] == profile_id)
        assert tester_review["workflow_status"] == "submitted"
        assert tester_review["can_take"] is True

        taken = client.post(
            f"/api/manager/reviews/{profile_id}/take",
            headers=manager_headers,
        ).json()
        assert taken["workflow_status"] == "under_review"
        assert taken["can_decide"] is True
        assert taken["review_events"][0]["action"] == "taken"

        employee_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert employee_profile["can_edit"] is False
        blocked = client.put(
            f"/api/my/profiles/{profile_id}/draft",
            headers=employee_headers,
            json={"answers": _complete_answers()},
        )
        assert blocked.status_code == 409


def test_manager_returns_employee_resubmits_and_manager_verifies(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        employee, manager, profile_id = _submitted_tester_profile(client)
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        client.post(f"/api/manager/reviews/{profile_id}/take", headers=manager_headers)

        returned = client.post(
            f"/api/manager/reviews/{profile_id}/return",
            headers=manager_headers,
            json={"reason": "Уточните измеримый результат основной обязанности."},
        ).json()
        assert returned["workflow_status"] == "returned_for_revision"
        assert returned["review_events"][0]["action"] == "returned"

        employee_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert employee_profile["can_edit"] is True
        assert employee_profile["review_events"][0]["comment"] == (
            "Уточните измеримый результат основной обязанности."
        )

        corrected = {
            **_complete_answers(),
            "duties_results": json.dumps(
                [["Проверяю релиз", "Передаю отчет о критичных дефектах до выпуска."]],
                ensure_ascii=False,
            ),
        }
        resubmitted = client.post(
            f"/api/my/profiles/{profile_id}/submit",
            headers=employee_headers,
            json={"answers": corrected},
        ).json()
        assert resubmitted["workflow_status"] == "submitted"
        assert [item["revision_no"] for item in resubmitted["revisions"]] == [2, 1]

        client.post(f"/api/manager/reviews/{profile_id}/take", headers=manager_headers)
        verified = client.post(
            f"/api/manager/reviews/{profile_id}/verify",
            headers=manager_headers,
            json={"comment": "Профиль соответствует фактической работе."},
        ).json()
        assert verified["workflow_status"] == "manager_verified"
        assert verified["review_events"][0]["action"] == "verified"
        assert verified["latest_revision"]["revision_no"] == 2

        blocked_after_verify = client.post(
            f"/api/my/profiles/{profile_id}/submit",
            headers=employee_headers,
            json={"answers": corrected},
        )
        assert blocked_after_verify.status_code == 409


def test_only_immediate_manager_can_review_submitted_profile(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        employee, _, profile_id = _submitted_tester_profile(client)
        users = client.get("/api/demo/users").json()
        director = next(user for user in users if user["email"] == "director.test@demo.local")
        director_response = client.post(
            f"/api/manager/reviews/{profile_id}/take",
            headers={"X-Demo-User-Id": str(director["id"])},
        )
        employee_queue = client.get(
            "/api/manager/reviews",
            headers={"X-Demo-User-Id": str(employee["id"])},
        )
        assert director_response.status_code == 404
        assert employee_queue.status_code == 403


def test_manager_bulk_returns_selected_direct_profiles_and_audits_batch(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, manager, profile_ids = _submitted_profiles(
            client,
            ["tester@demo.local", "heatmap2@demo.local"],
        )
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}
        for profile_id in profile_ids:
            taken = client.post(
                f"/api/manager/reviews/{profile_id}/take",
                headers=manager_headers,
            )
            assert taken.status_code == 200

        director = next(
            user
            for user in client.get("/api/demo/users").json()
            if user["email"] == "director.test@demo.local"
        )
        forbidden = client.post(
            "/api/manager/reviews/bulk-return",
            headers={"X-Demo-User-Id": str(director["id"])},
            json={"profile_ids": profile_ids, "reason": "Проверить измеримые результаты."},
        )
        assert forbidden.status_code == 404

        returned = client.post(
            "/api/manager/reviews/bulk-return",
            headers=manager_headers,
            json={
                "profile_ids": profile_ids,
                "reason": "Уточните измеримые результаты для общей проверки.",
            },
        )
        assert returned.status_code == 200
        assert returned.json()["selection"] == "profiles"
        assert returned.json()["returned_count"] == 2
        queue = client.get("/api/manager/reviews", headers=manager_headers).json()
        assert {
            item["id"] for item in queue if item["workflow_status"] == "returned_for_revision"
        }.issuperset(profile_ids)

        audit = client.get(
            "/api/hr/audit/recent",
            headers={"X-Demo-User-Id": str(hr["id"])},
        ).json()
        batch = next(
            event
            for event in audit
            if event["action"] == "profiles.bulk_returned_for_revision"
        )
        assert batch["details"]["profile_ids"] == profile_ids
        assert batch["details"]["returned_count"] == 2


def _manager_verified_profile(client: TestClient) -> tuple[dict, dict, dict, int]:
    employee, manager, profile_id = _submitted_tester_profile(client)
    hr = find_user(client.get("/api/demo/users").json(), "hr")
    manager_headers = {"X-Demo-User-Id": str(manager["id"])}
    client.post(f"/api/manager/reviews/{profile_id}/take", headers=manager_headers)
    verified = client.post(
        f"/api/manager/reviews/{profile_id}/verify",
        headers=manager_headers,
        json={"comment": "Проверено непосредственным руководителем."},
    )
    assert verified.status_code == 200
    return hr, employee, manager, profile_id


def test_hr_accepts_verified_profile_and_campaign_counts_final_status(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, employee, _, profile_id = _manager_verified_profile(client)
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}

        queue = client.get("/api/hr/profile-reviews", headers=hr_headers).json()
        review = next(item for item in queue if item["id"] == profile_id)
        assert review["workflow_status"] == "manager_verified"
        assert review["can_decide"] is True

        accepted = client.post(
            f"/api/hr/profile-reviews/{profile_id}/accept",
            headers=hr_headers,
            json={"comment": "Принято HR для итогового профиля."},
        ).json()
        assert accepted["workflow_status"] == "hr_accepted"
        assert accepted["review_events"][0]["action"] == "hr_accepted"

        employee_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert employee_profile["workflow_status"] == "hr_accepted"
        assert employee_profile["can_edit"] is False

        campaign = client.get("/api/hr/campaigns", headers=hr_headers).json()[0]
        assert campaign["status_counts"]["hr_accepted"] == 1
        assert campaign["status_counts"]["not_started"] == 8


def test_hr_return_goes_to_manager_before_employee_can_edit(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, employee, manager, profile_id = _manager_verified_profile(client)
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}

        returned = client.post(
            f"/api/hr/profile-reviews/{profile_id}/return",
            headers=hr_headers,
            json={"reason": "Нужно уточнить подтверждение результата в обязанностях."},
        ).json()
        assert returned["workflow_status"] == "returned_by_hr"
        assert returned["review_events"][0]["action"] == "hr_returned"

        employee_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert employee_profile["workflow_status"] == "returned_by_hr"
        assert employee_profile["can_edit"] is False

        manager_queue = client.get("/api/manager/reviews", headers=manager_headers).json()
        manager_review = next(item for item in manager_queue if item["id"] == profile_id)
        assert manager_review["returned_by_hr"] is True
        assert manager_review["can_decide"] is True

        delegated = client.post(
            f"/api/manager/reviews/{profile_id}/return",
            headers=manager_headers,
            json={"reason": "Добавьте измеримый результат проверки перед релизом."},
        ).json()
        assert delegated["workflow_status"] == "returned_for_revision"
        editable_again = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert editable_again["can_edit"] is True


def test_hr_bulk_returns_verified_profiles_by_unit_and_audits_batch(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, manager, profile_ids = _submitted_profiles(
            client,
            ["tester@demo.local", "heatmap2@demo.local"],
        )
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}
        for profile_id in profile_ids:
            client.post(f"/api/manager/reviews/{profile_id}/take", headers=manager_headers)
            verified = client.post(
                f"/api/manager/reviews/{profile_id}/verify",
                headers=manager_headers,
                json={"comment": "Проверено для группового решения."},
            )
            assert verified.status_code == 200

        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        hr_queue = client.get("/api/hr/profile-reviews", headers=hr_headers).json()
        unit_id = next(item for item in hr_queue if item["id"] == profile_ids[0])["org_unit_id"]
        returned = client.post(
            "/api/hr/profile-reviews/bulk-return",
            headers=hr_headers,
            json={
                "org_unit_id": unit_id,
                "reason": "Нужно единообразно уточнить доказательства результатов.",
            },
        )
        assert returned.status_code == 200
        assert returned.json()["selection"] == "org_unit"
        assert returned.json()["returned_count"] == 2
        manager_queue = client.get("/api/manager/reviews", headers=manager_headers).json()
        assert {
            item["id"] for item in manager_queue if item["workflow_status"] == "returned_by_hr"
        }.issuperset(profile_ids)

        audit = client.get("/api/hr/audit/recent", headers=hr_headers).json()
        batch = next(event for event in audit if event["action"] == "profiles.bulk_returned_by_hr")
        assert batch["details"]["org_unit_id"] == unit_id
        assert batch["details"]["returned_count"] == 2


def test_manager_can_reconfirm_hr_return_without_reopening_employee(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, employee, manager, profile_id = _manager_verified_profile(client)
        hr_headers = {"X-Demo-User-Id": str(hr["id"])}
        manager_headers = {"X-Demo-User-Id": str(manager["id"])}
        employee_headers = {"X-Demo-User-Id": str(employee["id"])}
        client.post(
            f"/api/hr/profile-reviews/{profile_id}/return",
            headers=hr_headers,
            json={"reason": "Проверьте пояснение перед повторным направлением."},
        )

        reconfirmed = client.post(
            f"/api/manager/reviews/{profile_id}/verify",
            headers=manager_headers,
            json={"comment": "Повторно подтверждаю без изменения ответов сотрудника."},
        ).json()
        assert reconfirmed["workflow_status"] == "manager_verified"
        assert reconfirmed["latest_revision"]["revision_no"] == 1

        employee_profile = client.get("/api/my/profiles", headers=employee_headers).json()[0]
        assert employee_profile["can_edit"] is False
        accepted = client.post(
            f"/api/hr/profile-reviews/{profile_id}/accept",
            headers=hr_headers,
            json={"comment": None},
        ).json()
        assert accepted["workflow_status"] == "hr_accepted"


def test_hr_cannot_accept_unverified_profile_and_manager_cannot_use_hr_queue(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        hr, employee = _activate_department_campaign(client)
        users = client.get("/api/demo/users").json()
        manager = next(user for user in users if user["email"] == "head.test@demo.local")
        profile_id = client.get(
            "/api/my/profiles",
            headers={"X-Demo-User-Id": str(employee["id"])},
        ).json()[0]["id"]

        premature = client.post(
            f"/api/hr/profile-reviews/{profile_id}/accept",
            headers={"X-Demo-User-Id": str(hr["id"])},
            json={"comment": None},
        )
        forbidden = client.get(
            "/api/hr/profile-reviews",
            headers={"X-Demo-User-Id": str(manager["id"])},
        )
        assert premature.status_code == 409
        assert forbidden.status_code == 403
