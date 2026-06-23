# Frontend refactor map – привязка к текущему `frontend/src`

Цель отчёта – не переписать frontend, а нарезать понятные задачи на перенос кода без хаоса и без поломки текущего MVP.

Границы всего репозитория описаны в `docs/REPOSITORY_MAP.md`, а общий план задач - в `docs/BACKEND_REFACTOR_TASKS.md`. Здесь только подробная frontend-карта.

## 0. Что сейчас лежит в `src`

Текущие крупные файлы:

```txt
src/
  App.tsx
  api.ts
  types.ts
  ProfileWorkspace.tsx
  DocumentPanel.tsx
  HrControls.tsx
  HrAnalyticsPanel.tsx
  HrReviewPanel.tsx
  ManagerOverviewPanel.tsx
  ManagerReviewPanel.tsx
  OrganizationTreePanel.tsx
  SettingsPanel.tsx
  BulkReturnBox.tsx
  main.tsx
  index.css
```

Главная проблема – почти всё лежит на одном уровне. Из-за этого непонятно, что является страницей, что является компонентом, что относится к API, а что является общей логикой.

---

## 1. Карта переноса из `App.tsx`

### 1.1. Что вынести из верхней части `App.tsx`

| Сейчас в `App.tsx` | Куда перенести | Комментарий |
|---|---|---|
| `roleLabels` | `src/shared/constants/roleLabels.ts` | Общий словарь ролей |
| `SectionId` | `src/app/navigation/types.ts` | Тип разделов приложения |
| `DataScope` | `src/shared/types/scope.ts` | `demo / work` используется в разных местах |
| `NavItem` | `src/app/navigation/types.ts` | Тип элемента меню |
| `navForRole()` | `src/app/navigation/navForRole.ts` | Логика меню не должна лежать в `App.tsx` |
| `displayFte()` | `src/shared/utils/formatters.ts` | Уже повторяется в других местах |
| `MetricCard` | `src/components/MetricCard/index.tsx` | Переиспользуемая карточка |
| `Metrics` | `src/components/SummaryMetrics/index.tsx` | Блок метрик по summary |
| `LoginScreen` | `src/pages/LoginPage/index.tsx` | Это отдельная страница |
| `WorkContourPlaceholder` | `src/components/WorkContourPlaceholder/index.tsx` | Небольшой общий блок-заглушка |
| `StructureDeleteConfirm` | `src/components/StructureDeleteConfirm/index.tsx` | Модалка подтверждения удаления |

### 1.2. Какие страницы сделать из условий `activeSection`

| Условие в `App.tsx` | Новая страница |
|---|---|
| `activeSection === "profile"` | `src/pages/ProfilePage/index.tsx` |
| `activeSection === "structure"` | `src/pages/StructurePage/index.tsx` |
| `activeSection === "campaigns"` | `src/pages/CampaignsPage/index.tsx` |
| `activeSection === "documents"` | `src/pages/DocumentsPage/index.tsx` |
| `activeSection === "analytics"` | `src/pages/AnalyticsPage/index.tsx` |
| `activeSection === "settings"` | `src/pages/SettingsPage/index.tsx` |
| `activeSection === "hr-reviews"` | `src/pages/HrReviewsPage/index.tsx` |
| `activeSection === "manager-overview"` | `src/pages/ManagerOverviewPage/index.tsx` |
| `activeSection === "manager-reviews"` | `src/pages/ManagerReviewsPage/index.tsx` |

### 1.3. Что оставить в `App.tsx`

В `App.tsx` оставить только:

```tsx
export default function App() {
  return (
    <AppProviders>
      <AppLayout>
        <CurrentPage />
      </AppLayout>
    </AppProviders>
  );
}
```

На первом этапе можно не вводить роутер. Можно оставить текущий `activeSection`, но сам рендер разделов вынести в `CurrentPage`.

Пример:

```tsx
function CurrentPage() {
  switch (activeSection) {
    case "profile":
      return <ProfilePage />;
    case "structure":
      return <StructurePage />;
    case "campaigns":
      return <CampaignsPage />;
    case "documents":
      return <DocumentsPage />;
    default:
      return null;
  }
}
```

---

## 2. Карта переноса `api.ts`

Сейчас `api.ts` содержит всё: auth, settings, organization, HR, campaigns, documents, profile, reviews, exports.

На этом этапе не нужно переводить frontend на другой query-стек. Сначала надо разнести текущие fetch/request-хелперы по доменам и оставить существующий `request()` helper как общий слой.

### 2.1. Общие файлы API

```txt
src/api/
  urls.ts
  request.ts
  types.ts
```

### 2.2. Модули API

| Функции из текущего `api.ts` | Новый файл |
|---|---|
| `getHealth` | `src/api/systemApi.ts` |
| `getDemoUsers` | `src/api/demoApi.ts` |
| `getMe`, `loginWithPassword`, `logoutAuth`, `requestMagicLink`, `consumeMagicLink` | `src/api/authApi.ts` |
| `getAiSettings`, `updateAiSettings`, `getQuestionnaireSettings`, `updateQuestionnaireSettings` | `src/api/settingsApi.ts` |
| `getTree`, `getSummary`, `getWorkTree`, `getWorkSummary`, `getManagerOptions` | `src/api/organizationApi.ts` |
| `bulkAddEmployees`, `importWorkEmployees`, `createWorkStaffingLine`, `deleteWorkAssignment`, `deleteWorkStaffingLine` | `src/api/structureApi.ts` |
| `resetDemoData` | `src/api/demoApi.ts` |
| `getCampaigns`, `createCampaign`, `createCampaignWave`, `launchCampaignWave`, `editCampaignWave`, `includeBranch`, `excludeBranch`, `setCampaignAssignments` | `src/api/campaignsApi.ts` |
| `getRecentAudit` | `src/api/auditApi.ts` |
| `getHrAnalytics`, `getManagerOverview` | `src/api/analyticsApi.ts` |
| `getHrDocuments`, `getManagerDocuments`, `setWorkDocumentLink`, `uploadWorkDocument`, `reviewWorkDocumentQuality`, `downloadWorkDocumentSource` | `src/api/documentsApi.ts` |
| `downloadHrExport`, `downloadCredentialsExport`, `issueWaveCredentialsExport`, `downloadProfileTemplateExport` | `src/api/exportApi.ts` |
| `getMyProfiles`, `saveProfileDraft`, `submitProfile`, `checkProfileAnswer` | `src/api/profileApi.ts` |
| `getManagerReviews`, `takeProfileForReview`, `returnProfileForRevision`, `bulkReturnProfilesForRevision`, `verifyProfileByManager` | `src/api/managerReviewApi.ts` |
| `getHrProfileReviews`, `acceptProfileByHr`, `returnProfileByHr`, `bulkReturnProfilesByHr` | `src/api/hrReviewApi.ts` |

### 2.3. `urls.ts`

Все URL вынести отдельно:

```ts
export const API_URL = {
  system: {
    health: "/api/health",
  },
  auth: {
    me: "/api/me",
    login: "/api/auth/login",
    logout: "/api/auth/logout",
    requestMagicLink: "/api/auth/magic-link/request",
    consumeMagicLink: "/api/auth/magic-link/consume",
  },
  organization: {
    tree: "/api/organization/tree",
    summary: "/api/organization/summary",
    workTree: "/api/work/organization/tree",
    workSummary: "/api/work/organization/summary",
    managers: "/api/hr/managers",
    workManagers: "/api/work/hr/managers",
  },
};
```

### 2.4. `request.ts`

`request.ts` должен остаться общим helper-слоем для JSON/blob запросов, чтобы его можно было переиспользовать в доменных модулях.

### 2.5. Переходный re-export

На переходный период можно оставить `src/api.ts` как фасад, который реэкспортит доменные функции. Это позволит переносить модули постепенно и не ломать импорты одним большим MR.

### 2.6. Что не делать здесь

- Не вводить Redux/RTK Query только ради рефакторинга.
- Не менять backend API.
- Не менять payloads и ответы.
- Не менять поведение экранов.

---

## 3. Карта переноса `types.ts`

Сейчас `types.ts` содержит все типы проекта. Его лучше дробить по доменам.

```txt
src/shared/types/
  common.ts
  scope.ts

src/api/types/
  auth.ts
  system.ts
  settings.ts
  organization.ts
  structure.ts
  campaigns.ts
  documents.ts
  analytics.ts
  profile.ts
  reviews.ts
  exports.ts
```

### 3.1. Куда переносить типы

| Типы из `types.ts` | Новый файл |
|---|---|
| `AiStatus`, `Health` | `src/api/types/system.ts` |
| `DemoUser`, `AuthUser`, `AuthSession`, `MagicLinkResponse` | `src/api/types/auth.ts` |
| `AiAnswerCheckResult` | `src/api/types/profile.ts` |
| `AiConfigurationMode`, `AiProvider`, `AiConfiguration`, `AiConfigurationInput` | `src/api/types/settings.ts` |
| `QuestionnaireQuestionSetting`, `QuestionnaireSettings`, `QuestionnaireQuestionSettingInput`, `QuestionnaireSettingsInput` | `src/api/types/settings.ts` |
| `Assignment`, `Position`, `OrgNode`, `Tree`, `Summary`, `ManagerOption` | `src/api/types/organization.ts` |
| `NewEmployee`, `BulkEmployeeResult`, `WorkEmployeeImportResult`, `WorkStaffingEmployeeInput`, `WorkStaffingLineInput`, `WorkStaffingLineResult`, `StructureDeleteResult` | `src/api/types/structure.ts` |
| `DemoResetResult` | `src/api/types/demo.ts` |
| `Campaign`, `CampaignWave` | `src/api/types/campaigns.ts` |
| `AuditEvent` | `src/api/types/audit.ts` |
| `DocumentGap`, `DocumentCoverageItem`, `DocumentLink`, `DocumentRecord`, `DocumentMatrixCell`, `DocumentPositionMatrixRow`, `DocumentRegistry` | `src/api/types/documents.ts` |
| `HrAnalytics`, `ManagerOverview`, `ManagerOverviewUnit`, `ManagerProfileSignal`, `ProfileDocumentSignal`, `DocumentAnomalyCheck` | `src/api/types/analytics.ts` |
| `ProfileQuestion`, `ProfileAssistedSections`, `ProfileRevision`, `ProfileReviewEvent`, `EmployeeProfile` | `src/api/types/profile.ts` |
| `ManagerReviewProfile`, `HrReviewProfile`, `BulkReviewReturnResult` | `src/api/types/reviews.ts` |

### 3.2. Общий re-export

Чтобы импорты не сломались сразу, можно временно оставить `src/types.ts` как re-export:

```ts
export * from "./api/types/auth";
export * from "./api/types/system";
export * from "./api/types/settings";
export * from "./api/types/organization";
export * from "./api/types/structure";
export * from "./api/types/campaigns";
export * from "./api/types/documents";
export * from "./api/types/analytics";
export * from "./api/types/profile";
export * from "./api/types/reviews";
```

Так можно переносить типы постепенно.

---

## 4. Карта переноса текущих компонентов

### 4.1. Оставить как страницы или крупные feature-компоненты

| Текущий файл | Куда перенести |
|---|---|
| `ProfileWorkspace.tsx` | `src/features/profile/ProfileWorkspace/index.tsx` |
| `DocumentPanel.tsx` | `src/features/documents/DocumentPanel/index.tsx` |
| `HrAnalyticsPanel.tsx` | `src/features/analytics/HrAnalyticsPanel/index.tsx` |
| `HrReviewPanel.tsx` | `src/features/reviews/HrReviewPanel/index.tsx` |
| `ManagerOverviewPanel.tsx` | `src/features/managerOverview/ManagerOverviewPanel/index.tsx` |
| `ManagerReviewPanel.tsx` | `src/features/reviews/ManagerReviewPanel/index.tsx` |
| `OrganizationTreePanel.tsx` | `src/features/organization/OrganizationTreePanel/index.tsx` |
| `SettingsPanel.tsx` | `src/features/settings/SettingsPanel/index.tsx` |
| `HrControls.tsx` | разделить, см. ниже |
| `BulkReturnBox.tsx` | `src/components/BulkReturnBox/index.tsx` |

### 4.2. Разделить `HrControls.tsx`

`HrControls.tsx` сейчас содержит несколько разных компонентов. Лучше разнести так:

```txt
src/features/structure/EmployeeModal/
  index.tsx
  style.ts
  types.ts

src/features/structure/StaffingLineModal/
  index.tsx
  style.ts
  types.ts

src/features/demo/DemoResetPanel/
  index.tsx
  style.ts
  types.ts

src/features/campaigns/CampaignPanel/
  index.tsx
  style.ts
  types.ts
```

---

## 5. Повторяющиеся места, которые стоит вынести

### 5.1. Повторяющиеся функции

| Повтор | Куда вынести |
|---|---|
| `displayFte()` | `src/shared/utils/formatters.ts` |
| `formatTimestamp()` / работа с датами | `src/shared/utils/date.ts` |
| `formatAnswer()` | `src/shared/utils/profileAnswers.ts` |
| `assistantUsageLabel()` | `src/shared/utils/assistantUsage.ts` |
| `answerText()` | `src/shared/utils/profileAnswers.ts` |
| `visibleTree()` / `filterTree()` | пока не объединять сразу, см. риски |
| `statusLabels` | `src/shared/constants/statusLabels.ts` |

### 5.2. Повторяющиеся UI-блоки

| UI-блок | Куда вынести |
|---|---|
| Карточка метрики | `src/components/MetricCard` |
| Информационный alert | `src/components/InfoAlert` |
| Error-блок | `src/components/ErrorMessage` |
| Loading-текст/блок | `src/components/LoadingState` |
| Empty state | `src/components/EmptyState` |
| Модальное окно подтверждения | `src/components/ConfirmModal` |
| Блок массового возврата | уже есть `BulkReturnBox`, перенести в `components` |

---

## 6. Что пока лучше не трогать

Эти места лучше сначала только перенести как есть, без внутренней переработки:

| Место | Почему рискованно |
|---|---|
| `ProfileWorkspace.tsx` | там анкета, localStorage-черновик, таблицы, AI-проверки, статусы ответов |
| `DocumentPanel.tsx` | там привязка документов, upload, OCR quality, матрица покрытия |
| `OrganizationTreePanel.tsx` | там выбор веток, включение/исключение кампаний, дерево |
| `CampaignPanel` из `HrControls.tsx` | волны, активная кампания, выдача доступов, экспорт |
| review-flow в `ManagerReviewPanel` и `HrReviewPanel` | статусы профилей и массовый возврат |
| auth-логика в `App.tsx` | токен, magic link, сброс сессии |

Правило: сначала переносим файл/кусок как есть. После этого уже дробим внутреннюю логику.

---

## 7. Предлагаемый порядок MR

### MR 1 – подготовка структуры

Создать папки:

```txt
src/app
src/pages
src/features
src/components
src/api
src/hooks
src/shared
```

Пока без изменения логики.

---

### MR 2 – вынести простые shared-части из `App.tsx`

Перенести:

```txt
roleLabels
navForRole
displayFte
MetricCard
Metrics
WorkContourPlaceholder
```

Цель – уменьшить `App.tsx`, не меняя поведение.

---

### MR 3 – вынести `LoginPage`

Перенести `LoginScreen` в:

```txt
src/pages/LoginPage/
  index.tsx
  style.ts
  types.ts
```

Auth-запросы пока можно оставить в старом `api.ts`.

---

### MR 4 – вынести layout и навигацию

Создать:

```txt
src/app/AppLayout/
  index.tsx
  style.ts

src/app/navigation/
  navForRole.ts
  types.ts
```

В `App.tsx` оставить только состояние активного раздела и выбор страницы.

---

### MR 5 – вынести страницы из `App.tsx`

Создать страницы:

```txt
pages/ProfilePage
pages/StructurePage
pages/CampaignsPage
pages/DocumentsPage
pages/AnalyticsPage
pages/SettingsPage
pages/HrReviewsPage
pages/ManagerOverviewPage
pages/ManagerReviewsPage
```

На этом этапе страницы могут получать много props из `App.tsx`. Это нормально.

---

### MR 6 – разнести `HrControls.tsx`

Разделить:

```txt
EmployeeModal
StaffingLineModal
DemoResetPanel
CampaignPanel
```

Логику не менять.

---

### MR 7 – разнести `types.ts`

Разнести типы по доменам.

Оставить временный `src/types.ts` с re-export, чтобы не переписывать все импорты сразу.

---

### MR 8 – разнести `api.ts` по обычным модулям

Сначала без RTK Query:

```txt
api/auth.ts
api/profile.ts
api/organization.ts
api/campaigns.ts
api/documents.ts
api/reviews.ts
api/analytics.ts
```

Общий `request()` временно оставить в `api/request.ts`.

---

### MR 9 – подключить `RTK Query`

Добавить:

```txt
api/baseApi.ts
app/store.ts
app/providers.tsx
```

Переводить запросы по одному домену:

1. `authApi`
2. `profileApi`
3. `organizationApi`
4. `campaignsApi`
5. `documentsApi`
6. `reviewsApi`
7. `analyticsApi`
8. `settingsApi`

Не переводить всё за один MR.

---

### MR 10 – перенести локальную page-логику в hooks

После RTK Query:

```txt
hooks/useAuth.ts
hooks/useProfileDraft.ts
hooks/useCampaignSelection.ts
hooks/useStructureActions.ts
hooks/useDocumentActions.ts
hooks/useReviewActions.ts
```

---

### MR 11 – styled-components

Постепенно заменить большие куски Tailwind/обычного JSX на `styled-components`.

Начинать с новых/вынесенных страниц:

```txt
pages/LoginPage/style.ts
pages/ProfilePage/style.ts
pages/StructurePage/style.ts
components/MetricCard/style.ts
components/ConfirmModal/style.ts
```

---

### MR 12 – тесты основных сценариев

Добавить e2e-тесты на ключевые сценарии:

1. HR login.
2. HR видит структуру.
3. HR создаёт кампанию/волну.
4. Сотрудник заполняет и отправляет анкету.
5. Руководитель возвращает/подтверждает профиль.
6. HR принимает профиль.
7. HR открывает документы и аналитику.

---

## 8. Итоговая целевая структура

```txt
src/
  app/
    App.tsx
    AppLayout/
    navigation/
    providers.tsx
    store.ts

  pages/
    LoginPage/
    ProfilePage/
    StructurePage/
    CampaignsPage/
    DocumentsPage/
    AnalyticsPage/
    SettingsPage/
    HrReviewsPage/
    ManagerOverviewPage/
    ManagerReviewsPage/

  features/
    profile/
    organization/
    campaigns/
    documents/
    analytics/
    settings/
    reviews/
    structure/
    demo/

  components/
    MetricCard/
    SummaryMetrics/
    BulkReturnBox/
    ConfirmModal/
    ErrorMessage/
    LoadingState/
    EmptyState/
    InfoAlert/

  api/
    baseApi.ts
    urls.ts
    authApi.ts
    systemApi.ts
    settingsApi.ts
    organizationApi.ts
    structureApi.ts
    campaignsApi.ts
    documentsApi.ts
    profileApi.ts
    managerReviewApi.ts
    hrReviewApi.ts
    analyticsApi.ts
    exportApi.ts
    auditApi.ts
    types/

  hooks/
    useAuth.ts
    useProfileDraft.ts
    useCampaignSelection.ts
    useStructureActions.ts
    useDocumentActions.ts
    useReviewActions.ts

  shared/
    constants/
    utils/
    types/
```

---

## 9. Самое важное правило

Не делать одновременно:

- перенос файлов;
- смену API layer;
- замену React Query на RTK Query;
- замену Tailwind на styled-components;
- изменение логики.

Каждый MR должен делать один тип изменения.
