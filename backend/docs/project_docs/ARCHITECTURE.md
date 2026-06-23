# Архитектура демонстрационного MVP

**Статус:** решение для первого переносимого показа  
**Дата фиксации:** 26.05.2026  
**Основание:** `ТЗ_ИИ_профилирование_должностей_бизнес_v2.md`

## 1. Цель первого контура

Первый MVP предназначен для демонстрации полного рабочего сценария профилирования на отдельной тестовой ветке:

1. HR видит структуру и добавляет сотрудников.
2. HR запускает кампанию по ветке.
3. Сотрудник заполняет профиль, сохраняет черновик и сдаёт версию.
4. Руководитель проверяет, подтверждает или возвращает профиль.
5. HR принимает результат либо возвращает его руководителю для дальнейшей доработки.
6. Система показывает документы, покрытие, статусы, прогресс и историю.

Приложение должно запускаться без подключения к LLM. Runtime database - PostgreSQL.
Старый SQLite-файл допускается только как источник одноразовой миграции данных.

## 2. Выбранный стек

| Слой | Текущее решение | Путь к pilot/production |
|---|---|---|
| Архитектура | Модульный монолит | Сохраняется до появления реальной необходимости разделения |
| Frontend | Vite + React + TypeScript + Tailwind CSS | То же |
| Навигация/данные UI | React Router + TanStack Query | То же |
| Графики | Apache ECharts | То же |
| Backend | FastAPI + Pydantic + SQLAlchemy 2 + Alembic | То же |
| База данных | PostgreSQL через SQLAlchemy и Alembic migrations | То же |
| Файлы | Локальная папка данных приложения | S3/MinIO или защищённое файловое хранилище |
| Авторизация | Локальный быстрый демо-вход в `demo-local/test` + magic-link/bearer-session вход | Подключение почтового транспорта, затем возможно SSO/LDAP |
| ИИ | `AI_MODE=off`, контракт AI Gateway, HR-настройки режима, Ollama-интервьюер по одному открытому вопросу | LM Studio/OpenAI-compatible и общий AI-router после расширения политики обезличивания |
| Экспорт | Excel/CSV/JSON на backend | То же |

## 3. Docker/pilot runtime с PostgreSQL и отдельным frontend

Основной Docker-сценарий содержит три runtime-сервиса и одноразовый migration job:

```text
postgres -> PostgreSQL 16, persistent volume grades_mgtu_postgres_data
migrate  -> Alembic, bootstrap и import, завершается до запуска app
app      -> FastAPI backend API, liveness/readiness, configurable Uvicorn workers
frontend -> Node static server, frontend/dist, SPA fallback, /api proxy to app:8000
```

Порты в pilot-схеме:

```text
frontend: 3000:3000
app:      8010:8000
postgres: 6432:5432
```

Пользовательский вход в приложение идёт через `frontend` на `http://127.0.0.1:3000`.
Backend API остаётся доступен напрямую на `http://127.0.0.1:8010/api/...` для
debug и внутренних проверок. В production-like UI frontend static service
проксирует `/api/*` на `http://app:8000/api/*` внутри Docker network. Внешние
TLS, reverse proxy, домены и ingress остаются ответственностью
deployment-инфраструктуры.

Порядок запуска:

```text
postgres healthy
  -> migrate: alembic upgrade head + seed/bootstrap/import
  -> app startup без изменения схемы и данных
  -> app ready
  -> frontend startup
```

Health endpoints:

```text
/api/health/live  -> проверка backend-процесса без PostgreSQL
/api/health/ready -> проверка готовности и соединения с PostgreSQL
/api/readiness    -> compatibility alias для readiness
```

`UVICORN_WORKERS` и `UVICORN_GRACEFUL_SHUTDOWN_SECONDS` задаются через
окружение. По умолчанию используется один worker и 30 секунд на корректное
завершение.

`DATABASE_URL` задаётся через `.env` и в pilot-режиме должен указывать на
PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://grades_mgtu:change-me-in-.env@postgres:5432/grades_mgtu
```

Документы и другие файловые runtime-данные остаются в `/app/backend/data`
(`grades_mgtu_data`). PostgreSQL-данные лежат в отдельном Docker volume
`grades_mgtu_postgres_data`, а не в `.codex-local`.

Backend static fallback для `frontend/dist` не является обязательной production
схемой. Его можно включить только явно через `SERVE_FRONTEND_STATIC=true` для
локального single-process сценария.

`.codex-local` не является runtime-хранилищем. Это ignored-папка с локальной
рабочей памятью Codex: контекст, команды, статус и архитектурные заметки. В ней
не должны храниться `.env`, дампы БД или секреты.

SQLite больше не является runtime database. Для переноса старой базы используется
`backend/scripts/migrate_sqlite_to_postgres.py`: скрипт делает временную копию
SQLite-файла, прогоняет миграции на копии, импортирует application tables в
PostgreSQL внутри transaction и сверяет результат перед commit.

## 3.1. Backend test DB стратегия

Backend tests разделены по слоям:

```text
unit/service/architecture -> быстрые проверки rules/services/dependency guards
api/integration           -> FastAPI + Alembic + SQLAlchemy + PostgreSQL
docker smoke              -> production-like compose runtime
```

API/integration tests не используют SQLite как замену runtime. Они подключаются
к maintenance PostgreSQL URL из `BACKEND_TEST_DATABASE_URL` или к локальному
compose Postgres по умолчанию:

```text
postgresql+psycopg://grades_mgtu:grades_mgtu@127.0.0.1:6432/postgres
```

На каждый test case создаётся отдельная база `grades_mgtu_test_<uuid>`, затем
startup приложения прогоняет Alembic `upgrade head`, seed demo/work данных и
после теста база удаляется. Так проверяется связка router/service/database без
зависимости от production `.env` и без порядка запуска тестов.

## 4. Модули backend

| Модуль | Ответственность |
|---|---|
| `auth` | Локальный демо-вход только в `demo-local/test`, одноразовые magic-link токены, bearer-сессии, logout и аудит входов |
| `organization` | Структура, штатные строки, сотрудники, назначения, остатки ставок |
| `campaigns` | Кампании, включение участников, массовые действия по ветке |
| `profiles` | Анкета, черновики, прогресс, версии сдачи, профиль должности |
| `workflow` | Проверка, возвраты, утверждения, блокировки, маршруты |
| `documents` | Реестр документов, версии, привязки, качество OCR, покрытие |
| `analytics` | KPI, прогресс, статусы, покрытие документов, сигналы |
| `exports` | Excel/CSV/JSON |
| `audit` | Неизменяемая история значимых действий |
| `notifications` | Персональные уведомления, непрочитанные события, переходы к связанным разделам и защита от дублей |
| `ai_gateway` | `OffProvider`, локальный `OllamaProvider`, HR-конфигурация режима, структурный AI-интервьюер по открытому вопросу |

## 5. AI Gateway в первом этапе

В MVP интерфейс содержит состояние ИИ, но реальная модель не подключается.

```text
AI_MODE=off
AI_PROVIDER=off
```

Минимальные контракты Gateway:

| Метод | Назначение | Реализация этапа 1 |
|---|---|---|
| `health_status()` | Возвращает режим и доступность помощника | `off` |
| `check_answer()` | Проверка ответа и уточняющий вопрос | Заглушка без анализа |
| `extract_document_facts()` | Выделение фактов документа | Не выполняется |
| `compare_profile_with_documents()` | Сверка профиля с источниками | Статус `не проверено ИИ` |
| `compare_functions()` | Анализ пересечений функций | Не выполняется |

При `AI_MODE=off` пользователь видит:

```text
ИИ-помощник отключён. Проверьте, что ответ конкретен,
соответствует примеру и полностью отвечает на вопрос.
```

Пользователь может продолжить, дополнить или изменить ответ. Все версии фиксируют, что автоматическое сопровождение не выполнялось.

## 6. Разделение demo и real

- Демонстрационные подразделения, позиции, сотрудники, документы и кампании получают `is_demo = true`.
- Демо-объекты не входят в рабочие KPI по умолчанию.
- Демо-документы связываются только с ID демо-объектов, не с текстом названия должности.
- При будущем импорте реальных данных демо-режим остаётся отдельным набором/фильтром.

## 7. Переход к пилоту

Для пилота должны быть заменены или расширены только инфраструктурные части:

1. Runtime database уже переведена на PostgreSQL; старый SQLite используется только как источник миграции.
2. Демо-аутентификация заменяется на magic links.
3. Локальное хранение документов переводится на защищённое хранилище.
4. Подключается реальный импорт сотрудников, назначений и руководителей.
5. После утверждения политики может подключаться AI Gateway.

Доменная модель профилей, кампаний, документов, аудита и маршрутов согласования должна сохраниться.
