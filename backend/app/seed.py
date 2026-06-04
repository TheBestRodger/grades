from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    Document,
    DocumentLink,
    Employee,
    EmployeeProfile,
    OrgUnit,
    ProfileDraft,
    ProfileReviewEvent,
    ProfileRevision,
    StaffingLine,
)
from .profile_operations import PROFILE_QUESTIONS
from .work_staffing_import import seed_work_staffing_data


_VISIBLE_LABEL_REPLACEMENTS = (
    ("Демо-сценарий тепловой карты", "Кампания профилирования подразделения"),
    ("Демо-волна тестового направления", "Кампания профилирования"),
    ("Волна 1: тестовый отдел", "Волна 1: отдел сопровождения процессов"),
    ("Проректор по тестовым делам", "Проректор по развитию процессов"),
    ("Тестовое направление", "Направление развития процессов"),
    ("Тестовый отдел", "Отдел сопровождения процессов"),
    ("Директор тестового направления", "Директор направления развития процессов"),
    ("Начальник тестового отдела", "Начальник отдела сопровождения процессов"),
    ("Тестировщик", "Специалист по сопровождению процессов"),
    ("тестировщика", "специалиста"),
    ("тестировщик", "специалист"),
    ("Тестов Тест Тестович-2", "Павлов Сергей Игоревич"),
    ("Тестов Тест Тестович-3", "Кузнецов Андрей Петрович"),
    ("Тестов-4 Тест-4 Тестович-4", "Орлова Марина Викторовна"),
    ("Тестов Тест Тестович", "Иванов Иван Сергеевич"),
    ("Тестова Вторая Тестовна", "Петрова Анна Сергеевна"),
    ("Тестов Третий Тестович", "Смирнов Алексей Олегович"),
    ("Тестова Четвертая Тестовна", "Волкова Мария Дмитриевна"),
    ("Тестов Пятый Демо", "Соколов Денис Андреевич"),
    ("Тестова Шестая Демо", "Морозова Елена Викторовна"),
    ("Тестов Седьмой Сомневающийся", "Федоров Павел Николаевич"),
    ("Тестов Восьмой Аномальный", "Николаева Ольга Игоревна"),
    ("ДИ-ДЕМО-НАЧ-ТО-001", "ДИ-ОСП-РУК-001"),
    ("ДИ-ДЕМО-ТЕСТ-001", "ДИ-ОСП-СПЕЦ-001"),
    ("ПОЛ-ДЕМО-ТО-001", "ПОЛ-ОСП-001"),
    ("ПС-ДЕМО-ТЕСТ-001", "ПС-ОСП-001"),
    ("1.0-demo", "1.0"),
    ("hr@demo.local", "hr@profile.local"),
    ("vice.test@demo.local", "vice@profile.local"),
    ("director.test@demo.local", "director@profile.local"),
    ("head.test@demo.local", "head@profile.local"),
    ("tester@demo.local", "specialist@profile.local"),
    ("heatmap2@demo.local", "employee2@profile.local"),
    ("heatmap3@demo.local", "employee3@profile.local"),
    ("heatmap4@demo.local", "employee4@profile.local"),
    ("heatmap5@demo.local", "employee5@profile.local"),
    ("heatmap6@demo.local", "employee6@profile.local"),
    ("heatmap7@demo.local", "employee7@profile.local"),
    ("heatmap8@demo.local", "employee8@profile.local"),
    ("Синтетическая демо-инструкция.", ""),
    ("Синтетическая демо-инструкция только для тестовой ветки.", ""),
    ("Синтетическое демо-положение.", ""),
    ("Синтетический демо-профстандарт.", ""),
    ("Профстандарт нстрационного специалиста", "Профстандарт специалиста по сопровождению процессов"),
    ("Должностная инструкция начальника проверокого отдела", "Должностная инструкция начальника отдела сопровождения процессов"),
    ("Должностная инструкция специалиста проверокого отдела", "Должностная инструкция специалиста по сопровождению процессов"),
    ("Положение о провероком отделе", "Положение об отделе сопровождения процессов"),
    ("проверокого выпуска", "выпуска"),
    ("проверокого направления", "направления"),
    ("рабочие проверки", "проверки"),
    ("рабочих профилей", "профилей"),
    ("рабочих замечаний", "замечаний"),
    ("достаточно рабочими", "актуальными"),
    ("рабочие задачи", "задачи"),
    ("рабочие профили", "профили"),
    ("рабочие дефекты", "дефекты"),
    ("рабочие замечания", "замечания"),
    ("рабочие проверки", "проверки"),
    ("демонстрационном контуре", "выбранном контуре"),
    ("демонстрационной группы", "рабочей группы"),
    ("демонстрационной иерархии", "структуре управления"),
    ("демонстрационного", ""),
    ("демо-сценария", "сценария"),
    ("Демо", ""),
    ("демо", ""),
    ("Тест-дизайн", "Чек-листы"),
    ("тест-дизайн", "чек-листы"),
    ("тестовые дефекты", "дефекты"),
    ("тестовые задачи", "задачи"),
    ("тестовые профили", "профили"),
    ("тестовые проверки", "проверки"),
    ("тестовые замечания", "замечания"),
    ("тестовые сценарии", "сценарии"),
    ("тестовый выпуск", "выпуск"),
    ("тестового выпуска", "выпуска"),
    ("тестового направления", "направления"),
    ("тестовой ветки", "выбранной ветки"),
    (" тестов ", " проверок "),
    (" тесты ", " проверки "),
)


def seed_demo_data(session: Session, work_staffing_file: Path | None = None) -> None:
    _normalize_visible_demo_labels(session)
    existing = session.scalar(select(OrgUnit.id).where(OrgUnit.path == "DEMO/Ректорат"))
    if existing:
        seed_demo_documents(session)
        seed_heat_map_showcase(session)
        if work_staffing_file is not None:
            seed_work_staffing_data(session, work_staffing_file)
        seed_work_test_direction(session)
        return

    rectorate = OrgUnit(name="Ректорат", path="DEMO/Ректорат", is_demo=True)
    vice_unit = OrgUnit(
        name="Проректор по развитию процессов",
        path="DEMO/Ректорат/Проректор по развитию процессов",
        parent=rectorate,
        is_demo=True,
    )
    direction = OrgUnit(
        name="Направление развития процессов",
        path="DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов",
        parent=vice_unit,
        is_demo=True,
    )
    department = OrgUnit(
        name="Отдел сопровождения процессов",
        path="DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов/Отдел сопровождения процессов",
        parent=direction,
        is_demo=True,
    )
    session.add_all([rectorate, vice_unit, direction, department])
    session.flush()

    rector_line = StaffingLine(
        org_unit=rectorate, title="Ректор", approved_fte=1, reported_occupied_fte=1, is_demo=True
    )
    vice_line = StaffingLine(
        org_unit=vice_unit,
        title="Проректор по развитию процессов",
        approved_fte=1,
        reported_occupied_fte=1,
        is_demo=True,
    )
    director_line = StaffingLine(
        org_unit=direction,
        title="Директор направления развития процессов",
        approved_fte=1,
        reported_occupied_fte=1,
        is_demo=True,
    )
    head_line = StaffingLine(
        org_unit=department,
        title="Начальник отдела сопровождения процессов",
        approved_fte=1,
        reported_occupied_fte=1,
        is_demo=True,
    )
    tester_line = StaffingLine(
        org_unit=department,
        title="Специалист по сопровождению процессов",
        approved_fte=12,
        reported_occupied_fte=8,
        is_demo=True,
    )
    session.add_all([rector_line, vice_line, director_line, head_line, tester_line])
    session.flush()

    hr = Employee(
        full_name="Эйчар Эйчарович Эйчаров",
        email="hr@profile.local",
        system_role="hr",
        is_demo=True,
    )
    vice = Employee(
        full_name="Павлов Сергей Игоревич",
        email="vice@profile.local",
        system_role="manager",
        is_demo=True,
    )
    director = Employee(
        full_name="Кузнецов Андрей Петрович",
        email="director@profile.local",
        system_role="manager",
        is_demo=True,
    )
    head = Employee(
        full_name="Орлова Марина Викторовна",
        email="head@profile.local",
        system_role="manager",
        is_demo=True,
    )
    tester = Employee(
        full_name="Иванов Иван Сергеевич",
        email="specialist@profile.local",
        system_role="employee",
        is_demo=True,
    )
    session.add_all([hr, vice, director, head, tester])
    session.flush()

    hr_assignment = Assignment(employee=hr, staffing_line=rector_line, fte=1, is_demo=True)
    session.add(hr_assignment)
    session.flush()
    vice_assignment = Assignment(
        employee=vice,
        staffing_line=vice_line,
        manager=hr_assignment,
        fte=1,
        is_demo=True,
    )
    session.add(vice_assignment)
    session.flush()
    director_assignment = Assignment(
        employee=director,
        staffing_line=director_line,
        manager=vice_assignment,
        fte=1,
        is_demo=True,
    )
    session.add(director_assignment)
    session.flush()
    head_assignment = Assignment(
        employee=head,
        staffing_line=head_line,
        manager=director_assignment,
        fte=1,
        is_demo=True,
    )
    session.add(head_assignment)
    session.flush()
    session.add(
        Assignment(
            employee=tester,
            staffing_line=tester_line,
            manager=head_assignment,
            fte=1,
            is_demo=True,
        )
    )
    session.flush()
    seed_demo_documents(session)
    seed_heat_map_showcase(session)
    if work_staffing_file is not None:
        seed_work_staffing_data(session, work_staffing_file)
    seed_work_test_direction(session)


def seed_work_test_direction(session: Session) -> None:
    root = _ensure_work_test_unit(session, "!Направление тест", None)

    structure = {
        "Аналитика": {
            "Группа методологии": ["Сектор регламентов", "Сектор описания процессов"],
            "Группа данных": ["Сектор метрик", "Сектор качества данных"],
        },
        "Внедрение": {
            "Группа сопровождения": ["Сектор пилотов", "Сектор поддержки"],
            "Группа обучения": ["Сектор материалов", "Сектор практик"],
        },
        "Разработка": {
            "Группа интеграций": ["Сектор API", "Сектор данных"],
            "Группа платформы": ["Сектор интерфейсов", "Сектор эксплуатации"],
        },
    }

    _ensure_work_test_staffing_pack(session, root)
    for level_1_name, level_2 in structure.items():
        level_1 = _ensure_work_test_unit(session, level_1_name, root)
        _ensure_work_test_staffing_pack(session, level_1)
        for level_2_name, level_3_names in level_2.items():
            level_2_unit = _ensure_work_test_unit(session, level_2_name, level_1)
            _ensure_work_test_staffing_pack(session, level_2_unit)
            for level_3_name in level_3_names:
                level_3 = _ensure_work_test_unit(session, level_3_name, level_2_unit)
                _ensure_work_test_staffing_line(session, level_3, f"Руководитель: {level_3_name}", 1)
                _ensure_work_test_staffing_line(session, level_3, f"Специалист: {level_3_name}", 2)


def _ensure_work_test_unit(session: Session, name: str, parent: OrgUnit | None) -> OrgUnit:
    path = f"{parent.path}/{name}" if parent else f"WORK/{name}"
    unit = session.scalar(select(OrgUnit).where(OrgUnit.path == path, OrgUnit.is_demo.is_(False)))
    if unit is not None:
        unit.name = name
        unit.parent = parent
        unit.is_active = True
        return unit
    unit = OrgUnit(name=name, path=path, parent=parent, is_demo=False)
    session.add(unit)
    session.flush()
    return unit


def _ensure_work_test_staffing_pack(session: Session, unit: OrgUnit) -> None:
    _ensure_work_test_staffing_line(session, unit, f"Руководитель подразделения: {unit.name}", 1)
    _ensure_work_test_staffing_line(session, unit, f"Ведущий специалист: {unit.name}", 1)
    _ensure_work_test_staffing_line(session, unit, f"Специалист: {unit.name}", 1)


def _ensure_work_test_staffing_line(session: Session, unit: OrgUnit, title: str, approved_fte: float) -> None:
    line = session.scalar(
        select(StaffingLine).where(
            StaffingLine.org_unit_id == unit.id,
            StaffingLine.title == title,
            StaffingLine.is_demo.is_(False),
        )
    )
    if line is not None:
        line.approved_fte = max(line.approved_fte, approved_fte)
        line.is_active = True
        return
    session.add(
        StaffingLine(
            org_unit=unit,
            title=title,
            approved_fte=approved_fte,
            reported_occupied_fte=0,
            is_demo=False,
        )
    )


def _normalize_visible_demo_labels(session: Session) -> None:
    for unit in session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(True))).all():
        unit.name = _clean_visible_label(unit.name)
        unit.path = _clean_visible_label(unit.path)

    for line in session.scalars(select(StaffingLine).where(StaffingLine.is_demo.is_(True))).all():
        line.title = _clean_visible_label(line.title)

    for employee in session.scalars(select(Employee).where(Employee.is_demo.is_(True))).all():
        employee.full_name = _clean_visible_label(employee.full_name)
        employee.email = _clean_visible_email(employee)

    for campaign in session.scalars(select(Campaign).where(Campaign.is_demo.is_(True))).all():
        campaign.name = _clean_visible_label(campaign.name)

    for wave in session.scalars(select(CampaignWave).where(CampaignWave.is_demo.is_(True))).all():
        wave.name = _clean_visible_label(wave.name)

    for document in session.scalars(select(Document).where(Document.is_demo.is_(True))).all():
        document.document_code = _clean_visible_label(document.document_code)
        document.title = _clean_visible_label(document.title)
        document.version = _clean_visible_label(document.version)
        if document.content_text:
            document.content_text = _clean_visible_label(document.content_text)

    for draft in session.scalars(
        select(ProfileDraft)
        .join(ProfileDraft.profile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(Campaign.is_demo.is_(True))
    ).all():
        draft.answers_json = _clean_visible_label(draft.answers_json)

    for revision in session.scalars(
        select(ProfileRevision)
        .join(ProfileRevision.profile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(Campaign.is_demo.is_(True))
    ).all():
        revision.answers_json = _clean_visible_label(revision.answers_json)

    for event in session.scalars(
        select(ProfileReviewEvent)
        .join(ProfileReviewEvent.profile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(Campaign.is_demo.is_(True))
    ).all():
        if event.comment:
            event.comment = _clean_visible_label(event.comment)

    for event in session.scalars(select(AuditEvent)).all():
        if event.details_json:
            event.details_json = _clean_visible_label(event.details_json)


def _clean_visible_label(value: str) -> str:
    result = value
    for source, target in _VISIBLE_LABEL_REPLACEMENTS:
        result = result.replace(source, target)
    return " ".join(result.split())


def _clean_visible_email(employee: Employee) -> str:
    email = _clean_visible_label(employee.email)
    lowered = email.lower()
    if "demo" in lowered or "test" in lowered:
        return f"user{employee.id}@profile.local"
    return email


def seed_heat_map_showcase(session: Session) -> None:
    hr = session.scalar(select(Employee).where(Employee.email == "hr@profile.local"))
    head = session.scalar(select(Employee).where(Employee.email == "head@profile.local"))
    tester_line = session.scalar(
        select(StaffingLine)
        .join(StaffingLine.org_unit)
        .where(
            StaffingLine.title == "Специалист по сопровождению процессов",
            OrgUnit.path
            == "DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов/Отдел сопровождения процессов",
        )
    )
    head_assignment = session.scalar(
        select(Assignment)
        .join(Assignment.employee)
        .where(Employee.email == "head@profile.local", Assignment.is_demo.is_(True))
    )
    if hr is None or head is None or tester_line is None or head_assignment is None:
        return

    tester_line.approved_fte = max(tester_line.approved_fte, 12)
    tester_line.reported_occupied_fte = max(tester_line.reported_occupied_fte, 8)

    showcase_people = [
        ("specialist@profile.local", "Иванов Иван Сергеевич", "hr_accepted"),
        ("employee2@profile.local", "Петрова Анна Сергеевна", "hr_accepted"),
        ("employee3@profile.local", "Смирнов Алексей Олегович", "hr_accepted"),
        ("employee4@profile.local", "Волкова Мария Дмитриевна", "hr_accepted"),
        ("employee5@profile.local", "Соколов Денис Андреевич", "hr_accepted"),
        ("employee6@profile.local", "Морозова Елена Викторовна", "hr_accepted"),
        ("employee7@profile.local", "Федоров Павел Николаевич", "returned_for_revision"),
        ("employee8@profile.local", "Николаева Ольга Игоревна", "returned_by_hr"),
    ]

    assignments: list[tuple[Assignment, str, int]] = []
    for index, (email, full_name, status) in enumerate(showcase_people, start=1):
        employee = _ensure_demo_employee(session, email, full_name)
        assignment = _ensure_assignment(session, employee, tester_line, head_assignment)
        assignments.append((assignment, status, index))

    campaign = _ensure_showcase_campaign(session, hr)
    wave = _ensure_showcase_wave(session, campaign, hr)

    for assignment, status, index in assignments:
        participant = _ensure_showcase_participant(session, campaign, wave, assignment, hr)
        _ensure_showcase_profile(session, participant, status, index, head, hr)


def _ensure_demo_employee(session: Session, email: str, full_name: str) -> Employee:
    employee = session.scalar(select(Employee).where(Employee.email == email))
    if employee is not None:
        return employee
    employee = Employee(
        full_name=full_name,
        email=email,
        system_role="employee",
        is_demo=True,
    )
    session.add(employee)
    session.flush()
    return employee


def _ensure_assignment(
    session: Session,
    employee: Employee,
    staffing_line: StaffingLine,
    manager: Assignment,
) -> Assignment:
    assignment = session.scalar(
        select(Assignment).where(
            Assignment.employee_id == employee.id,
            Assignment.staffing_line_id == staffing_line.id,
            Assignment.is_demo.is_(True),
        )
    )
    if assignment is not None:
        if assignment.manager_assignment_id is None:
            assignment.manager_assignment_id = manager.id
        return assignment
    assignment = Assignment(
        employee=employee,
        staffing_line=staffing_line,
        manager=manager,
        fte=1,
        is_demo=True,
    )
    session.add(assignment)
    session.flush()
    return assignment


def _ensure_showcase_campaign(session: Session, hr: Employee) -> Campaign:
    campaign = session.scalar(
        select(Campaign).where(
            Campaign.name == "Кампания профилирования подразделения",
            Campaign.is_demo.is_(True),
        )
    )
    if campaign is not None:
        campaign.status = "active"
        return campaign
    campaign = Campaign(
        name="Кампания профилирования подразделения",
        status="active",
        created_by_id=hr.id,
        is_demo=True,
    )
    session.add(campaign)
    session.flush()
    return campaign


def _ensure_showcase_wave(session: Session, campaign: Campaign, hr: Employee) -> CampaignWave:
    wave = session.scalar(
        select(CampaignWave).where(
            CampaignWave.campaign_id == campaign.id,
            CampaignWave.name == "Волна 1: отдел сопровождения процессов",
        )
    )
    if wave is not None:
        wave.status = "active"
        return wave
    wave = CampaignWave(
        campaign=campaign,
        name="Волна 1: отдел сопровождения процессов",
        status="active",
        created_by_id=hr.id,
        is_demo=True,
    )
    session.add(wave)
    session.flush()
    return wave


def _ensure_showcase_participant(
    session: Session,
    campaign: Campaign,
    wave: CampaignWave,
    assignment: Assignment,
    hr: Employee,
) -> CampaignParticipant:
    participant = session.scalar(
        select(CampaignParticipant).where(
            CampaignParticipant.campaign_id == campaign.id,
            CampaignParticipant.assignment_id == assignment.id,
        )
    )
    if participant is not None:
        participant.campaign_wave_id = wave.id
        participant.participation_status = "included"
        participant.expected_to_submit = True
        return participant
    participant = CampaignParticipant(
        campaign=campaign,
        wave=wave,
        assignment=assignment,
        participation_status="included",
        expected_to_submit=True,
        included_by_id=hr.id,
    )
    session.add(participant)
    session.flush()
    return participant


def _ensure_showcase_profile(
    session: Session,
    participant: CampaignParticipant,
    workflow_status: str,
    index: int,
    manager: Employee,
    hr: Employee,
) -> None:
    profile = participant.profile
    if profile is None:
        profile = EmployeeProfile(participant=participant)
        session.add(profile)
        session.flush()

    if profile.revisions:
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    answers = _showcase_answers(index, workflow_status)
    profile.started_at = now
    profile.last_activity_at = now
    profile.progress_percent = 100
    profile.workflow_status = workflow_status
    profile.draft = ProfileDraft(
        answers_json=json.dumps(answers, ensure_ascii=False),
        updated_at=now,
    )
    revision = ProfileRevision(
        profile=profile,
        revision_no=1,
        answers_json=json.dumps(answers, ensure_ascii=False),
        submitted_at=now,
        assistant_mode="off",
        assistance_level="none",
        assisted_sections_json="[]",
        ai_check_status="not_run",
        locked_at=now if workflow_status != "returned_for_revision" else None,
    )
    session.add(revision)
    session.flush()

    if workflow_status == "hr_accepted":
        _add_showcase_event(session, profile, revision, manager, "verified", "Профиль соответствует работе специалиста.")
        _add_showcase_event(session, profile, revision, hr, "hr_accepted", "Профиль принят.")
    elif workflow_status == "returned_for_revision":
        _add_showcase_event(
            session,
            profile,
            revision,
            manager,
            "returned",
            "Нужно уточнить измеримый результат по регрессионной проверке.",
        )
    elif workflow_status == "returned_by_hr":
        _add_showcase_event(session, profile, revision, manager, "verified", "Подтверждено руководителем.")
        _add_showcase_event(
            session,
            profile,
            revision,
            hr,
            "hr_returned",
            "В ответах есть обязанности, не подтвержденные должностной инструкцией.",
        )


def _add_showcase_event(
    session: Session,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    actor: Employee,
    action: str,
    comment: str,
) -> None:
    session.add(
        ProfileReviewEvent(
            profile=profile,
            revision=revision,
            actor=actor,
            action=action,
            comment=comment,
        )
    )


def _showcase_answers(index: int, workflow_status: str) -> dict[str, str]:
    duties = [
        ["Проверяет ключевые сценарии процесса", "Критичные дефекты выявляются до релиза."],
        ["Фиксирует дефекты", "Команда разработки получает воспроизводимые описания."],
        ["Готовит отчет о проверке", "Руководитель видит готовность выпуска."],
        ["Поддерживает исходные данные", "Проверки повторяются без ручного поиска исходных данных."],
    ]
    if workflow_status == "returned_for_revision":
        duties[2] = ["Проверяет регресс", "Результат пока описан без метрики и требует уточнения."]
    if workflow_status == "returned_by_hr":
        duties = [
            ["Выполняет несвязанные поручения", "Результат не относится к профилю должности."],
            ["Готовит организационные материалы", "Участники быстрее возвращаются к рабочему процессу."],
            ["Иногда открывает баг-трекер", "Дефекты появляются, но без понятной проверки."],
        ]

    external = [["Внешний подрядчик", "Среда проверки", "Согласована готовность стенда."]]
    internal = [["Разработчики", "Дефекты", "Исправления проверены до выпуска."]]
    experience = [
        ["Профессиональный", str(1 + index % 4), "Сопровождение информационных систем."],
        ["Управленческий", "0", "Не требуется для должности."],
    ]
    answers = {
        "position_name": "Специалист по сопровождению процессов",
        "org_structure": "Ректорат / Проректор по развитию процессов / Направление развития процессов / Отдел сопровождения процессов",
        "administrative_manager": "Начальник отдела сопровождения процессов / Отдел сопровождения процессов",
        "functional_manager": "Совпадает.",
        "direct_admin_reports": "Нет.",
        "total_reports": "0",
        "functional_reports": "Нет.",
        "completion_date": "26.05.2026",
        "position_purpose": (
            "Помогает выпускать изменения без критичных дефектов."
            if workflow_status != "returned_by_hr"
            else "Занимаюсь всем понемногу: поручения, материалы, иногда проверки."
        ),
        "duties_results": json.dumps(duties, ensure_ascii=False),
        "income_responsibility": "Не применимо.",
        "expense_budget_type": "Не применимо.",
        "expense_budget_volume": "Не применимо.",
        "expense_budget_management": "Не применимо.",
        "task_typicality": "Типовые с вариациями",
        "complex_task_example": "При ограниченном времени выбирает критичные сценарии проверки и объясняет риск руководителю.",
        "external_interactions": json.dumps(external, ensure_ascii=False),
        "internal_interactions": json.dumps(internal, ensure_ascii=False),
        "government_interactions": "Не применимо.",
        "independent_decisions": "Самостоятельно оформляет дефекты и выбирает порядок проверки типовых сценариев.",
        "approval_decisions": "Выпуск и приоритеты согласует руководитель.",
        "education": "Высшее (бакалавр / специалист / магистр)",
        "specialization": "Информационные системы или смежное направление.",
        "certification": "Не требуется.",
        "legal_knowledge": "Не требуется.",
        "methods_knowledge": "Чек-листы, регрессионная проверка, анализ дефектов.",
        "technology_knowledge": "Баг-трекер, офисные приложения, базовые SQL-запросы.",
        "domain_context_knowledge": "Понимание жизненного цикла внутренних информационных систем.",
        "experience_requirements": json.dumps(experience, ensure_ascii=False),
        "comments": "Заполнено без сопровождения ассистента: AI_MODE=off.",
    }
    return {question["key"]: answers.get(question["key"], "") for question in PROFILE_QUESTIONS}


def seed_demo_documents(session: Session) -> None:
    department = session.scalar(
        select(OrgUnit).where(
            OrgUnit.path
            == "DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов/Отдел сопровождения процессов"
        )
    )
    head_line = session.scalar(
        select(StaffingLine)
        .join(StaffingLine.org_unit)
        .where(
            StaffingLine.title == "Начальник отдела сопровождения процессов",
            OrgUnit.path
            == "DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов/Отдел сопровождения процессов",
        )
    )
    tester_line = session.scalar(
        select(StaffingLine)
        .join(StaffingLine.org_unit)
        .where(
            StaffingLine.title == "Специалист по сопровождению процессов",
            OrgUnit.path
            == "DEMO/Ректорат/Проректор по развитию процессов/Направление развития процессов/Отдел сопровождения процессов",
        )
    )
    hr_id = session.scalar(select(Employee.id).where(Employee.email == "hr@profile.local"))
    if department is None or head_line is None or tester_line is None:
        return

    def document(
        code: str,
        document_type: str,
        title: str,
        content_text: str,
    ) -> Document:
        existing = session.scalar(select(Document).where(Document.document_code == code))
        if existing is not None:
            return existing
        item = Document(
            document_code=code,
            document_type=document_type,
            title=title,
            version="1.0",
            document_status="confirmed",
            content_text=content_text,
            ocr_quality_status="manual_demo",
            is_demo=True,
        )
        session.add(item)
        session.flush()
        return item

    def link(item: Document, target_type: str, target_id: int) -> None:
        exists = session.scalar(
            select(DocumentLink.id).where(
                DocumentLink.document_id == item.id,
                DocumentLink.target_type == target_type,
                DocumentLink.target_id == target_id,
            )
        )
        if exists:
            return
        session.add(
            DocumentLink(
                document_id=item.id,
                target_type=target_type,
                target_id=target_id,
                link_status="confirmed",
                confirmed_by_id=hr_id,
                confirmed_at=datetime.now(UTC).replace(tzinfo=None),
                is_demo=True,
            )
        )

    head_instruction = document(
        "ДИ-ОСП-РУК-001",
        "job_instruction",
        "Должностная инструкция начальника отдела сопровождения процессов",
        (
            "Начальник отдела сопровождения процессов планирует проверки, распределяет задачи, "
            "подтверждает результаты профилей и контролирует готовность материалов к выпуску."
        ),
    )
    tester_instruction = document(
        "ДИ-ОСП-СПЕЦ-001",
        "job_instruction",
        "Должностная инструкция специалиста по сопровождению процессов",
        (
            "Специалист по сопровождению процессов проверяет сценарии, фиксирует дефекты "
            "и готовит краткий отчет о готовности выпуска."
        ),
    )
    department_regulation = document(
        "ПОЛ-ОСП-001",
        "unit_regulation",
        "Положение об отделе сопровождения процессов",
        (
            "Отдел сопровождения процессов обеспечивает проверку ключевых процессов, ведет "
            "реестр замечаний и передает сводку руководителю направления."
        ),
    )
    tester_standard = document(
        "ПС-ОСП-001",
        "professional_standard",
        "Профстандарт специалиста по сопровождению процессов",
        (
            "Подтверждает базовые навыки: работа с чек-листами, фиксация дефектов, "
            "коммуникация с руководителем и аккуратное заполнение профиля без передачи "
            "персональных данных в ИИ."
        ),
    )

    link(head_instruction, "staffing_line", head_line.id)
    link(tester_instruction, "staffing_line", tester_line.id)
    link(department_regulation, "org_unit", department.id)
    link(tester_standard, "staffing_line", tester_line.id)
