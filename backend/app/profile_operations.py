from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    ProfileDraft,
    QuestionnaireQuestionSetting,
    ProfileReviewEvent,
    ProfileRevision,
    StaffingLine,
)
from .schemas import ProfileAnswersRequest, QuestionnaireSettingsUpdate


PROFILE_QUESTIONS = [
    {
        "key": "position_name",
        "section": "Раздел 1. Общая информация",
        "title": "Наименование должности",
        "question": "Укажите полное наименование согласно штатному расписанию.",
        "example": "Для новой должности укажите планируемое полное наименование.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "org_structure",
        "section": "Раздел 1. Общая информация",
        "title": "Принадлежность к организационной структуре",
        "question": "Укажите всю цепочку подразделений, все уровни, без аббревиатур.",
        "example": "Например: Ректорат / Проректор по развитию процессов / Направление развития процессов / Отдел сопровождения процессов.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "administrative_manager",
        "section": "Раздел 1. Общая информация",
        "title": "Административный руководитель",
        "question": "Укажите должность и подразделение непосредственного руководителя по административной линии.",
        "example": "Формат: должность / подразделение.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "functional_manager",
        "section": "Раздел 1. Общая информация",
        "title": "Функциональный руководитель",
        "question": "Если функциональный руководитель отличается от административного, укажите должность и подразделение.",
        "example": "Если отличается - укажите; иначе напишите «совпадает».",
        "input_type": "text",
        "quick_answers": ["Совпадает."],
    },
    {
        "key": "direct_admin_reports",
        "section": "Раздел 1. Общая информация",
        "title": "Прямые административные подчиненные",
        "question": "Укажите должности и количество прямых административных подчиненных.",
        "example": "Например: специалист по сопровождению процессов - 8 чел.; аналитик - 2 чел. Если нет - «Нет».",
        "input_type": "text",
        "quick_answers": ["Нет."],
    },
    {
        "key": "total_reports",
        "section": "Раздел 1. Общая информация",
        "title": "Все подчиненные в подразделении",
        "question": "Укажите общее количество сотрудников во всей вертикали подчинения.",
        "example": "Число сотрудников во всех уровнях подчинения.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "functional_reports",
        "section": "Раздел 1. Общая информация",
        "title": "Функциональные подчиненные",
        "question": "Укажите количество сотрудников по функциональному направлению вне прямого подчинения.",
        "example": "Если нет функционального подчинения, напишите «Нет».",
        "input_type": "text",
        "quick_answers": ["Нет."],
    },
    {
        "key": "completion_date",
        "section": "Раздел 1. Общая информация",
        "title": "Дата заполнения",
        "question": "Укажите дату заполнения профиля.",
        "example": "Формат: дд.мм.гггг.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "position_purpose",
        "section": "Раздел 2. Цель должности",
        "title": "Цель должности",
        "question": "Для чего создана эта должность в университете? Ответьте в 1-3 предложениях.",
        "example": "Что стало бы хуже или не работало, если бы этой должности не было?",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "duties_results",
        "section": "Раздел 3. Обязанности и функциональные области",
        "title": "5-8 основных обязанностей через результат",
        "question": "Заполните обязанности или функциональные области и результат для университета.",
        "example": "Обязанность: «Разрабатывает систему мониторинга». Результат: «Руководители получают данные для решений».",
        "input_type": "table",
        "columns": ["Обязанность / функциональная область", "Результат для университета"],
        "rows": 8,
        "quick_answers": [],
    },
    {
        "key": "income_responsibility",
        "section": "Раздел 4. Бюджетная ответственность",
        "title": "Ответственность за доходы / привлечение финансирования",
        "question": "Есть ли план по генерации доходов или привлечению финансирования? Если да, укажите оценочный объем в руб./год.",
        "example": "Гранты, контракты, ДПО и т.п. Если нет - укажите «Не применимо».",
        "input_type": "textarea",
        "quick_answers": ["Не применимо."],
    },
    {
        "key": "expense_budget_type",
        "section": "Раздел 4. Бюджетная ответственность",
        "title": "Тип бюджета расходов",
        "question": "Укажите тип бюджета, с которым связана должность.",
        "example": "ФОТ / операционный / инвестиционный / иное.",
        "input_type": "single_choice",
        "options": [
            {"label": "ФОТ", "description": "Фонд оплаты труда."},
            {"label": "Операционный", "description": "Текущие расходы на регулярную деятельность."},
            {"label": "Инвестиционный", "description": "Развитие, закупки, проекты или капитальные вложения."},
            {"label": "Иное", "description": "Бюджет есть, но не относится к основным типам."},
            {"label": "Не применимо.", "description": "Должность не связана с бюджетом расходов."},
        ],
        "quick_answers": [],
    },
    {
        "key": "expense_budget_volume",
        "section": "Раздел 4. Бюджетная ответственность",
        "title": "Объем бюджета",
        "question": "Укажите сумму или диапазон бюджета расходов в рублях в год.",
        "example": "До 10 млн / 10-100 млн / 100 млн - 1 млрд / свыше 1 млрд.",
        "input_type": "single_choice",
        "options": [
            {"label": "До 10 млн", "description": "Небольшой бюджет расходов в год."},
            {"label": "10-100 млн", "description": "Средний бюджет расходов в год."},
            {"label": "100 млн - 1 млрд", "description": "Крупный бюджет расходов в год."},
            {"label": "Свыше 1 млрд", "description": "Очень крупный бюджет расходов в год."},
            {"label": "Не применимо.", "description": "У должности нет бюджета расходов."},
        ],
        "quick_answers": [],
    },
    {
        "key": "expense_budget_management",
        "section": "Раздел 4. Бюджетная ответственность",
        "title": "Характер управления бюджетом",
        "question": "Укажите характер полномочий по бюджету расходов.",
        "example": "Полная ответственность / участие в формировании и согласовании / контроль соблюдения.",
        "input_type": "single_choice",
        "options": [
            {
                "label": "Полная ответственность",
                "description": "Самостоятельно отвечает за бюджет и результат его использования.",
            },
            {
                "label": "Участие в формировании и согласовании",
                "description": "Готовит, обосновывает или согласует бюджет, но не владеет им полностью.",
            },
            {
                "label": "Контроль соблюдения",
                "description": "Следит за лимитами, правилами расходования или исполнением бюджета.",
            },
            {"label": "Не применимо.", "description": "Должность не управляет бюджетом расходов."},
        ],
        "quick_answers": [],
    },
    {
        "key": "task_typicality",
        "section": "Раздел 5. Сложность задач и принимаемых решений",
        "title": "Типичность задач",
        "question": "Выберите один вариант, который лучше всего характеризует большинство ваших задач.",
        "example": "В шаблоне это поле заполняется отметкой X или ✓ в нужной строке.",
        "input_type": "single_choice",
        "options": [
            {
                "label": "Стандартные",
                "description": "Задачи повторяются, решаются по установленным правилам и процедурам.",
            },
            {
                "label": "Типовые с вариациями",
                "description": "Задачи знакомы, но каждый раз требуют адаптации. Есть ориентиры, но готовых решений нет.",
            },
            {
                "label": "Сложные / нестандартные",
                "description": "Значительная часть задач не имеет готовых решений. Нужно анализировать и действовать в неопределенности.",
            },
            {
                "label": "Уникальные / пионерские",
                "description": "Большинство задач решаются впервые, прецедентов нет ни внутри университета, ни на рынке.",
            },
        ],
        "quick_answers": [],
    },
    {
        "key": "complex_task_example",
        "section": "Раздел 5. Сложность задач и принимаемых решений",
        "title": "Пример наиболее сложной задачи",
        "question": "Опишите 1-2 наиболее трудные задачи за последний год: что делало их сложными и как они решались.",
        "example": "Ключевой вопрос для оценки должности: нужны сложность, неопределенность и способ решения.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "external_interactions",
        "section": "Раздел 6. Коммуникации и взаимодействие",
        "title": "Взаимодействие во внешней среде",
        "question": "Укажите внешние организации или должности, тему взаимодействия и цель / результат.",
        "example": "Минобрнауки - согласование отчетности; отраслевые партнеры - совместные программы.",
        "input_type": "table",
        "columns": ["Организация / должность", "Тема взаимодействия", "Цель / результат"],
        "rows": 5,
        "quick_answers": [],
    },
    {
        "key": "internal_interactions",
        "section": "Раздел 6. Коммуникации и взаимодействие",
        "title": "Взаимодействие во внутренней среде",
        "question": "Укажите должности / подразделения внутри университета, тему и цель взаимодействия.",
        "example": "С кем внутри университета должность взаимодействует наиболее тесно.",
        "input_type": "table",
        "columns": ["Должность / подразделение", "Тема взаимодействия", "Цель / результат"],
        "rows": 6,
        "quick_answers": [],
    },
    {
        "key": "government_interactions",
        "section": "Раздел 6. Коммуникации и взаимодействие",
        "title": "Взаимодействие с государственными органами",
        "question": "Укажите государственные органы или органы надзора и характер взаимодействия.",
        "example": "Если такого взаимодействия нет, напишите «Не применимо».",
        "input_type": "textarea",
        "quick_answers": ["Не применимо."],
    },
    {
        "key": "independent_decisions",
        "section": "Раздел 7. Полномочия и принятие решений",
        "title": "Решения, принимаемые самостоятельно",
        "question": "Опишите решения, которые принимаются без согласования с руководителем.",
        "example": "Выбор метода работы, приоритизация задач, оперативные решения, распределение задач в команде.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "approval_decisions",
        "section": "Раздел 7. Полномочия и принятие решений",
        "title": "Решения, требующие согласования",
        "question": "Опишите решения, которые готовятся или инициируются, но требуют одобрения вышестоящего руководителя.",
        "example": "Годовой бюджет, изменения оргструктуры, крупные партнерства, политики университета.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "education",
        "section": "Раздел 8. Требования к должности",
        "title": "Образование",
        "question": "Выберите минимальный уровень образования, необходимый для выполнения обязанностей.",
        "example": "В шаблоне это поле заполняется отметкой X или ✓.",
        "input_type": "single_choice",
        "options": [
            {"label": "Среднее общее", "description": ""},
            {"label": "Среднее специальное / среднее профессиональное", "description": ""},
            {"label": "Неполное высшее", "description": ""},
            {"label": "Высшее (бакалавр / специалист / магистр)", "description": ""},
            {"label": "MBA", "description": ""},
            {"label": "Учёная степень (кандидат / доктор наук)", "description": ""},
        ],
        "quick_answers": [],
    },
    {
        "key": "specialization",
        "section": "Раздел 8. Требования к должности",
        "title": "Специализация / квалификация",
        "question": "Укажите направление подготовки, профиль или квалификацию.",
        "example": "Например: Управление персоналом, Экономика, Юриспруденция.",
        "input_type": "text",
        "quick_answers": [],
    },
    {
        "key": "certification",
        "section": "Раздел 8. Требования к должности",
        "title": "Сертификация",
        "question": "Укажите обязательные сертификаты, лицензии или допуски.",
        "example": "Если сертификация не нужна, укажите «Не требуется».",
        "input_type": "text",
        "quick_answers": ["Не требуется."],
    },
    {
        "key": "legal_knowledge",
        "section": "Раздел 8. Требования к должности",
        "title": "Знание законодательства",
        "question": "Укажите конкретные законы и нормативные акты, необходимые для должности.",
        "example": "Например: ТК РФ, 44-ФЗ, Закон об образовании, ФЗ о госзакупках.",
        "input_type": "textarea",
        "quick_answers": ["Не требуется."],
    },
    {
        "key": "methods_knowledge",
        "section": "Раздел 8. Требования к должности",
        "title": "Знание методик и практик",
        "question": "Укажите методики, практики и подходы, необходимые для работы.",
        "example": "Например: Hay Group, PMBOK, Agile, методы оценки персонала, бюджетирование.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "technology_knowledge",
        "section": "Раздел 8. Требования к должности",
        "title": "Знание программ и технологий",
        "question": "Укажите программы, инструменты и технологии, необходимые для должности.",
        "example": "Например: 1С:ЗУП, SAP, Excel, Power BI, AutoCAD.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "domain_context_knowledge",
        "section": "Раздел 8. Требования к должности",
        "title": "Знание текущей ситуации в функциональной области",
        "question": "Укажите тенденции, конкурентную среду или нормативные изменения, важные для роли.",
        "example": "Тенденции рынка труда / отрасли, конкурентная среда, ключевые нормативные изменения.",
        "input_type": "textarea",
        "quick_answers": [],
    },
    {
        "key": "experience_requirements",
        "section": "Раздел 8. Требования к должности",
        "title": "Опыт",
        "question": "Укажите профессиональный и управленческий опыт, годы и специализацию.",
        "example": "Для управленческого опыта уточните коллективы, проекты или ресурсы.",
        "input_type": "table",
        "columns": ["Вид опыта", "Лет (от)", "Описание / специализация"],
        "row_labels": ["Профессиональный", "Управленческий"],
        "rows": 2,
        "quick_answers": [],
    },
    {
        "key": "comments",
        "section": "Раздел 9. Комментарии и дополнения",
        "title": "Комментарии и дополнения",
        "question": "Добавьте вопросы, уточнения или важную информацию о должности, не вошедшую в предыдущие разделы.",
        "example": "Если дополнений нет, можно указать «Дополнений нет».",
        "input_type": "textarea",
        "quick_answers": ["Дополнений нет."],
    },
]
QUESTION_KEYS = {question["key"] for question in PROFILE_QUESTIONS}
AI_CHECKABLE_QUESTION_KEYS = {
    question["key"] for question in PROFILE_QUESTIONS if question["input_type"] != "single_choice"
}
EDITABLE_STATUSES = {"not_started", "draft", "submitted", "returned_for_revision"}


class ProfileOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    session: Session,
    actor: Employee,
    action: str,
    entity_id: int,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type="employee_profile",
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


def _question_settings_by_key(session: Session) -> dict[str, QuestionnaireQuestionSetting]:
    return {
        setting.question_key: setting
        for setting in session.scalars(select(QuestionnaireQuestionSetting)).all()
    }


def _question_with_settings(
    question: dict[str, object],
    setting: QuestionnaireQuestionSetting | None,
) -> dict[str, object]:
    checkable = question["key"] in AI_CHECKABLE_QUESTION_KEYS
    configured_good_example = setting.good_example if setting else None
    configured_requirements = setting.requirements if setting else None
    return {
        **question,
        "example": configured_good_example or question["example"],
        "good_example": configured_good_example or question["example"],
        "bad_example": setting.bad_example if setting else None,
        "requirements": configured_requirements or _default_answer_requirements(question),
        "ai_check_enabled": checkable and (setting.ai_check_enabled if setting else True),
    }


def _default_answer_requirements(question: dict[str, object]) -> str:
    if question["input_type"] == "table":
        return "Заполните таблицу по смыслу вопроса и указанным строкам."
    return (
        f"Ответ должен прямо отвечать на вопрос «{question['question']}». "
        f"Ориентир: {question['example']}"
    )


def get_effective_profile_questions(session: Session) -> list[dict[str, object]]:
    settings = _question_settings_by_key(session)
    return [
        _question_with_settings(question, settings.get(str(question["key"])))
        for question in PROFILE_QUESTIONS
    ]


def get_questionnaire_settings(session: Session) -> dict[str, object]:
    settings = _question_settings_by_key(session)
    questions = []
    for question in PROFILE_QUESTIONS:
        if question["key"] not in AI_CHECKABLE_QUESTION_KEYS:
            continue
        setting = settings.get(str(question["key"]))
        effective = _question_with_settings(question, setting)
        questions.append(
            {
                "question_key": question["key"],
                "section": question["section"],
                "title": question["title"],
                "input_type": question["input_type"],
                "question": question["question"],
                "base_example": question["example"],
                "ai_check_enabled": effective["ai_check_enabled"],
                "good_example": effective["good_example"],
                "bad_example": effective["bad_example"],
                "requirements": effective["requirements"],
                "updated_at": setting.updated_at.isoformat() if setting and setting.updated_at else None,
                "updated_by_id": setting.updated_by_id if setting else None,
            }
        )
    return {
        "scope": "global_current_questionnaire",
        "versioning_status": "not_versioned_yet",
        "questions": questions,
    }


def update_questionnaire_settings(
    session: Session,
    actor: Employee,
    request: QuestionnaireSettingsUpdate,
) -> dict[str, object]:
    incoming_keys = {item.question_key for item in request.questions}
    unknown_keys = incoming_keys - AI_CHECKABLE_QUESTION_KEYS
    if unknown_keys:
        raise ProfileOperationError("Настраивать можно только открытые вопросы анкеты.", 422)

    existing = _question_settings_by_key(session)
    now = _now()
    changed = []
    for item in request.questions:
        setting = existing.get(item.question_key)
        if setting is None:
            setting = QuestionnaireQuestionSetting(question_key=item.question_key)
            session.add(setting)
        setting.ai_check_enabled = item.ai_check_enabled
        setting.good_example = item.good_example
        setting.bad_example = item.bad_example
        setting.requirements = item.requirements
        setting.updated_by_id = actor.id
        setting.updated_at = now
        changed.append(item.question_key)
    session.flush()
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="settings.questionnaire_answers_updated",
            entity_type="questionnaire_settings",
            entity_id="current",
            details_json=json.dumps(
                {
                    "changed_question_keys": changed,
                    "policy": "global_settings_before_questionnaire_versioning",
                },
                ensure_ascii=False,
            ),
        )
    )
    return get_questionnaire_settings(session)


def _answers_from_draft(profile: EmployeeProfile) -> dict[str, str]:
    if profile.draft is None:
        return {}
    return json.loads(profile.draft.answers_json)


def _answers_for_profile(profile: EmployeeProfile) -> dict[str, str]:
    answers = _prefilled_section_one_answers(profile)
    answers.update(_answers_from_draft(profile))
    return answers


def _prefilled_section_one_answers(profile: EmployeeProfile) -> dict[str, str]:
    assignment = profile.participant.assignment
    line = assignment.staffing_line
    unit = line.org_unit
    manager = assignment.manager
    manager_label = "Нет."
    if manager is not None:
        manager_line = manager.staffing_line
        manager_label = f"{manager_line.title} / {manager_line.org_unit.name}"

    direct_reports = len(assignment.reports)
    return {
        "position_name": line.title,
        "org_structure": _visible_org_path(unit.path),
        "administrative_manager": manager_label,
        "functional_manager": "Совпадает.",
        "direct_admin_reports": f"{direct_reports} чел." if direct_reports else "Нет.",
        "total_reports": f"{direct_reports} чел." if direct_reports else "Нет.",
        "functional_reports": "Нет.",
        "completion_date": _now().strftime("%d.%m.%Y"),
    }


def _visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def _is_answer_filled(question: dict[str, object], answer: str) -> bool:
    if not answer.strip():
        return False
    if question.get("input_type") == "single_choice":
        return answer in _single_choice_labels(question)
    if question.get("input_type") != "table":
        return True
    try:
        rows = json.loads(answer)
    except json.JSONDecodeError:
        return True
    if not isinstance(rows, list):
        return False
    return any(
        isinstance(row, list)
        and any(isinstance(cell, str) and cell.strip() for cell in row)
        for row in rows
    )


def _single_choice_labels(question: dict[str, object]) -> set[str]:
    return {
        str(option.get("label", ""))
        for option in question.get("options", [])
        if isinstance(option, dict)
    }


def _validate_answers(answers: dict[str, str]) -> None:
    invalid = [
        question["title"]
        for question in PROFILE_QUESTIONS
        if question.get("input_type") == "single_choice"
        and answers.get(question["key"], "").strip()
        and answers.get(question["key"], "") not in _single_choice_labels(question)
    ]
    if invalid:
        raise ProfileOperationError(
            "Выберите допустимый вариант в полях: " + ", ".join(invalid) + ".",
            422,
        )


def _assistant_payload(request: ProfileAnswersRequest, fallback_mode: str) -> tuple[str, str, str]:
    checked = [key for key in request.ai_checked_questions if key in QUESTION_KEYS]
    ignored = [key for key in request.ai_ignored_questions if key in QUESTION_KEYS and key in checked]
    without_ai = [
        key
        for key in request.ai_without_ai_questions
        if key in QUESTION_KEYS and key not in checked and key not in ignored
    ]
    used = bool(checked or without_ai)
    if not used:
        return fallback_mode, "none" if fallback_mode == "off" else "partial", "[]"

    has_rejected = any(request.ai_answer_statuses.get(key) == "rejected" for key in checked if key not in ignored)
    if checked and len(ignored) == len(checked):
        assistance_level = "ignored"
    elif checked and not ignored and not without_ai and not has_rejected:
        assistance_level = "accepted"
    elif without_ai and not checked:
        assistance_level = "without_ai"
    else:
        assistance_level = "mixed"
    answer_statuses = {
        key: request.ai_answer_statuses.get(key, "accepted")
        for key in checked
    }
    for key in ignored:
        answer_statuses[key] = "ignored"
    answer_statuses.update({key: "without_ai" for key in without_ai})
    return (
        "ai_checked",
        assistance_level,
        json.dumps(
            {
                "checked_questions": checked,
                "ignored_questions": ignored,
                "without_ai_questions": without_ai,
                "answer_statuses": answer_statuses,
            },
            ensure_ascii=False,
        ),
    )


def _progress(answers: dict[str, str]) -> float:
    completed = sum(
        1
        for question in PROFILE_QUESTIONS
        if _is_answer_filled(question, answers.get(question["key"], ""))
    )
    return round(completed / len(PROFILE_QUESTIONS) * 100, 2)


def _get_owned_profile(session: Session, actor: Employee, profile_id: int) -> EmployeeProfile:
    profile = session.scalar(
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .where(EmployeeProfile.id == profile_id, Assignment.employee_id == actor.id)
        .options(
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.campaign),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(EmployeeProfile.draft),
            selectinload(EmployeeProfile.revisions),
            selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.revision),
            selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.actor),
        )
    )
    if profile is None:
        raise ProfileOperationError("Профиль не найден или недоступен.", 404)
    return profile


def _ensure_profile(session: Session, participant: CampaignParticipant) -> EmployeeProfile:
    if participant.profile is not None:
        return participant.profile
    profile = EmployeeProfile(campaign_participant_id=participant.id)
    session.add(profile)
    session.flush()
    participant.profile = profile
    return profile


def _serialize_profile(
    profile: EmployeeProfile,
    questions: list[dict[str, object]],
) -> dict[str, object]:
    participant = profile.participant
    assignment = participant.assignment
    line = assignment.staffing_line
    revisions = sorted(profile.revisions, key=lambda item: item.revision_no, reverse=True)
    return {
        "id": profile.id,
        "campaign_id": participant.campaign_id,
        "campaign_name": participant.campaign.name,
        "assignment_id": participant.assignment_id,
        "position_title": line.title,
        "unit_name": line.org_unit.name,
        "workflow_status": profile.workflow_status,
        "progress_percent": profile.progress_percent,
        "answers": _answers_for_profile(profile),
        "draft_assisted_sections": _draft_assisted_sections(profile.draft),
        "can_edit": profile.workflow_status in EDITABLE_STATUSES,
        "questions": questions,
        "review_events": [
            {
                "id": event.id,
                "revision_no": event.revision.revision_no,
                "action": event.action,
                "comment": event.comment,
                "actor_name": event.actor.full_name,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in sorted(profile.review_events, key=lambda item: item.id, reverse=True)
        ],
        "revisions": [
            {
                "id": revision.id,
                "revision_no": revision.revision_no,
                "submitted_at": revision.submitted_at.isoformat(),
                "assistant_mode": revision.assistant_mode,
                "assistance_level": revision.assistance_level,
                "assisted_sections": _assisted_sections(revision),
                "answers": json.loads(revision.answers_json),
            }
            for revision in revisions
        ],
    }


def _assisted_sections(revision: ProfileRevision) -> dict[str, object]:
    return _assisted_sections_from_json(revision.assisted_sections_json)


def _draft_assisted_sections(draft: ProfileDraft | None) -> dict[str, object]:
    return _assisted_sections_from_json(draft.ai_usage_json if draft is not None else "{}")


def _assisted_sections_from_json(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"checked_questions": [], "ignored_questions": [], "without_ai_questions": [], "answer_statuses": {}}
    if isinstance(payload, dict):
        return {
            "checked_questions": payload.get("checked_questions", []),
            "ignored_questions": payload.get("ignored_questions", []),
            "without_ai_questions": payload.get("without_ai_questions", []),
            "answer_statuses": payload.get("answer_statuses", {}),
        }
    if isinstance(payload, list):
        return {"checked_questions": payload, "ignored_questions": [], "without_ai_questions": [], "answer_statuses": {}}
    return {"checked_questions": [], "ignored_questions": [], "without_ai_questions": [], "answer_statuses": {}}


def get_my_profiles(session: Session, actor: Employee) -> list[dict[str, object]]:
    participants = session.scalars(
        select(CampaignParticipant)
        .join(CampaignParticipant.assignment)
        .join(CampaignParticipant.campaign)
        .where(
            Assignment.employee_id == actor.id,
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
            Campaign.status == "active",
        )
        .options(
            selectinload(CampaignParticipant.campaign),
            selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(CampaignParticipant.profile).selectinload(EmployeeProfile.draft),
            selectinload(CampaignParticipant.profile).selectinload(EmployeeProfile.revisions),
            selectinload(CampaignParticipant.profile)
            .selectinload(EmployeeProfile.review_events)
            .selectinload(ProfileReviewEvent.revision),
            selectinload(CampaignParticipant.profile)
            .selectinload(EmployeeProfile.review_events)
            .selectinload(ProfileReviewEvent.actor),
        )
        .order_by(CampaignParticipant.id.desc())
    ).all()
    profiles = [_ensure_profile(session, participant) for participant in participants]
    session.flush()
    questions = get_effective_profile_questions(session)
    return [_serialize_profile(profile, questions) for profile in profiles]


def save_draft(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ProfileAnswersRequest,
    assistant_mode: str,
) -> dict[str, object]:
    profile = _get_owned_profile(session, actor, profile_id)
    if profile.workflow_status not in EDITABLE_STATUSES:
        raise ProfileOperationError("Профиль заблокирован для редактирования.", 409)
    unknown_keys = set(request.answers) - QUESTION_KEYS
    if unknown_keys:
        raise ProfileOperationError("Переданы неизвестные разделы анкеты.")

    answers = {key: request.answers.get(key, "") for key in QUESTION_KEYS}
    _validate_answers(answers)
    now = _now()
    assistant_payload = _assistant_payload(request, assistant_mode)
    if profile.draft is None:
        profile.draft = ProfileDraft(
            answers_json=json.dumps(answers, ensure_ascii=False),
            ai_usage_json=assistant_payload[2],
            updated_at=now,
        )
    else:
        profile.draft.answers_json = json.dumps(answers, ensure_ascii=False)
        profile.draft.ai_usage_json = assistant_payload[2]
        profile.draft.updated_at = now
    if profile.started_at is None:
        profile.started_at = now
    profile.last_activity_at = now
    profile.progress_percent = _progress(answers)
    profile.workflow_status = "draft"
    _audit(
        session,
        actor,
        "profile.draft_saved",
        profile.id,
        {
            "progress_percent": profile.progress_percent,
            "assistant_mode": assistant_payload[0],
            "ai_checked_questions": request.ai_checked_questions,
            "ai_ignored_questions": request.ai_ignored_questions,
            "ai_without_ai_questions": request.ai_without_ai_questions,
        },
    )
    session.flush()
    return _serialize_profile(profile, get_effective_profile_questions(session))


def submit_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ProfileAnswersRequest,
    assistant_mode: str,
) -> dict[str, object]:
    profile = _get_owned_profile(session, actor, profile_id)
    if profile.workflow_status not in EDITABLE_STATUSES:
        raise ProfileOperationError("Профиль заблокирован для отправки.", 409)
    unknown_keys = set(request.answers) - QUESTION_KEYS
    if unknown_keys:
        raise ProfileOperationError("Переданы неизвестные разделы анкеты.")
    answers = {key: request.answers.get(key, "") for key in QUESTION_KEYS}
    _validate_answers(answers)
    missing = [
        question["title"]
        for question in PROFILE_QUESTIONS
        if not _is_answer_filled(question, answers.get(question["key"], ""))
    ]
    if missing:
        raise ProfileOperationError(
            "Перед отправкой заполните разделы: " + ", ".join(missing) + ".",
            422,
        )

    now = _now()
    revision_assistant_mode, assistance_level, assisted_sections_json = _assistant_payload(
        request,
        assistant_mode,
    )
    if profile.draft is None:
        profile.draft = ProfileDraft(
            answers_json=json.dumps(answers, ensure_ascii=False),
            ai_usage_json=assisted_sections_json,
            updated_at=now,
        )
    else:
        profile.draft.answers_json = json.dumps(answers, ensure_ascii=False)
        profile.draft.ai_usage_json = assisted_sections_json
        profile.draft.updated_at = now
    next_number = max((revision.revision_no for revision in profile.revisions), default=0) + 1
    prior = max(profile.revisions, key=lambda item: item.revision_no, default=None)
    revision = ProfileRevision(
        profile=profile,
        revision_no=next_number,
        based_on_revision_id=prior.id if prior else None,
        answers_json=json.dumps(answers, ensure_ascii=False),
        submitted_at=now,
        assistant_mode=revision_assistant_mode,
        assistance_level=assistance_level,
        assisted_sections_json=assisted_sections_json,
        ai_check_status="not_run",
    )
    session.add(revision)
    profile.workflow_status = "submitted"
    profile.progress_percent = 100
    profile.last_activity_at = now
    if profile.started_at is None:
        profile.started_at = now
    _audit(
        session,
        actor,
        "profile.submitted",
        profile.id,
        {
            "revision_no": next_number,
            "assistant_mode": revision.assistant_mode,
            "assistance_level": revision.assistance_level,
            "ai_checked_questions": request.ai_checked_questions,
            "ai_ignored_questions": request.ai_ignored_questions,
        },
    )
    session.flush()
    return _serialize_profile(profile, get_effective_profile_questions(session))
