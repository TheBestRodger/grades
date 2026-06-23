# ADR 0001: Backend Architecture Standard

## Контекст

Grades MGTU уже не является маленьким CRUD-приложением. В backend есть несколько связанных бизнес-областей:

- авторизация и выдача доступов;
- оргструктура и штатные строки;
- анкеты сотрудников и черновики;
- AI-проверки ответов;
- маршрутизация согласования руководителем и HR;
- кампании и волны;
- документы, импорт, экспорт и аналитика.

В текущем `dev` уже есть полезные слои:

```text
legacy FastAPI router wrapper layer/
backend/app/services/
backend/app/schemas/
backend/app/domain/
backend/app/repositories/
backend/app/infrastructure/
```

Но часть бизнес-логики все еще живет в крупных service-файлах и root-level operation-файлах. Из-за этого одну бизнес-фичу приходится собирать по нескольким папкам, а крупные изменения легко создают конфликты.

Нужен стандарт, который сохранит один backend и один деплой, но даст четкие внутренние границы.

## Решение

Используем feature-based modular monolith как основной backend-стандарт.

Целевая архитектура:

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

Целевая структура:

```text
backend/app/
  core/
    config.py
    db.py

  features/
    auth/
    structure/
    profiles/
    reviews/
    campaigns/
    documents/
    imports/
    exports/
    analytics/
    settings/

  infrastructure/
    ai/
    email/
    files/
    xlsx/

  shared/
    errors.py
    audit.py
    time.py
```

Каждый feature-модуль должен владеть своим HTTP router, schemas, services/use cases, repositories/queries, rules, serializers и feature errors.

## Последствия

Плюсы:

- один backend остается простым для запуска и деплоя;
- бизнес-код группируется по фичам, а не размазывается по техническим слоям;
- изменения по одной фиче проще ревьюить;
- меньше конфликтов при параллельной работе;
- большие service-файлы можно резать по use cases;
- внешние системы можно изолировать через adapters;
- если модуль когда-нибудь потребуется вынести отдельно, у него уже будут границы.

Цена решения:

- нужны явные dependency rules;
- `shared` нельзя превращать в общую мусорку;
- feature-модули должны иметь публичные входы;
- архитектурные правила нужно проверять в ревью и тестах.

## Рассмотренные альтернативы

### Оставить layer-based структуру

Отклонено как долгосрочный стандарт. Для маленького приложения это нормально, но здесь бизнес-фича становится разбросанной по нескольким верхнеуровневым папкам.

### Микросервисы

Отклонено для текущего этапа. У проекта одна база, связанные workflows и небольшая команда. Микросервисы добавят сетевые границы, отдельные деплои, версионирование API и распределенную консистентность раньше, чем это нужно.

### Полная Clean Architecture

Отклонено как стандарт по умолчанию. Проекту нужны ясные границы, а не максимальная абстракция. Интерфейсы на каждый класс, interactors, presenters и dependency container сейчас создадут больше шума, чем пользы.

## Практическое правило

Новые backend-изменения должны сначала отвечать на вопрос:

```text
К какой бизнес-фиче это относится?
```

Если ответ понятен, код должен жить в соответствующем `backend/app/features/<feature>/`.
