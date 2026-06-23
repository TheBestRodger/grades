# Frontend

## Установка зависимостей

```bash
npm install
```

## Запуск проекта

```bash
npm run dev
```

Запускает frontend в dev-режиме через Vite.

## Production build

```bash
npm run build
```

Проверяет TypeScript и собирает production-версию приложения.

## Preview production build

```bash
npm run preview
```

Локально запускает собранную production-версию.

## Тесты

```bash
npm run test
```

Запускает unit-тесты один раз.

```bash
npm run test:watch
```

Запускает тесты в watch-режиме. Удобно использовать во время разработки: watch-режим оставляет тесты запущенными и автоматически перезапускает их при изменении файлов, чтобы сразу видеть, сломалась ли логика после правок

```bash
npm run test:coverage
```

Запускает тесты и формирует отчёт покрытия в папке `coverage/`.
