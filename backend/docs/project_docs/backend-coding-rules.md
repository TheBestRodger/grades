# Backend Coding Rules

## Назначение

Этот документ фиксирует рабочие правила backend-разработки при переходе Grades MGTU к feature-based modular monolith.

Цель: код должен быть проще найти, проще ревьюить и безопаснее рефакторить.

## Краткий стандарт

Backend-стандарт:

```text
Feature Modular Monolith
+ Feature-Based Structure
+ Service Layer
+ Repository / Queries
+ Ports & Adapters
+ Use Case Split
+ Dependency Rules
+ ADR
+ Tests
+ Observability
```

Коротко:

```text
features дают ownership
routers expose HTTP
services выполняют business scenarios
repositories загружают data
rules защищают invariants
serializers собирают responses
adapters общаются с external systems
tests защищают behavior
observability объясняет runtime
ADR объясняет decisions
```

## Структура feature-модуля

Для зрелых backend features предпочитаем:

```text
backend/app/features/<feature>/
  __init__.py
  router.py
  schemas.py
  service.py
  repository.py
  rules.py
  serializers.py
  errors.py
```

Если `service.py` становится большим, режем по use cases:

```text
backend/app/features/profiles/
  draft.py
  submit.py
  routing.py
  ai_answers.py
```

Используем бизнесовые названия:

```text
good: submit.py, waves.py, participants.py
bad: helpers.py, utils.py, misc.py
```

## Правила routers

Routers должны:

- описывать paths, methods, request bodies и dependencies;
- вызывать service или use-case functions;
- переводить feature errors в HTTP responses через общие error helpers;
- не содержать бизнес-сценарии.

Routers не должны:

- содержать business workflows;
- содержать сложные SQLAlchemy queries;
- напрямую создавать audit events для бизнес-операций;
- напрямую вызывать repositories для business workflows.

Правильно:

```python
@router.post("/profiles/{profile_id}/submit")
def submit_profile_endpoint(...):
    return run_profile_operation(
        lambda: submit_profile(session, actor, profile_id, request)
    )
```

Плохо:

```python
@router.post("/profiles/{profile_id}/submit")
def submit_profile_endpoint(...):
    profile = session.scalar(select(EmployeeProfile).where(...))
    if profile.workflow_status != "draft":
        raise HTTPException(...)
    ...
```

## Правила services и use cases

Services должны:

- реализовывать один бизнес-сценарий на публичную функцию;
- координировать repositories, rules, serializers, audit и infrastructure adapters;
- держать transaction boundary понятным;
- кидать feature-specific operation errors.

Services не должны:

- импортировать FastAPI;
- кидать `HTTPException`;
- содержать крупные SQLAlchemy query blocks, если repository будет понятнее;
- вызывать private-функции другой feature.

Правило:

```text
один service call = одна бизнес-операция
```

Примеры:

```text
login_with_password
request_magic_link
save_draft
submit_profile
launch_wave
upload_document
export_credentials_xlsx
```

## Правила repositories

Repositories должны:

- владеть сложными SQLAlchemy queries;
- загружать и сохранять данные, нужные services;
- иметь имена, описывающие загружаемые данные;
- не содержать бизнес-решения.

Repositories не должны:

- импортировать services;
- кидать HTTP errors;
- решать, разрешена ли операция;
- отправлять email, вызывать AI или писать файлы.

Правильно:

```python
def load_campaign_with_waves(session: Session, campaign_id: int) -> Campaign | None:
    return session.scalar(...)
```

Плохо:

```python
def load_wave_if_launch_allowed(session: Session, wave_id: int) -> CampaignWave:
    wave = session.get(CampaignWave, wave_id)
    if wave.status == "active":
        raise CampaignOperationError(...)
    return wave
```

Repository загружает данные. Rules или services проверяют бизнес-смысл.

## Правила rules

Rules должны:

- быть pure или почти pure;
- содержать business invariants и status checks;
- легко покрываться unit tests.

Rules не должны:

- импортировать DB sessions;
- выполнять SQLAlchemy queries;
- вызывать infrastructure adapters;
- зависеть от FastAPI.

Пример:

```python
def is_wave_editable(status: str) -> bool:
    return status in {"draft", "editing"}
```

## Правила infrastructure

External systems должны жить в infrastructure adapters:

```text
backend/app/infrastructure/ai/
backend/app/infrastructure/email/
backend/app/infrastructure/files/
backend/app/infrastructure/xlsx/
```

Services не должны напрямую владеть деталями:

- SMTP;
- OpenAI или других AI SDK;
- filesystem storage;
- XLSX writer internals;
- external parsers.

Adapter владеет внешними деталями. Service владеет бизнес-решением использовать adapter.

## Cross-feature правила

Не импортировать private-функции из другой feature.

Плохо:

```python
from app.features.campaigns.waves import _resolve_wave
```

Хорошо:

```python
from app.features.campaigns.service import get_campaign_summary
from app.features.structure.read_model import get_assignments_for_units
```

Если feature нужны данные другой feature, создаем публичную query/read model, а не лезем во внутренние helpers.

## Правила shared

`shared` только для действительно общего кода.

Можно:

```text
shared/errors.py
shared/audit.py
shared/time.py
shared/pagination.py
```

Плохо:

```text
shared/profile_helpers.py
shared/campaign_utils.py
shared/hr_logic.py
```

Feature-specific logic должна жить внутри своей feature.

## Правила размера файлов

Ориентир:

```text
0-150 строк: хорошо
150-220 строк: допустимо
220+ строк: нужно объяснить или разделить
400+ строк: почти всегда делить
```

Сначала делим по бизнес-use-case, а не создаем generic helpers.

## Правила ошибок

Services должны кидать feature errors:

```python
raise ProfileOperationError("Анкета не найдена.", 404)
```

Routers или API helpers переводят feature errors в HTTP responses.

Не кидать `HTTPException` из services, repositories, rules или infrastructure adapters.

## Правила транзакций

Service/use-case функция должна представлять одну бизнес-транзакцию.

Пример:

```text
submit_profile:
  load profile
  validate status
  save answers
  create revision
  route to manager or HR
  write audit event
```

Если обязательный шаг падает, вся операция должна откатиться через session context.

`session.flush()` используем там, где внутри операции нужны ID. Commit/rollback остается на границе session.

## Правила тестов

Новое или перенесенное поведение покрываем на минимально полезном уровне:

```text
unit tests: rules, serializers, pure helpers
service tests: business scenarios
api smoke tests: endpoint wiring
integration tests: DB/files/XLSX/runtime services
```

Не полагаться только на ручное UI-тестирование backend-рефакторинга.

## Правила observability

Runtime-поведение должно быть объяснимо через:

- request IDs;
- structured request logs;
- health/readiness checks;
- slow request logs;
- business audit events;
- consistent error responses.

Technical logs и audit events - разные вещи:

```text
logs: что технически произошло
audit: какое бизнес-действие произошло и кто его сделал
```

Не логировать passwords, magic-link tokens, bearer tokens или содержимое чувствительных документов.

## Review checklist

Перед merge backend-кода проверить:

- [ ] Router тонкий.
- [ ] Service не импортирует FastAPI.
- [ ] Repository не импортирует service.
- [ ] Rules не обращаются к DB/session.
- [ ] Feature не импортирует private-функции другой feature.
- [ ] External systems спрятаны за infrastructure adapters.
- [ ] Большие файлы разделены или обоснованы.
- [ ] Важное поведение покрыто тестами или есть явная причина отложить тесты.
- [ ] `git diff --check` проходит.
- [ ] Python compile или test command был запущен.
