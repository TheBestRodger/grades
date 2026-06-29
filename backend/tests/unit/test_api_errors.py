from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.errors import run_operation
from app.features.analytics.errors import ManagerOverviewError
from app.features.auth.errors import AuthOperationError
from app.features.campaigns.errors import CampaignOperationError
from app.features.documents.errors import DocumentOperationError
from app.features.exports.errors import ExportOperationError
from app.features.hr_reviews.errors import HrReviewOperationError
from app.features.imports.work_employee import WorkEmployeeImportError
from app.features.manager_reviews.errors import ReviewOperationError
from app.features.notifications.errors import NotificationOperationError
from app.features.profiles.errors import AiProfileCheckError, ProfileOperationError
from app.features.settings.demo_reset import DemoResetError
from app.features.structure.errors import StructureOperationError


@pytest.mark.parametrize(
    ("error", "status_code", "message"),
    [
        (
            AuthOperationError("Неверный логин или пароль.", 401),
            401,
            "Неверный логин или пароль.",
        ),
        (
            AuthOperationError("Пользователь отключен.", 403),
            403,
            "Пользователь отключен.",
        ),
        (
            AuthOperationError("Пользователь с таким email не найден.", 404),
            404,
            "Пользователь с таким email не найден.",
        ),
        (
            AuthOperationError("Ссылка входа уже использована.", 409),
            409,
            "Ссылка входа уже использована.",
        ),
        (
            AuthOperationError(
                "SMTP не настроен: задайте SMTP_HOST и SMTP_FROM_EMAIL.", 500
            ),
            500,
            "SMTP не настроен: задайте SMTP_HOST и SMTP_FROM_EMAIL.",
        ),
        (
            ProfileOperationError("Профиль не найден или недоступен.", 404),
            404,
            "Профиль не найден или недоступен.",
        ),
        (
            ReviewOperationError("Действие доступно только руководителю.", 403),
            403,
            "Действие доступно только руководителю.",
        ),
        (
            HrReviewOperationError(
                "Все выбранные профили должны быть подтверждены руководителем.", 409
            ),
            409,
            "Все выбранные профили должны быть подтверждены руководителем.",
        ),
        (
            ManagerOverviewError("Обзор доступен только руководителю.", 403),
            403,
            "Обзор доступен только руководителю.",
        ),
        (
            ExportOperationError("Excel-шаблон профиля не найден.", 500),
            500,
            "Excel-шаблон профиля не найден.",
        ),
        (
            DocumentOperationError("Документ с таким кодом уже существует.", 409),
            409,
            "Документ с таким кодом уже существует.",
        ),
        (
            DemoResetError("Сброс данных доступен только HR.", 403),
            403,
            "Сброс данных доступен только HR.",
        ),
        (WorkEmployeeImportError("Файл импорта пуст."), 400, "Файл импорта пуст."),
        (
            AiProfileCheckError("Неизвестный вопрос анкеты.", 422),
            422,
            "Неизвестный вопрос анкеты.",
        ),
        (
            CampaignOperationError(
                "Для запуска волны выберите минимум одного участника.", 422
            ),
            422,
            "Для запуска волны выберите минимум одного участника.",
        ),
        (
            NotificationOperationError("Уведомление не найдено.", 404),
            404,
            "Уведомление не найдено.",
        ),
        (
            StructureOperationError("Позиция не найдена.", 404),
            404,
            "Позиция не найдена.",
        ),
    ],
)
def test_run_operation_preserves_operation_error_status_and_message(
    error: Exception,
    status_code: int,
    message: str,
) -> None:
    def operation() -> None:
        raise error

    with pytest.raises(HTTPException) as raised:
        run_operation(operation)

    assert raised.value.status_code == status_code
    assert raised.value.detail == message
    assert raised.value.__cause__ is error


def test_run_operation_returns_successful_result_without_shape_changes() -> None:
    assert run_operation(lambda: {"ok": True}) == {"ok": True}
