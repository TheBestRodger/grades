# ADR 0003: Tests And Observability Baseline

## Контекст

Backend переходит к feature-based modular monolith. Такой рефакторинг должен сохранять поведение, а не менять продуктовые сценарии без отдельной задачи.

Без тестов перенос файлов держится только на ручной проверке. Без observability работающий сервис трудно диагностировать: непонятно, какой запрос сломался, где медленно, какие бизнес-действия произошли.

Нужен практичный baseline, а не большой observability/platform rewrite.

## Решение

Используем такие уровни тестов:

```text
unit tests:
  domain rules
  serializers
  pure helper functions

service tests:
  auth login and sessions
  profile draft and submit
  review routing
  campaign wave lifecycle
  document import idempotency

api smoke tests:
  login
  profile submit
  campaign launch
  document upload/download

integration tests:
  Postgres runtime
  file storage
  XLSX export generation
```

Используем такой observability baseline:

```text
request_id
structured request logs
health endpoint
readiness endpoint with DB check
slow request logging
consistent API error format
business audit events
```

На первом этапе не добавляем Prometheus, OpenTelemetry, distributed tracing, message broker или сложный metrics stack без отдельной необходимости.

## Последствия

Плюсы:

- feature-рефакторинг можно проверять повторяемо;
- ключевые бизнес-сценарии защищены от regressions;
- runtime-ошибки можно связывать по request ID;
- медленные endpoints и DB-проблемы становятся видимыми;
- audit events отделяют бизнес-действия от технических logs.

Цена решения:

- test data setup нужно держать поддерживаемым;
- service tests не должны превращаться в тяжелые end-to-end tests;
- integration tests могут требовать Docker services;
- logs не должны раскрывать пароли, bearer tokens, magic-link tokens и содержимое чувствительных документов.

## Определения

Technical logs отвечают:

```text
Что технически произошло?
```

Пример:

```text
request_id=abc method=POST path=/api/profiles/5/submit status=200 duration_ms=143
```

Audit events отвечают:

```text
Какое бизнес-действие произошло и кто его сделал?
```

Пример:

```text
profile.submitted actor_employee_id=10 profile_id=5
```

Нужны оба слоя. Они решают разные задачи.
