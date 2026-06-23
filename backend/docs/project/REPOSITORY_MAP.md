# Repository Map

## Назначение

Этот документ - короткий навигатор по репозиторию. Он не дублирует backend/frontend карты, а только фиксирует верхнеуровневые границы.

Подробные карты:

- Backend: `backend/docs/project/BACKEND_REFACTOR_MAP.md`
- Frontend: `backend/docs/project/FRONTEND_REFACTOR_MAP.md`
- Архитектурные документы: `backend/docs/project_docs/`

## Главный принцип

В проекте две основные рабочие зоны:

- `backend/` - API, бизнес-логика, БД, миграции, backend docs, backend scripts/tools, исходные данные для импортов.
- `frontend/` - React-приложение, frontend docs, frontend build config.

В корне остаются только файлы, которые нужны всему проекту целиком.

## Root

В корне оставить:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`
- `.gitignore`
- `README.md`

Документы, исходные материалы и scripts/tools не лежат в root. Они разложены внутри `backend/`.

## Backend

Целевая зона:

```text
backend/
  app/
  migrations/
  tests/
  docs/
  scripts/
  tools/
  source_documents/
  data/
  alembic.ini
  requirements.txt
  requirements-dev.txt
```

Что должно жить внутри `backend/`:

- backend runtime code;
- миграции;
- backend tests;
- backend docs;
- backend maintenance scripts/tools;
- исходные Excel/DOCX/import data;
- runtime data volume mount (`backend/data/`).

## Frontend

Целевая зона:

```text
frontend/
  src/
  docs/
  package.json
  package-lock.json
  vite.config.ts
  tsconfig*.json
```

Что должно жить внутри `frontend/`:

- React code;
- frontend docs;
- frontend package/build config;
- frontend-only tooling.

## Source Documents

Исходные документы и справочные файлы не должны лежать в root.

Целевые папки:

```text
backend/source_documents/Изначальные документы_история/
backend/source_documents/Intrukcii_i_pologeniya/
backend/source_documents/Грейды/
backend/source_documents/ШР по уровням на 15.05.26.xlsx
```

Dockerfile копирует `backend/`, поэтому эти материалы попадают в контейнер вместе с backend context.

## Legacy / Archive

Legacy Windows scripts и исторические аналитические заметки не должны мешать рабочему root.

Варианты:

- удалить, если не нужны;
- перенести в `backend/docs/archive/`, если нужна история;
- перенести в `backend/tools/`, если это реально ещё запускается;
- перенести в `backend/scripts/`, если это рабочий скрипт запуска/обслуживания.

## Что не описывать здесь

Не хранить в этом файле:

- список backend routers/services/repositories;
- перенос `main.py`;
- перенос `App.tsx`, `api.ts`, `types.ts`;
- детальные задачи на MR.

Для этого есть отдельные BE/FE карты и task plan.
