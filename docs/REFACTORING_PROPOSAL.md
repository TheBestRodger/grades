# Предложение по рефакторингу и архитектурному паттерну

**Статус:** проектное предложение, без изменения поведения MVP  
**Дата фиксации:** 05.06.2026  
**Основание:** обзор текущего кода backend/frontend и обязательные правила проекта из `AGENTS.md`  
**Цель:** подготовить кодовую базу к безопасному расширению MVP без подключения внешних LLM, реальных интеграций и без поломки текущего локального сценария на SQLite.

## 1. Краткий вывод

Текущий MVP лучше сохранить как **модульный монолит**, но внутри него перейти к структуре **Clean Architecture / Hexagonal Architecture в прагматичном варианте**:

```text
HTTP/UI adapters -> application use-cases -> domain rules -> repositories -> DB/external adapters
```

Это не означает переписывание проекта. Предлагается постепенно вынести из крупных файлов маршруты, сценарии, доступ к БД, схемы и UI-фичи так, чтобы:

- backend оставался единственным местом проверки прав, статусов и переходов workflow;
- frontend только отображал разрешённые backend действия;
- сохранялась работа при `AI_MODE=off`;
- SQLite оставался основным demo-local хранилищем, а PostgreSQL можно было подключить позднее через тот же слой репозиториев и миграций;
- каждый этап рефакторинга был покрыт регрессионными тестами и мог быть откатан без потери бизнес-сценария.

## 2. Основные проблемы текущей структуры

### 2.1. Backend

1. **`backend/app/main.py` совмещает composition root и все HTTP-маршруты.**  
   В одном файле находятся создание приложения, lifespan, зависимости, обработчики ошибок и десятки endpoint-ов для auth, HR, work/demo контуров, документов, экспорта, профилей и review. Это затрудняет локальные изменения, ревью и тестирование отдельных API-групп.

2. **Файлы `*_operations.py` фактически являются смесью use-case, repository и domain logic.**  
   Например, HR-операции одновременно валидируют бизнес-правила, строят SQLAlchemy-запросы, создают audit-записи и формируют API-ответы. Такой подход быстрый для MVP, но усложняет повторное использование логики и проверку инвариантов.

3. **Нет явной границы между доменной моделью и ORM-моделью.**  
   `backend/app/models.py` сейчас является единственным центром сущностей БД. Доменным правилам приходится напрямую оперировать SQLAlchemy-объектами, поэтому правила статусов, ставок, демо/рабочего контура и версионности размазаны по операциям.

4. **`backend/app/schemas.py` стал общим контейнером всех Pydantic-схем.**  
   С ростом числа API-контрактов один файл будет провоцировать конфликты, циклические знания между доменами и неочевидные зависимости.

5. **Дублирование demo/work endpoint-ов и сценариев.**  
   В `main.py` есть параллельные маршруты `/api/hr/...` и `/api/work/hr/...`, которые часто отличаются только `is_demo`. Это повышает риск, что правка попадёт в один контур и не попадёт в другой.

6. **Audit создаётся локальными helper-функциями в разных модулях.**  
   Для проекта критично сохранять версии, возвраты, подтверждения, смены статусов и привязки документов. Поэтому audit лучше сделать отдельным application-сервисом или unit-of-work hook, а не набором частных `_audit` функций.

7. **Слой AI уже выделен частично, но правила обезличивания и допустимого контекста должны оставаться на application/domain уровне.**  
   Gateway может быть адаптером, но он не должен сам решать, какие персональные данные можно передавать.

### 2.2. Frontend

1. **`frontend/src/App.tsx` является сверхкрупным контейнером приложения.**  
   В нём смешаны авторизация, выбор пользователя/контура, загрузка данных, состояния модалок, обработчики HR/manager/employee действий, навигация и layout.

2. **Компоненты панелей слишком много знают о форме данных и сценариях.**  
   Например, рабочее место профиля, HR-контролы и документы содержат одновременно UI-разметку, локальную бизнес-валидацию, derived-state и вызовы API.

3. **`frontend/src/api.ts` — единый список всех HTTP-вызовов.**  
   При росте API этот файл становится точкой конфликтов и не даёт явно увидеть принадлежность endpoint-а к фиче: auth, profiles, HR campaigns, documents, exports, settings.

4. **`frontend/src/types.ts` — единый контейнер всех типов.**  
   Типы разных доменов связаны через один файл, поэтому сложно менять контракт одной фичи без риска затронуть весь UI.

5. **Frontend местами дублирует бизнес-ограничения.**  
   Это допустимо как UX-подсказка, но любое правило статуса, доступа, валидности ответа, демо/рабочего контура и AI-допуска должно иметь backend-источник истины.

6. **Нет стандартизованного слоя hooks/state для серверных данных.**  
   Сейчас загрузка и мутации в основном управляются локальным состоянием компонентов. Даже если TanStack Query не внедрять сразу, стоит отделить `api` и `hooks`, чтобы позже заменить внутреннюю реализацию без изменения страниц.

## 3. Целевые зоны ответственности backend

Рекомендуемая структура:

```text
backend/app/
  main.py                       # только create_app, middleware, include_router, lifespan
  api/
    deps.py                     # get_session, current_actor, current_hr, error mapping
    routers/
      auth.py
      health.py
      organization.py
      hr_campaigns.py
      hr_settings.py
      hr_documents.py
      hr_exports.py
      hr_reviews.py
      manager_reviews.py
      my_profiles.py
      work_imports.py
  application/
    auth/use_cases.py
    campaigns/use_cases.py
    profiles/use_cases.py
    reviews/use_cases.py
    documents/use_cases.py
    analytics/use_cases.py
    exports/use_cases.py
    settings/use_cases.py
    audit_service.py
    unit_of_work.py
  domain/
    auth.py
    campaign.py
    profile.py
    review.py
    organization.py
    document.py
    ai_policy.py
    errors.py
  infrastructure/
    db.py
    models.py
    repositories/
      employees.py
      organization.py
      campaigns.py
      profiles.py
      documents.py
      audit.py
    ai_gateway.py
    file_storage.py
    xlsx.py
  schemas/
    auth.py
    campaigns.py
    profiles.py
    reviews.py
    documents.py
    analytics.py
    settings.py
    common.py
  seed/
    demo_data.py
```

### 3.1. `api/routers`

Отвечают только за HTTP-адаптацию:

- объявление path/method/status codes;
- FastAPI `Depends`;
- чтение path/query/body параметров;
- вызов одного application use-case;
- перевод application/domain ошибок в HTTP-ответы;
- отсутствие SQLAlchemy-запросов и бизнес-ветвлений по статусам.

### 3.2. `application/use_cases`

Отвечают за сценарии приложения:

- orchestration нескольких репозиториев;
- транзакционная граница;
- проверка прав через domain-policy;
- вызов audit-сервиса;
- вызов AI/file/export адаптеров;
- возврат DTO для API.

Пример именования use-case функций:

```text
create_campaign(...)
launch_campaign_wave(...)
save_profile_draft(...)
submit_profile_revision(...)
return_profile_to_employee(...)
accept_profile_by_hr(...)
link_work_document(...)
```

### 3.3. `repositories / DB-access`

Отвечают только за хранение и выборки:

- SQLAlchemy `select`, `join`, `selectinload`, aggregate queries;
- создание/обновление ORM-объектов;
- отсутствие HTTP-исключений;
- отсутствие знания о frontend DTO;
- методы с понятной предметной семантикой: `get_active_wave`, `list_profiles_for_manager`, `save_revision`, `find_assignment_with_line`.

На первом этапе репозитории можно делать тонкими функциями, не обязательно классами. Классы пригодятся, когда появится `UnitOfWork` и PostgreSQL-пилот.

### 3.4. `schemas`

Pydantic-схемы стоит разнести по API-доменам:

- `schemas/auth.py` — login, magic link, session/user response;
- `schemas/campaigns.py` — campaign/wave/assignment requests;
- `schemas/profiles.py` — answers, revisions, questionnaire settings;
- `schemas/reviews.py` — manager/HR review requests;
- `schemas/documents.py` — registry, links, OCR quality, source;
- `schemas/settings.py` — AI/settings;
- `schemas/common.py` — общие enum/literal/response helpers.

Важно: схемы — это API-контракт, а не место доменных решений. Валидация формата допустима, бизнес-статусы и права — в application/domain.

### 3.5. `domain logic`

Доменный слой должен хранить чистые правила, которые можно тестировать без FastAPI и БД:

- допустимые переходы статусов профиля и кампании;
- расчёт свободной ставки на штатной строке;
- правила demo/work изоляции;
- правило «после сдачи не перезаписывать ответы, а создавать новую версию»;
- правила видимости и действий ролей;
- политика AI-контекста: что можно/нельзя передавать при будущих провайдерах;
- правила исключения demo-данных из рабочих KPI.

## 4. Целевые зоны ответственности frontend

Рекомендуемая структура:

```text
frontend/src/
  app/
    App.tsx
    routes.tsx
    providers.tsx
    layout/
  pages/
    LoginPage.tsx
    EmployeeProfilePage.tsx
    ManagerReviewPage.tsx
    ManagerOverviewPage.tsx
    HrDashboardPage.tsx
    HrSettingsPage.tsx
    DocumentsPage.tsx
  features/
    auth/
      api.ts
      hooks.ts
      types.ts
      ui/
    profile-questionnaire/
      api.ts
      hooks.ts
      types.ts
      ui/
      model/
    manager-review/
    hr-campaigns/
    hr-review/
    documents/
    analytics/
    settings/
  shared/
    api/
      client.ts
      errors.ts
    ui/
      Button.tsx
      Card.tsx
      Modal.tsx
      Badge.tsx
      Table.tsx
      EmptyState.tsx
    hooks/
      useDebouncedValue.ts
      useLocalStorage.ts
    types/
      common.ts
    lib/
      format.ts
      tree.ts
      dates.ts
```

### 4.1. `pages`

Страницы собирают фичи и layout:

- выбирают, какие виджеты показать;
- получают параметры маршрута/активного таба;
- не содержат сложной бизнес-валидации;
- не знают деталей HTTP endpoint-ов.

### 4.2. `features`

Фича содержит всё, что относится к одному пользовательскому сценарию:

- feature-specific components;
- hooks для загрузки/мутаций;
- локальные helper-ы derived-state;
- типы, относящиеся только к этой фиче;
- адаптеры API конкретной фичи.

Примеры фич:

- `profile-questionnaire` — анкета, черновик, submit, AI-check open answer;
- `hr-campaigns` — кампании, волны, включение/исключение участников;
- `documents` — реестр, покрытие, привязка, качество OCR;
- `manager-review` — очередь проверки, возвраты, подтверждение;
- `settings` — AI и questionnaire settings.

### 4.3. `shared`

`shared` должен быть предметно нейтральным:

- UI primitives без знания профилей/кампаний;
- общий API client;
- форматирование дат/чисел;
- общие хуки;
- общие типы вроде `Id`, `ApiError`, `Scope`.

### 4.4. `api layer`

Нужен один низкоуровневый `shared/api/client.ts`:

- добавляет bearer token;
- обрабатывает JSON/errors;
- поддерживает file upload/download;
- не знает о конкретных endpoint-ах фич.

Endpoint-функции должны жить рядом с фичей:

```text
features/auth/api.ts
features/profile-questionnaire/api.ts
features/hr-campaigns/api.ts
features/documents/api.ts
```

### 4.5. `hooks`

Даже без немедленного внедрения React Query стоит ввести hooks как стабильную границу:

```text
useCurrentUser()
useEmployeeProfiles()
useSaveProfileDraft()
useSubmitProfile()
useCampaigns(scope)
useDocumentRegistry(scope)
```

Позже внутри hook можно перейти с ручного `useEffect/useState` на TanStack Query, не меняя страницы.

### 4.6. `types`

Разделить типы по доменам:

- `features/auth/types.ts`;
- `features/profile-questionnaire/types.ts`;
- `features/hr-campaigns/types.ts`;
- `features/documents/types.ts`;
- `shared/types/common.ts`.

Типы API-ответов должны по возможности генерироваться из OpenAPI или сверяться контрактными тестами, чтобы frontend не расходился с backend.

## 5. Какие текущие файлы дробить первыми

### 5.1. Backend: приоритет 1

1. **`backend/app/main.py`**  
   Разнести endpoint-ы по `api/routers/*`, оставить в `main.py` только `create_app`, middleware, lifespan и подключение router-ов.

2. **`backend/app/schemas.py`**  
   Разделить по доменам после выноса router-ов, чтобы каждый router импортировал только свои схемы.

3. **`backend/app/hr_operations.py`**  
   Разделить на `campaigns`, `employees/staffing`, `audit/query` и отдельно вынести DB-access. Это один из наиболее рискованных модулей, потому что он влияет на кампании, назначения, ставки и права HR.

4. **`backend/app/profile_operations.py`**  
   Вынести доменные правила анкеты, сохранения черновика, сдачи версии, AI-usage и single-choice в отдельные функции, тестируемые без HTTP.

5. **`backend/app/document_operations.py` и `backend/app/export_operations.py`**  
   Разнести документный workflow, file storage и генерацию файлов. Сейчас эти зоны будут быстро расти при OCR/версионировании/экспортах.

### 5.2. Backend: приоритет 2

- `backend/app/models.py` — не дробить первым, чтобы не ломать миграции; сначала стабилизировать use-cases/repositories, потом при необходимости выделить model modules.
- `backend/app/seed.py` — позже разделить на demo seed, work fixtures и helpers.
- `backend/app/ai_gateway.py` — оставить адаптером, а AI policy вынести в domain/application до расширения LLM-контекста.

### 5.3. Frontend: приоритет 1

1. **`frontend/src/App.tsx`**  
   Сначала выделить страницы и layout, затем вынести обработчики по фичам. Не менять визуальный поток за один шаг.

2. **`frontend/src/api.ts`**  
   Сначала создать `shared/api/client.ts`, затем переносить endpoint-группы по одной фиче.

3. **`frontend/src/types.ts`**  
   Разнести типы только после переноса соответствующей API-группы, чтобы не получить большой конфликтный diff.

4. **`frontend/src/ProfileWorkspace.tsx`**  
   Разделить на `QuestionnaireForm`, `QuestionField`, `TableAnswer`, `AiAnswerCheck`, `RevisionHistory`, helpers `model/answers.ts`.

5. **`frontend/src/HrControls.tsx` и `frontend/src/DocumentPanel.tsx`**  
   Вынести формы, модалки, tree helpers и document controls в feature-модули.

### 5.4. Frontend: приоритет 2

- `OrganizationTreePanel.tsx` — вынести tree filtering/selection helpers и переиспользуемые строки дерева.
- `ManagerReviewPanel.tsx`, `HrReviewPanel.tsx`, `ManagerOverviewPanel.tsx` — унифицировать отображение ревизий, ответов, возвратов и статусов.
- `SettingsPanel.tsx` — разделить AI settings и questionnaire settings.

## 6. Предлагаемый паттерн/структура

### 6.1. Основной паттерн

**Modular Monolith + Clean/Hexagonal boundaries + Feature-Sliced frontend.**

Почему это подходит проекту:

- MVP не требует микросервисов и отдельной инфраструктуры;
- проще сохранить portable/demo-local запуск;
- domain/application слой защищает бизнес-правила от FastAPI/React деталей;
- repositories позволяют подготовить PostgreSQL без переписывания сценариев;
- frontend feature-slicing уменьшает размер `App.tsx`, `api.ts`, `types.ts` и снижает риск регрессий.

### 6.2. Границы зависимостей

Backend-зависимости должны идти только внутрь:

```text
api -> application -> domain
application -> repositories interfaces/protocols -> infrastructure repositories
infrastructure -> ORM/file/AI adapters
```

Запрещённые зависимости:

- `domain` импортирует FastAPI, SQLAlchemy session или Pydantic API schemas;
- `repositories` выбрасывают `HTTPException`;
- `api/routers` содержат SQLAlchemy queries;
- AI adapter сам выбирает персональные поля для промпта;
- frontend page вызывает `fetch` напрямую.

Frontend-зависимости:

```text
pages -> features -> shared
features не импортируют друг друга напрямую, кроме явно вынесенных shared/model типов
shared не импортирует features/pages
```

## 7. Поэтапный план рефакторинга без поломки MVP

### Этап 0. Зафиксировать safety net

- Запустить текущие backend tests и frontend build.
- Добавить недостающие smoke/contract tests для ключевых сценариев.
- Зафиксировать список публичных endpoint-ов и основных UI-сценариев.
- Не менять поведение, статусы, seed-данные и миграции.

### Этап 1. Разрезать backend routes без изменения операций

- Создать `api/deps.py` и `api/routers/*`.
- Перенести endpoint-ы из `main.py` группами: `health/auth`, `organization`, `profiles`, `manager`, `hr`, `documents/exports`.
- Все router-ы пока продолжают вызывать существующие `*_operations.py`.
- После каждой группы запускать backend tests.

Критерий готовности: `main.py` стал composition root, API-контракты не изменились.

### Этап 2. Разделить frontend API client и страницы

- Создать `shared/api/client.ts`, оставить совместимый wrapper.
- Перенести auth/profile/campaign/document endpoint-ы по одному.
- Разделить `App.tsx` на layout/pages без изменения CSS и UX.
- Проверять frontend build после каждого крупного переноса.

Критерий готовности: страницы не содержат прямого `fetch`, `App.tsx` управляет только shell/nav/top-level state.

### Этап 3. Выделить application use-cases на backend

- Для каждого старого `*_operations.py` сначала создать фасад с прежними функциями.
- Внутри фасада постепенно вызывать новые `application/*/use_cases.py`.
- Начать с менее рискованных чтений, затем перейти к мутациям статусов и версий.
- Audit оставить обязательным параметром/сервисом use-case.

Критерий готовности: use-case можно протестировать через session fixture без FastAPI client.

### Этап 4. Вынести repositories

- Начать с read repositories: очереди review, analytics, documents registry.
- Затем вынести write repositories: profile revisions, campaign participants, document links.
- Не менять ORM-модели и миграции в том же PR, где меняется orchestration.

Критерий готовности: SQLAlchemy-запросы исчезают из use-case кроме временно согласованных исключений.

### Этап 5. Выделить domain rules

- Статусы профиля и кампаний оформить как enum/value objects или чистые функции.
- Правила `is_demo`, свободных ставок, версионности, single-choice и AI policy покрыть unit-тестами.
- Заменять scattered string literals постепенно, не одним большим diff.

Критерий готовности: ключевые бизнес-инварианты тестируются без БД и HTTP.

### Этап 6. Укрепить frontend features

- Разделить большие панели на feature-компоненты.
- Перенести derived-state helpers в `model/*` и покрыть unit-тестами.
- Ввести единые UI primitives только после 2-3 повторов, без premature abstraction.

Критерий готовности: компоненты страниц читаются как композиция фич, а не как набор низкоуровневых обработчиков.

### Этап 7. Подготовка к PostgreSQL и расширениям

- Проверить SQLAlchemy-запросы на совместимость с PostgreSQL.
- Убрать SQLite-специфичные предположения из application слоя.
- Подготовить contract/integration tests на альтернативный `DATABASE_URL`, когда будет принято решение по F-041.

## 8. Правила кодстайла и именования

### 8.1. Общие правила

- Один модуль — одна зона ответственности.
- Не смешивать перенос кода и изменение поведения в одном PR без явной причины.
- Любое изменение бизнес-правила отражать в `docs/FEATURE_REGISTRY.md`.
- Демо-данные всегда явно помечать `is_demo = true` и не смешивать с рабочим контуром по совпадению названий.
- Не добавлять реальные интеграции, почтовые отправки и внешние модели без отдельного решения.

### 8.2. Backend

- Имена router-файлов: по предметной области во множественном числе или устойчивом bounded context: `profiles.py`, `campaigns.py`, `documents.py`.
- Имена use-case функций: глагол + объект + контекст, например `submit_profile_revision`, `return_profile_to_manager`, `link_work_document`.
- Имена repository методов: `get_*`, `list_*`, `find_*`, `save_*`, `update_*`, `delete_*`.
- Domain errors: `ProfileStatusError`, `AccessDeniedError`, `DocumentQualityError`; HTTP-коды назначаются только в API layer.
- Константы статусов держать в domain modules, не размножать string literals.
- Не использовать `HTTPException` вне `api/*`.
- Не делать `try/except` вокруг импортов.
- Все write use-cases должны явно создавать audit event или документировать, почему audit не нужен.

### 8.3. Frontend

- Компоненты: `PascalCase.tsx`.
- Hooks: `useSomething.ts` или `hooks.ts` внутри маленькой фичи.
- Feature API: `features/<feature>/api.ts`, функции в формате `getProfiles`, `saveDraft`, `submitProfile`.
- Типы: `PascalCase` для DTO и UI models; `type` использовать по умолчанию, `interface` — для расширяемых object contracts.
- Файлы helpers: `camelCase.ts` или предметные `answers.ts`, `tree.ts`, `format.ts`.
- Page-компоненты не вызывают `fetch` напрямую.
- Business-critical проверки можно дублировать для UX, но backend response должен оставаться источником истины.
- Не создавать общий компонент, пока нет повторного использования минимум в двух местах или явного дизайн-решения.

## 9. Тесты для безопасного рефакторинга

### 9.1. Backend unit tests

Покрыть чистые domain rules:

- расчёт свободной ставки при вакантных ставках и нескольких сотрудниках на одной штатной строке;
- допустимые переходы профиля: draft -> submitted -> manager_verified -> hr_accepted / returned;
- запрет перезаписи ответов после сдачи, создание новой версии;
- single-choice validation для анкеты;
- demo/work isolation и исключение demo-данных из рабочих KPI;
- AI policy: запрещённые персональные поля не попадают в промпт.

### 9.2. Backend integration/API tests

Сохранить и расширить тесты FastAPI:

- auth: demo-local selector, magic link, bearer session, logout;
- HR: создание кампании, волны, включение/исключение ветки и отдельных назначений;
- employee: черновик, submit, export profile;
- manager: очередь, take, return, verify;
- HR review: accept/return/bulk return;
- documents: registry, upload, link, quality, source;
- analytics: KPI считают только из БД и по умолчанию не включают demo в рабочие показатели;
- `AI_MODE=off`: все сценарии работают без модели.

### 9.3. Contract tests

- Зафиксировать OpenAPI snapshot или набор JSON shape assertions для ключевых endpoint-ов.
- Проверять, что frontend types соответствуют backend response shape хотя бы через smoke fixtures.
- Для file endpoints проверять headers/content-type и минимальную валидность XLSX/CSV.

### 9.4. Frontend tests

Минимальный набор перед крупным UI-рефакторингом:

- unit tests для helper-ов: group questions by section, progress calculation, answer formatting, tree filtering/selection;
- component tests для анкеты: draft, submit guard, AI-check state, required/single-choice fields;
- component tests для HR campaign controls: include/exclude, wave edit confirmation;
- component tests для document panel: фильтр дерева, link controls, OCR quality form;
- smoke test render основных pages с mocked API.

### 9.5. End-to-end smoke

Для MVP достаточно короткого happy path:

1. HR входит в demo-local.
2. Создаёт/редактирует кампанию и включает ветку.
3. Сотрудник заполняет профиль и сдаёт.
4. Руководитель подтверждает или возвращает.
5. HR принимает.
6. Проверяется audit и отсутствие обращения к внешней LLM при `AI_MODE=off`.

## 10. Рекомендуемые первые PR

1. **PR-1: backend route split.**  
   Только `main.py -> api/routers`, без изменения операций и схем.

2. **PR-2: frontend API client split.**  
   `shared/api/client.ts` + перенос auth/profile endpoint-ов, совместимость текущих вызовов.

3. **PR-3: frontend App split.**  
   Вынести `LoginPage`, top-level layout, employee/manager/HR pages.

4. **PR-4: profile domain/use-case extraction.**  
   Чистые функции для анкеты, версий, single-choice и AI usage + unit tests.

5. **PR-5: campaign/HR use-case extraction.**  
   Разделить кампании, сотрудников, staffing и audit.

6. **PR-6: documents/export boundaries.**  
   File storage, document repository, export service.

Такой порядок сначала уменьшает размер файлов и риск конфликтов, затем постепенно усиливает архитектурные границы вокруг наиболее критичных бизнес-правил.
