# ADR 0002: Backend Dependency Rules

## Контекст

Feature-based modular monolith работает только при реальных границах между слоями и модулями. Простого переноса файлов в папки недостаточно.

Если не зафиксировать правила импортов, возможны типичные проблемы:

- service начинает импортировать router;
- repository начинает вызывать service;
- rules начинают ходить в DB/session;
- feature начинает использовать private helper другой feature;
- infrastructure начинает знать бизнес-сценарии.

Такой код формально лежит в красивых папках, но архитектурно остается связанным хаотично.

## Решение

Используем однонаправленные dependency rules.

Разрешенный поток:

```text
router -> service/use_case
service/use_case -> repository
service/use_case -> rules
service/use_case -> serializers
service/use_case -> infrastructure adapter
repository -> models
rules -> pure Python/constants
serializers -> models/schemas
infrastructure -> external libraries
```

Запрещенный поток:

```text
service -> FastAPI / HTTPException
repository -> service
rules -> database session / SQLAlchemy queries
infrastructure -> feature service
feature A -> private functions of feature B
router -> repository напрямую для business workflow
```

Feature-модуль может давать другим модулям публичный вход через:

```text
service.py
read_model.py
queries.py
package-level exports
```

Другие модули не должны импортировать функции с префиксом `_` из чужой feature.

## Последствия

Плюсы:

- routers остаются тонкими;
- бизнес-логика тестируется без HTTP;
- SQLAlchemy-запросы проще оптимизировать;
- rules проще покрывать unit tests;
- внешние детали изолируются;
- границы feature-модулей становятся понятными.

Цена решения:

- часть существующего кода придется переносить постепенно;
- code review должен отклонять новые нарушения;
- repository не должен превращаться в service под другим названием;
- `shared` должен оставаться действительно общим.

## Примеры

Правильно:

```python
profile = repository.load_profile(session, profile_id)
rules.ensure_can_submit(profile, actor)
return serializers.profile_detail(profile)
```

Неправильно:

```python
# rules.py
def can_submit(session, profile_id):
    profile = session.get(EmployeeProfile, profile_id)
    return profile.workflow_status == "draft"
```

Rules не должны загружать данные. Service загружает данные через repository и передает в rules обычные объекты или значения.

Правильный cross-feature доступ:

```python
from app.features.structure.read_model import get_assignments_for_units
```

Неправильный cross-feature доступ:

```python
from app.features.structure.service import _resolve_manager_assignment
```

Private helpers являются деталями реализации своего модуля.
