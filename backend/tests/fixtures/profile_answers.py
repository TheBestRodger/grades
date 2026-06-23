from __future__ import annotations

import json


def complete_profile_answers() -> dict[str, str]:
    return {
        "functional_manager": "Совпадает.",
        "direct_admin_reports": "Нет.",
        "total_reports": "0",
        "functional_reports": "Нет.",
        "position_purpose": "Помогает выпускать изменения без критичных дефектов.",
        "duties_results": json.dumps(
            [["Проверяет сценарии", "Критичные дефекты выявляются до релиза."]],
            ensure_ascii=False,
        ),
        "income_responsibility": "Не применимо.",
        "expense_budget_type": "Не применимо.",
        "expense_budget_volume": "Не применимо.",
        "expense_budget_management": "Не применимо.",
        "task_typicality": "Типовые с вариациями",
        "complex_task_example": "Выбирает критичные сценарии проверки при ограниченном времени.",
        "external_interactions": json.dumps(
            [["Подрядчик", "Тестовая среда", "Готовность стенда согласована."]],
            ensure_ascii=False,
        ),
        "internal_interactions": json.dumps(
            [["Разработчики", "Дефекты", "Исправления проверены."]],
            ensure_ascii=False,
        ),
        "government_interactions": "Не применимо.",
        "independent_decisions": "Самостоятельно оформляет дефекты и выбирает порядок проверки.",
        "approval_decisions": "Выпуск и приоритеты согласует руководитель.",
        "education": "Высшее (бакалавр / специалист / магистр)",
        "specialization": "Информационные системы или смежное направление.",
        "certification": "Не требуется.",
        "legal_knowledge": "Не требуется.",
        "methods_knowledge": "Тест-дизайн, чек-листы, регрессионное тестирование.",
        "technology_knowledge": "Баг-трекер, офисные приложения, базовые SQL-запросы.",
        "domain_context_knowledge": "Понимание жизненного цикла внутренних информационных систем.",
        "experience_requirements": json.dumps(
            [
                ["Профессиональный", "2", "Тестирование информационных систем."],
                ["Управленческий", "0", "Не требуется для должности."],
            ],
            ensure_ascii=False,
        ),
        "comments": "Дополнений нет.",
    }
