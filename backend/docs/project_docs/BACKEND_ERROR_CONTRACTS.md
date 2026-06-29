# Backend error contracts

Короткий каталог фиксирует текущие backend operation error-контракты для API-слоя. Цель каталога — сохранить предсказуемые `status_code` и `detail` для frontend и тестов, а не исправить все найденные gaps.

## Единый API-helper

- `backend/app/api/errors.py::run_operation` — единая точка преобразования feature operation errors в `fastapi.HTTPException`.
- Response shape не меняется: FastAPI продолжает отдавать стандартный `{"detail": "..."}`.
- Helper сохраняет `exc.status_code` и `exc.message` без нормализации текста.
- Auth dependency `current_actor` также пропускает `AuthOperationError` от `actor_from_authorization` через `run_operation`.

## Где используются статусы

### 401 Unauthorized

- Auth: некорректный/отсутствующий/истёкший session bearer token; невалидный логин/пароль; magic-link не найден или истёк.
- Dependency fallback: вне `demo-local`/`test` без валидной сессии — `"Войдите по одноразовой ссылке."`; в demo/test без выбранного пользователя — `"Войдите или выберите пользователя."`.

### 403 Forbidden

- Auth: отключенный пользователь.
- Dependencies: выбранный demo-пользователь не найден; `current_hr` требует HR-доступ.
- Feature-зоны: manager review, HR review, manager overview, document registry, demo reset ограничивают действия по роли/зоне.

### 404 Not Found

- Auth: email не найден при запросе magic link.
- Profiles/exports/reviews: профиль не найден или недоступен.
- Campaigns: кампания, волна, ветка структуры или назначения не найдены в выбранном контуре.
- Documents: рабочий документ, оригинал, штатная позиция или документ нужного типа не найдены/недоступны.
- Structure: позиция, назначение, штатная строка или рабочее подразделение не найдены.
- Notifications: уведомление не найдено.

### 409 Conflict

- Auth: magic link уже использован.
- Profiles/reviews/campaigns: действие не разрешено текущим статусом профиля/волны.
- Documents: дубликат документа или оригинала.
- Structure: дубликаты сотрудников/email/штатных строк; удаление или изменение заблокировано активной волной.

### 422 Unprocessable Entity

- Campaigns: запуск волны без участников; выдача доступов без новых участников.
- Profiles/AI checks/questionnaire: неизвестный вопрос, недопустимый тип вопроса для AI check, пустой ответ для проверки, неизвестные секции анкеты, настройки только для открытых вопросов.
- Pydantic schemas также возвращают 422 для validation errors; это не operation error mapping.

### 500 Internal Server Error

- Auth email: SMTP не настроен.
- Exports: Excel-шаблон профиля не найден.
- Непойманные exceptions остаются 500 и не должны маскироваться `run_operation`, если это не feature operation error с существующим контрактом.

## 404, скрывающие существование объекта

404 намеренно используется не только для отсутствующих объектов, но и для недоступных объектов, чтобы не раскрывать существование данных вне зоны пользователя:

- `"Профиль не найден или недоступен."` в profiles/exports.
- `"Профиль подчиненного не найден или недоступен."` и bulk-варианты `"Один или несколько профилей недоступны руководителю."`.
- HR review: `"Профиль для HR-проверки не найден."`, `"Один или несколько профилей недоступны HR."`, `"Подразделение недоступно HR."`.
- Campaign/document/structure work-scope ошибки с формулировками `не найдена` / `не найден` также используются как граница выбранного demo/work контура.

## Feature-зоны и error classes

- `auth` → `AuthOperationError`: 401/403/404/409/500/502.
- `profiles` → `ProfileOperationError`, `AiProfileCheckError`: 404/409/422 и default 400.
- `manager_reviews` → `ReviewOperationError`: 403/404/409.
- `hr_reviews` → `HrReviewOperationError`: 404/409.
- `analytics` → `ManagerOverviewError`: 403.
- `exports` → `ExportOperationError`: 404/500.
- `documents` → `DocumentOperationError`: 403/404/409 и default 400.
- `campaigns` → `CampaignOperationError`: 404/409/422.
- `settings/demo reset` → `DemoResetError`: 403.
- `imports/work_employee` → `WorkEmployeeImportError`: default 400.
- `notifications` → `NotificationOperationError`: 404.
- `structure` → `StructureOperationError`: 404/409 and default 400.

## Зафиксированные gaps, не исправленные в этой задаче

- `organization` router/service не использует operation error mapping и пока работает без dedicated operation error class.
- `structure` read-only manager endpoints вызывают `get_manager_options` напрямую; на момент каталога там нет `StructureOperationError`, поэтому подключение к helper не требовалось.
- Validation errors из Pydantic schemas остаются стандартными 422 FastAPI и не проходят через `run_operation`.
- `imports/grades_documents.py` конвертирует часть import errors в `RuntimeError`; это не подключено к текущему API operation mapping.
