# ИИ-профилирование должностей

MVP системы профилирования должностей для серверного стенда.

Текущий этап:

- backend на FastAPI и PostgreSQL;
- frontend на React/Vite, в Docker собирается отдельно и отдаётся Node static server;
- рабочий контур с кабинетами HR, руководителя и сотрудника;
- персональные уведомления о назначениях, проверках, документах и изменениях структуры;
- вход по одноразовой email-ссылке;
- интеграция с OpenAI-compatible LLM;
- запуск через Docker для macOS, Linux и Ubuntu VM.

Актуальные архитектурные решения находятся в `backend/docs/project_docs/`, правила разработки - в `backend/docs/project/AGENTS.md`.

## Быстрый запуск через Docker

Рекомендуемый способ для macOS, Linux и Ubuntu VM:

```bash
cp .env.example .env
docker compose up -d --build
```

После запуска интерфейс доступен по адресу:

```text
http://192.168.18.163:3000
```

По умолчанию Docker-стенд работает в pilot-режиме:

```env
APP_ENV=pilot
PUBLIC_BASE_URL=http://192.168.18.163:3000
DATABASE_URL=postgresql+psycopg://grades_mgtu:change-me-in-.env@postgres:5432/grades_mgtu
```

SMTP нужен только для сценария входа по одноразовой email-ссылке. Основной пилотный
вход сейчас работает по логину и паролю.

```env
SMTP_HOST=smtp.example.ru
SMTP_PORT=587
SMTP_USERNAME=login@example.ru
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=login@example.ru
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

Для входа без SMTP используется логин/пароль. Первый HR-пользователь берётся из
seed-данных, а его логин и пароль задаются через `.env`:

```env
BOOTSTRAP_HR_USERNAME=hr
BOOTSTRAP_HR_PASSWORD=...
```

После входа HR добавляет руководителей и сотрудников в рабочую структуру. Для
каждого добавленного пользователя система генерирует логин и временный пароль;
HR скачивает XLSX с доступами и передаёт их пользователям.

Уведомления доступны после входа через индикатор в верхней панели. Список
обновляется автоматически, уведомления можно отметить прочитанными по одному
или все сразу; переход открывает связанный раздел приложения.

Для внешней OpenAI-compatible LLM:

```env
AI_MODE=token
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=...
AI_REQUEST_TIMEOUT_SECONDS=60
```

Перед запуском замените `POSTGRES_PASSWORD` и пароль внутри `DATABASE_URL` в `.env`
на стендовый пароль. Если пароль содержит спецсимволы, URL-часть пароля нужно
percent-encode.

Compose содержит runtime-сервисы `postgres`, `app`, `frontend` и одноразовый job
`migrate`. Frontend доступен снаружи на `3000:3000`: production build из
`frontend/dist` отдаётся Node static server, который также отправляет `/api/*`
на backend внутри Docker сети. Backend остаётся доступен напрямую на
`8010:8000` для API/debug.

`postgres` подключает Docker volume `grades_mgtu_postgres_data` к
`/var/lib/postgresql/data`. Файлы приложения и документы остаются в volume
`grades_mgtu_data`, который монтируется в `/app/backend/data`. Backend зависит от
healthy-состояния Postgres. После этого одноразовый `migrate` выполняет
`alembic upgrade head`, bootstrap начальных данных и настроенный импорт
документов. `app` запускается только после успешного завершения этого job.
Backend проходит Docker healthcheck через `/api/health/ready` и не обязан
отдавать frontend static.

Количество Uvicorn workers и время graceful shutdown задаются в `.env`:

```env
UVICORN_WORKERS=1
UVICORN_GRACEFUL_SHUTDOWN_SECONDS=30
```

Не увеличивайте число workers без нагрузочных замеров и проверки доступных
CPU/RAM. При остановке Compose отправляет backend и frontend `SIGTERM` и даёт им
время корректно завершить активные запросы.

Health endpoints:

```text
/api/health/live  -> backend-процесс работает, PostgreSQL не проверяется
/api/health/ready -> backend готов принимать запросы, PostgreSQL доступен
/api/readiness    -> временный alias readiness для обратной совместимости
```

SQLite больше не поддерживается как runtime database. Старую SQLite-базу можно
использовать только как источник одноразовой миграции в Postgres.

Папка `.codex-local` используется только как локальная рабочая память Codex:
контекст, команды и заметки. Runtime-данные, Postgres volume, `.env` и секреты в
`.codex-local` хранить не нужно.

Проверка после запуска:

```bash
docker compose ps -a
curl -s http://192.168.18.163:3000/
curl -s http://192.168.18.163:3000/api/health/live
curl -s http://192.168.18.163:3000/api/health/ready
curl -s http://192.168.18.163:8010/api/health/live
curl -s http://192.168.18.163:8010/api/health/ready
```

Ожидаемо: `postgres`, `app` и `frontend` находятся в статусе `Up` / `healthy`;
`migrate` завершён с кодом `0`; frontend отдаёт HTML; liveness возвращает
`{"status":"alive"}`, readiness возвращает `"status":"ready"` и
`"database":"ok"`.

Повторный ручной запуск миграций:

```bash
docker compose run --rm migrate
```

Команда повторно применяет Alembic до текущего `head` и запускает идемпотентную
подготовку runtime-данных.

Полезные команды:

```bash
docker compose logs -f postgres
docker compose logs -f app
docker compose logs -f frontend
docker compose restart app
docker compose down
./backend/scripts/backup_data.sh
```

## Backend-тесты

Все команды выполняются из корня проекта. Backend требует Python 3.12:

```bash
cd /Users/user/Desktop/grades_mgtu
source .venv/bin/activate
python -V
python -m pip install -r backend/requirements-dev.txt
```

Ожидаемо `python -V` выводит `Python 3.12.x`.

Быстрые unit/service/architecture тесты не требуют запущенного Docker:

```bash
python -m pytest backend/tests/unit backend/tests/service backend/tests/architecture
```

API/integration тесты используют реальный PostgreSQL. Сначала поднимите только
test database service:

```bash
docker compose up -d postgres
docker compose ps

python -m pytest backend/tests/api backend/tests/integration
```

API/integration tests используют реальный Postgres test DB layer. По умолчанию
они ждут maintenance DB по адресу:

```text
postgresql+psycopg://grades_mgtu:grades_mgtu@127.0.0.1:6432/postgres
```

Для другого стенда задайте `BACKEND_TEST_DATABASE_URL`. Тесты создают временную
базу на каждый test case, прогоняют Alembic migrations через startup приложения
и удаляют базу после завершения. Production `.env` для тестов не нужен.

```bash
BACKEND_TEST_DATABASE_URL=postgresql+psycopg://user:password@host:port/postgres \
  python -m pytest backend/tests/api backend/tests/integration
```

Пользователь test database должен иметь право `CREATE DATABASE`.

Запуск всех backend-тестов:

```bash
docker compose up -d postgres
python -m pytest backend/tests
```

Coverage для быстрых business/architecture тестов:

```bash
python -m pytest backend/tests/unit backend/tests/service backend/tests/architecture \
  --cov=backend/app/features --cov=backend/app/core --cov=backend/app/shared \
  --cov-report=term-missing
```

Минимальная проверка перед merge:

```bash
docker compose up -d postgres

python -m pytest backend/tests/unit backend/tests/service backend/tests/architecture
python -m pytest backend/tests/api backend/tests/integration

PYTHONPYCACHEPREFIX=/private/tmp/grades_mgtu_pycache \
  python -m compileall -q backend/app

git diff --check
```

Ожидаемо: все тесты имеют статус `passed`, а `compileall` и `git diff --check`
ничего не выводят. Подробное назначение каждого теста описано в локальном
`not_staged/BACKEND_TESTING.md`.

Backup по умолчанию сохраняется вне папки проекта:

```text
../grades_mgtu_backups/<timestamp>/
```

Скрипт backup нужно запускать из корня репозитория при поднятом контейнере.
`backend/scripts/backup_data.sh` сохраняет дамп Postgres и, если доступен
контейнер `app`, каталог документов:

```bash
./backend/scripts/backup_data.sh
```

Можно указать другой каталог:

```bash
./backend/scripts/backup_data.sh /var/backups/grades_mgtu
```

Если нужно полностью сбросить Docker-данные стенда, включая Postgres volume и
документы:

```bash
docker compose down -v
```

На серверном стенде эту команду нельзя выполнять без backup.

## Миграция SQLite -> Postgres

Старая SQLite-база не должна подключаться к приложению напрямую. Для переноса
данных используйте скрипт:

```bash
docker compose up -d postgres
docker compose run --rm --no-deps app sh -c 'python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /app/backend/data/demo.sqlite \
  --database-url "$DATABASE_URL"'
```

Без `--apply` скрипт делает dry-run: копирует SQLite-файл во временную директорию,
прогоняет миграции на копии, проверяет доступность Postgres и показывает план.

Фактический перенос:

```bash
docker compose run --rm --no-deps app sh -c 'python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /app/backend/data/demo.sqlite \
  --database-url "$DATABASE_URL" \
  --apply'
```

Скрипт по умолчанию откажется писать в непустой Postgres. Если вы уже сделали
backup и осознанно хотите перезаписать целевую БД:

```bash
docker compose run --rm --no-deps app sh -c 'python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /app/backend/data/demo.sqlite \
  --database-url "$DATABASE_URL" \
  --apply \
  --replace-target'
```

Гарантии скрипта:

- исходный SQLite-файл не изменяется, миграции выполняются на временной копии;
- Postgres schema доводится Alembic до текущего head;
- импорт выполняется в одной transaction;
- при ошибке или несовпадении проверок transaction откатывается;
- перед commit проверяются counts и row-level equality по всем application tables;
- sequence values в Postgres выставляются после импорта.

## Добавление рабочих сотрудников

Во вкладке `Рабочий` -> `Структура` HR добавляет руководителей и сотрудников
вручную через кнопку `Добавить людей` у нужной штатной строки.

Порядок работы:

- сначала добавить руководителя на его штатную строку;
- затем добавить сотрудников на их штатные строки;
- для сотрудника выбрать непосредственного руководителя;
- для каждого пользователя указать ФИО и email, по которому он будет входить в систему.

## Локальный запуск в разработке

Backend:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.migrate
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

Frontend после установки зависимостей:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Vite проксирует запросы `/api` в backend на `http://127.0.0.1:8010`.

Если нужен старый single-process fallback, где FastAPI отдаёт уже собранный
`frontend/dist`, включите `SERVE_FRONTEND_STATIC=true`. В Docker production-like
сценарии frontend отдаёт отдельный service.

Для локальной проверки собранного frontend fallback:

```powershell
cd frontend
npm.cmd run build
cd ..
set SERVE_FRONTEND_STATIC=true
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8010
```

После этого интерфейс доступен по адресу `http://127.0.0.1:8010`.
