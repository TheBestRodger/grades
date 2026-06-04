import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  bulkAddEmployees,
  bulkReturnProfilesByHr,
  bulkReturnProfilesForRevision,
  acceptProfileByHr,
  checkProfileAnswer,
  createCampaign,
  createCampaignWave,
  downloadWorkDocumentSource,
  downloadHrExport,
  downloadProfileTemplateExport,
  excludeBranch,
  getCampaigns,
  getHealth,
  getAiSettings,
  getHrAnalytics,
  getHrDocuments,
  getHrProfileReviews,
  getMe,
  getManagerDocuments,
  getManagerOptions,
  getManagerOverview,
  getManagerReviews,
  getMyProfiles,
  getQuestionnaireSettings,
  getRecentAudit,
  getSummary,
  getTree,
  getWorkSummary,
  getWorkTree,
  editCampaignWave,
  includeBranch,
  issueWaveCredentialsExport,
  launchCampaignWave,
  loginWithPassword,
  logoutAuth,
  consumeMagicLink,
  resetDemoData,
  reviewWorkDocumentQuality,
  returnProfileByHr,
  saveProfileDraft,
  setWorkDocumentLink,
  setCampaignAssignments,
  submitProfile,
  takeProfileForReview,
  returnProfileForRevision,
  verifyProfileByManager,
  uploadWorkDocument,
  updateAiSettings,
  updateQuestionnaireSettings,
} from "./api";
import { DocumentPanel } from "./DocumentPanel";
import {
  CampaignPanel,
  DemoResetPanel,
  EmployeeModal,
} from "./HrControls";
import { HrAnalyticsPanel } from "./HrAnalyticsPanel";
import { HrReviewPanel } from "./HrReviewPanel";
import { ManagerOverviewPanel } from "./ManagerOverviewPanel";
import { ManagerReviewPanel } from "./ManagerReviewPanel";
import { OrganizationTreePanel } from "./OrganizationTreePanel";
import { ProfileWorkspace } from "./ProfileWorkspace";
import { SettingsPanel } from "./SettingsPanel";
import type {
  Campaign,
  DemoUser,
  EmployeeProfile,
  NewEmployee,
  OrgNode,
  Position,
  Summary,
  AiAnswerCheckResult,
} from "./types";

type ProfileAiUsagePayload = {
  ai_checked_questions: string[];
  ai_ignored_questions: string[];
  ai_without_ai_questions?: string[];
  ai_answer_statuses?: Record<string, "accepted" | "ignored" | "rejected" | "without_ai">;
};

const roleLabels: Record<DemoUser["role"], string> = {
  hr: "HR",
  manager: "Руководитель",
  employee: "Сотрудник",
};

function displayFte(value: number | null): string {
  return value === null ? "-" : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

type SectionId =
  | "profile"
  | "structure"
  | "campaigns"
  | "manager-overview"
  | "manager-reviews"
  | "hr-reviews"
  | "documents"
  | "analytics"
  | "settings"
  | "export";

type DataScope = "demo" | "work";

interface NavItem {
  id: SectionId;
  label: string;
  note: string;
  disabled?: boolean;
}

function navForRole(role?: DemoUser["role"]): NavItem[] {
  if (!role) return [];
  if (role === "employee") {
    return [{ id: "profile", label: "Моя анкета", note: "статус и заполнение" }];
  }
  if (role === "manager") {
    return [
      { id: "profile", label: "Моя анкета", note: "свой профиль" },
      { id: "manager-overview", label: "Анализ", note: "heat map и drill-down" },
      { id: "manager-reviews", label: "Проверка", note: "профили подчиненных" },
      { id: "documents", label: "Документы", note: "моя зона" },
      { id: "structure", label: "Структура", note: "моя ветка" },
    ];
  }
  return [
    { id: "structure", label: "Структура", note: "сотрудники и ставки" },
    { id: "campaigns", label: "Кампании", note: "включение веток" },
    { id: "hr-reviews", label: "Финальная проверка", note: "решения HR" },
    { id: "documents", label: "Документы", note: "ДИ и покрытия" },
    { id: "analytics", label: "Аналитика", note: "KPI и воронка" },
    { id: "profile", label: "Моя анкета", note: "свой профиль" },
  ];
}

function MetricCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  );
}

function Metrics({ summary, profile }: { summary: Summary; profile: EmployeeProfile | null }) {
  if (summary.scope === "self") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard label="Доступ" value="Свой профиль" note="Данные ветки скрыты правилами доступа" />
        <MetricCard
          label="Заполнение анкеты"
          value={profile ? `${Math.round(profile.progress_percent)}%` : "Не назначено"}
          note={profile ? "Сохраненный прогресс в активной кампании" : "Нет участия в активной кампании"}
        />
      </div>
    );
  }
  if (summary.scope === "work") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Штатные позиции"
          value={String(summary.staffing_lines)}
          note="Загружено в рабочую структуру"
        />
        <MetricCard
          label="Занято по ШР"
          value={displayFte(summary.assigned_fte)}
          note="Колонка «Занято», без персональных данных"
        />
        <MetricCard
          label="Ставки по ШР"
          value={displayFte(summary.approved_fte)}
          note="Сумма поля «Ед. по ШР»"
        />
        <MetricCard
          label="Свободно ставок"
          value={displayFte(summary.vacancy_fte)}
          note="Расчет из ШР: всего минус занято"
        />
      </div>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Штатные позиции"
        value={String(summary.staffing_lines)}
        note="В доступной ветке"
      />
      <MetricCard
        label="Сотрудники"
        value={String(summary.employees)}
        note="Добавленные назначения"
      />
      <MetricCard
        label="Ставки по ШР"
        value={displayFte(summary.approved_fte)}
        note={`Занято: ${displayFte(summary.assigned_fte)}`}
      />
      <MetricCard
        label="Свободно ставок"
        value={displayFte(summary.vacancy_fte)}
        note="Вакансии являются нормальным состоянием"
      />
    </div>
  );
}

function LoginScreen({
  authError,
  authMessage,
  isRequesting,
  onLogin,
}: {
  authError: string | null;
  authMessage: string | null;
  isRequesting: boolean;
  onLogin: (username: string, password: string) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onLogin(username, password);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-10 text-slate-800">
      <section className="w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="grid lg:grid-cols-[1fr_420px]">
          <div className="p-8 lg:p-10">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-blue-950 px-3 py-2 font-bold text-white">МГТУ</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
                  Профилирование должностей
                </p>
                <h1 className="text-2xl font-bold text-slate-950">Вход в систему</h1>
              </div>
            </div>

            <div className="mt-8 max-w-xl">
              <p className="text-sm text-slate-600">
                Введите логин и временный пароль, выданные HR. После входа откроется личный кабинет
                сотрудника, руководителя или HR.
              </p>
              {(authMessage || authError) && (
                <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm">
                  {authMessage && <p className="text-blue-950">{authMessage}</p>}
                  {authError && <p className="mt-1 text-red-700">{authError}</p>}
                </div>
              )}
            </div>
          </div>

          <aside className="border-t border-slate-100 bg-slate-50 p-8 lg:border-l lg:border-t-0 lg:p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Авторизация
            </p>
            <h2 className="mt-2 text-xl font-bold text-slate-950">Вход по логину и паролю</h2>
            <form className="mt-5 space-y-4" onSubmit={submit}>
              <label className="block text-sm font-medium text-slate-700">
                Логин
                <input
                  autoComplete="username"
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="login"
                  required
                  value={username}
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Пароль
                <input
                  autoComplete="current-password"
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="пароль"
                  required
                  type="password"
                  value={password}
                />
              </label>
              <button
                className="w-full rounded-xl bg-blue-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
                disabled={isRequesting}
                type="submit"
              >
                {isRequesting ? "Вхожу..." : "Войти"}
              </button>
            </form>
          </aside>
        </div>
      </section>
    </main>
  );
}

function WorkContourPlaceholder() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
        Рабочий контур
      </p>
      <h2 className="mt-2 text-xl font-bold text-slate-950">Данные пока не загружены</h2>
      <p className="mt-2 max-w-3xl text-sm text-slate-600">
        Структура и документальное покрытие рабочего ШР уже доступны в соответствующих вкладках.
        Для кампаний, проверок и профилей нужен следующий слой: добавление сотрудников, руководителей
        и ручное сопоставление документов.
      </p>
      <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
        <p className="font-semibold text-slate-900">Будущая схема</p>
        <p className="mt-2">Организация → подразделения → штатные строки → назначения сотрудников → кампании.</p>
      </div>
    </section>
  );
}

export default function App() {
  const queryClient = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(() =>
    window.localStorage.getItem("auth_token"),
  );
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<SectionId>("structure");
  const dataScope = useMemo<DataScope>(() => "work", []);
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const authMe = useQuery({
    queryKey: ["me", authToken],
    queryFn: getMe,
    enabled: Boolean(authToken),
    retry: false,
  });
  const passwordLoginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      loginWithPassword(username, password),
    onSuccess: async (session) => {
      window.localStorage.setItem("auth_token", session.token);
      setAuthToken(session.token);
      setSelectedUserId(session.user.id);
      setAuthMessage(`Вход выполнен: ${roleLabels[session.user.role]} ${session.user.full_name}.`);
      await queryClient.invalidateQueries();
    },
  });

  const consumeMagicLinkMutation = useMutation({
    mutationFn: consumeMagicLink,
    onSuccess: async (session) => {
      window.localStorage.setItem("auth_token", session.token);
      setAuthToken(session.token);
      setSelectedUserId(session.user.id);
      setAuthMessage(`Вход выполнен: ${roleLabels[session.user.role]} ${session.user.full_name}.`);
      window.history.replaceState({}, document.title, window.location.pathname);
      await queryClient.invalidateQueries();
    },
    onError: () => {
      window.history.replaceState({}, document.title, window.location.pathname);
    },
  });

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("auth_token");
    if (!token || authToken || consumeMagicLinkMutation.isPending || consumeMagicLinkMutation.isSuccess) return;
    consumeMagicLinkMutation.mutate(token);
  }, [authToken, consumeMagicLinkMutation]);

  useEffect(() => {
    if (authMe.error) {
      window.localStorage.removeItem("auth_token");
      setAuthToken(null);
      setAuthMessage("Сессия истекла или была завершена. Можно войти заново.");
    }
  }, [authMe.error]);

  useEffect(() => {
    if (!authMe.data) return;
    setSelectedUserId(authMe.data.id);
  }, [authMe.data]);

  const selectedUser = authMe.data;
  const activeUser = authMe.data;
  const navItems = useMemo(() => navForRole(activeUser?.role), [activeUser?.role]);
  const isHr = activeUser?.role === "hr";
  const isManager = activeUser?.role === "manager";

  useEffect(() => {
    const activeItem = navItems.find((item) => item.id === activeSection && !item.disabled);
    if (!activeItem) {
      setActiveSection(navItems.find((item) => !item.disabled)?.id ?? "profile");
    }
  }, [activeSection, navItems]);

  const summary = useQuery({
    queryKey: ["summary", selectedUserId],
    queryFn: () => getSummary(selectedUserId!),
    enabled: selectedUserId !== null,
  });
  const tree = useQuery({
    queryKey: ["tree", selectedUserId],
    queryFn: () => getTree(selectedUserId!),
    enabled: selectedUserId !== null,
  });
  const workTree = useQuery({
    queryKey: ["work-tree", selectedUserId],
    queryFn: () => getWorkTree(selectedUserId!),
    enabled: selectedUserId !== null && (isHr || dataScope === "work"),
  });
  const workSummary = useQuery({
    queryKey: ["work-summary", selectedUserId],
    queryFn: () => getWorkSummary(selectedUserId!),
    enabled: selectedUserId !== null && (isHr || dataScope === "work"),
  });
  const managers = useQuery({
    queryKey: ["managers", selectedUserId],
    queryFn: () => getManagerOptions(selectedUserId!),
    enabled: selectedUserId !== null && isHr,
  });
  const workManagers = useQuery({
    queryKey: ["work-managers", selectedUserId],
    queryFn: () => getManagerOptions(selectedUserId!, "work"),
    enabled: selectedUserId !== null && isHr,
  });
  const campaigns = useQuery({
    queryKey: ["campaigns", selectedUserId, dataScope],
    queryFn: () => getCampaigns(selectedUserId!, dataScope),
    enabled: selectedUserId !== null && isHr,
  });
  const audit = useQuery({
    queryKey: ["audit", selectedUserId, dataScope],
    queryFn: () => getRecentAudit(selectedUserId!, dataScope),
    enabled: selectedUserId !== null && isHr,
  });
  const hrAnalytics = useQuery({
    queryKey: ["hr-analytics", selectedUserId, dataScope],
    queryFn: () => getHrAnalytics(selectedUserId!, dataScope),
    enabled: selectedUserId !== null && isHr,
  });
  const aiSettings = useQuery({
    queryKey: ["ai-settings", selectedUserId],
    queryFn: () => getAiSettings(selectedUserId!),
    enabled: selectedUserId !== null && isHr,
  });
  const questionnaireSettings = useQuery({
    queryKey: ["questionnaire-settings", selectedUserId],
    queryFn: () => getQuestionnaireSettings(selectedUserId!),
    enabled: selectedUserId !== null && isHr,
  });
  const hrReviews = useQuery({
    queryKey: ["hr-profile-reviews", selectedUserId, dataScope],
    queryFn: () => getHrProfileReviews(selectedUserId!, dataScope),
    enabled: selectedUserId !== null && isHr,
  });
  const documents = useQuery({
    queryKey: ["hr-documents", selectedUserId, dataScope],
    queryFn: () => getHrDocuments(selectedUserId!, dataScope),
    enabled: selectedUserId !== null && isHr,
  });
  const personalProfiles = useQuery({
    queryKey: ["my-profiles", selectedUserId],
    queryFn: () => getMyProfiles(selectedUserId!),
    enabled: selectedUserId !== null,
  });
  const managerReviews = useQuery({
    queryKey: ["manager-reviews", selectedUserId],
    queryFn: () => getManagerReviews(selectedUserId!),
    enabled: selectedUserId !== null && isManager,
  });
  const managerOverview = useQuery({
    queryKey: ["manager-overview", selectedUserId],
    queryFn: () => getManagerOverview(selectedUserId!),
    enabled: selectedUserId !== null && isManager,
  });
  const managerDocuments = useQuery({
    queryKey: ["manager-documents", selectedUserId],
    queryFn: () => getManagerDocuments(selectedUserId!),
    enabled: selectedUserId !== null && isManager,
  });
  const [employeeTarget, setEmployeeTarget] = useState<Position | null>(null);
  const [activeCampaignId, setActiveCampaignId] = useState<number | null>(null);
  const [activeWaveId, setActiveWaveId] = useState<number | null>(null);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [includingUnitId, setIncludingUnitId] = useState<number | null>(null);
  const [excludingUnitId, setExcludingUnitId] = useState<number | null>(null);
  const [reviewActionProfileId, setReviewActionProfileId] = useState<number | null>(null);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [hrDecisionProfileId, setHrDecisionProfileId] = useState<number | null>(null);
  const [hrDecisionMessage, setHrDecisionMessage] = useState<string | null>(null);
  const [assigningDocumentKey, setAssigningDocumentKey] = useState<string | null>(null);
  const [reviewingDocumentId, setReviewingDocumentId] = useState<number | null>(null);
  const [documentDownloadError, setDocumentDownloadError] = useState<string | null>(null);
  const [changingAssignmentId, setChangingAssignmentId] = useState<number | null>(null);
  const [aiCheckResults, setAiCheckResults] = useState<Record<string, AiAnswerCheckResult>>({});
  const [aiCheckingKey, setAiCheckingKey] = useState<string | null>(null);
  const [aiCheckErrorKey, setAiCheckErrorKey] = useState<string | null>(null);
  const [aiAnswerSnapshots, setAiAnswerSnapshots] = useState<Record<string, string>>({});
  const [credentialsFileBlob, setCredentialsFileBlob] = useState<Blob | null>(null);
  const [preparingCredentials, setPreparingCredentials] = useState(false);

  const logoutMutation = useMutation({
    mutationFn: logoutAuth,
    onSuccess: async () => {
      window.localStorage.removeItem("auth_token");
      setAuthToken(null);
      setAuthMessage("Рабочая сессия завершена, снова доступен выбор пользователя.");
      await queryClient.invalidateQueries();
    },
  });
  const aiSettingsMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateAiSettings>[1]) =>
      updateAiSettings(selectedUserId!, payload),
    onSuccess: async (configuration) => {
      queryClient.setQueryData(["ai-settings", selectedUserId], configuration);
      setOperationMessage("Настройки ИИ сохранены. Реальные вызовы LLM пока остаются отключёнными.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["health"] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
    },
  });
  const questionnaireSettingsMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateQuestionnaireSettings>[1]) =>
      updateQuestionnaireSettings(selectedUserId!, payload),
    onSuccess: async (settings) => {
      queryClient.setQueryData(["questionnaire-settings", selectedUserId], settings);
      setOperationMessage("Настройки открытых ответов сохранены.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["my-profiles"] }),
        queryClient.invalidateQueries({ queryKey: ["manager-reviews"] }),
        queryClient.invalidateQueries({ queryKey: ["hr-profile-reviews"] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
    },
  });

  useEffect(() => {
    if (!campaigns.data?.length) {
      setActiveCampaignId(null);
      return;
    }
    if (!activeCampaignId || !campaigns.data.some((campaign) => campaign.id === activeCampaignId)) {
      setActiveCampaignId(campaigns.data[0].id);
    }
  }, [activeCampaignId, campaigns.data]);

  const activeCampaign =
    campaigns.data?.find((campaign) => campaign.id === activeCampaignId) ?? null;
  const activeWave =
    activeCampaign?.waves.find((wave) => wave.id === activeWaveId) ??
    activeCampaign?.waves.find((wave) => wave.id === activeCampaign.active_wave_id) ??
    activeCampaign?.waves[0] ??
    null;
  const activeCampaignForTree = useMemo<Campaign | null>(() => {
    if (!activeCampaign || !activeWave) return activeCampaign;
    return {
      ...activeCampaign,
      active_wave_id: activeWave.id,
      active_wave_name: activeWave.name,
      participants_expected: activeWave.participants_expected,
      participant_assignment_ids: activeWave.participant_assignment_ids,
      selected_org_unit_ids: activeWave.selected_org_unit_ids,
      selected_units_count: activeWave.selected_units_count,
      selected_staffing_lines: activeWave.selected_staffing_lines,
      selected_approved_fte: activeWave.selected_approved_fte,
      status_counts: activeWave.status_counts,
    };
  }, [activeCampaign, activeWave]);

  useEffect(() => {
    if (!activeCampaign) {
      setActiveWaveId(null);
      return;
    }
    const waveIds = activeCampaign.waves.map((wave) => wave.id);
    if (!activeWaveId || !waveIds.includes(activeWaveId)) {
      setActiveWaveId(activeCampaign.active_wave_id ?? waveIds[0] ?? null);
    }
  }, [activeCampaign, activeWaveId]);

  useEffect(() => {
    setCredentialsFileBlob(null);
  }, [activeCampaignId, activeWaveId]);

  async function refreshHrViews() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["tree", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["summary", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["demo-users"] }),
      queryClient.invalidateQueries({ queryKey: ["campaigns", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["audit", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["hr-analytics", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["hr-profile-reviews", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["manager-overview"] }),
      queryClient.invalidateQueries({ queryKey: ["work-tree", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["work-summary", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["managers", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["work-managers", selectedUserId] }),
    ]);
  }

  const addEmployeesMutation = useMutation({
    mutationFn: (rows: NewEmployee[]) =>
      bulkAddEmployees(selectedUserId!, employeeTarget!.id, rows, dataScope),
    onSuccess: async (result) => {
      setOperationMessage(`Добавлено сотрудников: ${result.added.length}. Свободно ставок: ${result.remaining_fte}.`);
      setCredentialsFileBlob(null);
      setEmployeeTarget(null);
      await refreshHrViews();
    },
  });
  const demoResetMutation = useMutation({
    mutationFn: () => resetDemoData(selectedUserId!),
    onSuccess: async (result) => {
      setOperationMessage(
        result.work_unchanged
          ? "Контур сброшен, рабочие данные сохранены."
          : "Контур сброшен, проверьте рабочий контур.",
      );
      await queryClient.invalidateQueries();
      setSelectedUserId(null);
    },
  });
  const createCampaignMutation = useMutation({
    mutationFn: ({ name, dueAt }: { name: string; dueAt: string | null }) =>
      createCampaign(selectedUserId!, name, dueAt, dataScope),
    onSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.active_wave_id);
      setOperationMessage(`Кампания «${campaign.name}» создана. Теперь выберите ветку.`);
      await refreshHrViews();
    },
  });
  const createWaveMutation = useMutation({
    mutationFn: ({ campaignId, name, dueAt }: { campaignId: number; name: string; dueAt: string | null }) =>
      createCampaignWave(selectedUserId!, campaignId, name, dueAt, dataScope),
    onSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.new_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`В кампании «${campaign.name}» создана волна «${campaign.new_wave_name}».`);
      await refreshHrViews();
    },
  });
  const launchWaveMutation = useMutation({
    mutationFn: ({ campaignId, waveId }: { campaignId: number; waveId: number }) =>
      launchCampaignWave(selectedUserId!, campaignId, waveId, dataScope),
    onSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.launched_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`Волна «${campaign.launched_wave_name}» запущена.`);
      await refreshHrViews();
    },
  });
  const editWaveMutation = useMutation({
    mutationFn: ({ campaignId, waveId }: { campaignId: number; waveId: number }) =>
      editCampaignWave(selectedUserId!, campaignId, waveId, dataScope),
    onSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.editing_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`Волна «${campaign.editing_wave_name}» взята в редакцию.`);
      await refreshHrViews();
    },
  });
  const includeMutation = useMutation({
    mutationFn: ({ campaignId, unitId, waveId }: { campaignId: number; unitId: number; waveId: number | null }) =>
      includeBranch(selectedUserId!, campaignId, unitId, waveId, dataScope),
    onSuccess: async (campaign) => {
      setOperationMessage(
        campaign.scope === "work"
          ? `Ветка «${campaign.included_unit_name}» включена в волну «${campaign.included_wave_name}»: новых участников ${campaign.new_participants ?? 0}.`
          : `Ветка «${campaign.included_unit_name}» включена в волну «${campaign.included_wave_name}»: новых участников ${campaign.new_participants}.`,
      );
      setIncludingUnitId(null);
      await refreshHrViews();
    },
    onError: () => setIncludingUnitId(null),
  });
  const excludeMutation = useMutation({
    mutationFn: ({ campaignId, unitId, waveId }: { campaignId: number; unitId: number; waveId: number | null }) =>
      excludeBranch(selectedUserId!, campaignId, unitId, waveId, dataScope),
    onSuccess: async (campaign) => {
      setOperationMessage(
        campaign.scope === "work"
          ? `Ветка «${campaign.excluded_unit_name}» снята из плана волны «${campaign.excluded_wave_name}».`
          : `Ветка «${campaign.excluded_unit_name}» выключена из волны «${campaign.excluded_wave_name}»: участников снято ${campaign.excluded_participants}.`,
      );
      setExcludingUnitId(null);
      await refreshHrViews();
    },
    onError: () => setExcludingUnitId(null),
  });
  const campaignAssignmentMutation = useMutation({
    mutationFn: ({ assignmentId, included }: { assignmentId: number; included: boolean }) =>
      setCampaignAssignments(
        selectedUserId!,
        activeCampaignId!,
        activeWaveId!,
        [assignmentId],
        included ? "include" : "exclude",
        dataScope,
      ),
    onSuccess: async (campaign) => {
      setOperationMessage(
        campaign.participant_action === "include"
          ? "Назначение включено в выбранную волну."
          : "Назначение исключено из выбранной волны.",
      );
      setChangingAssignmentId(null);
      await refreshHrViews();
    },
    onError: () => setChangingAssignmentId(null),
  });
  const documentLinkMutation = useMutation({
    mutationFn: ({
      staffingLineId,
      documentType,
      documentId,
    }: {
      staffingLineId: number;
      documentType: "job_instruction" | "unit_regulation" | "professional_standard";
      documentId: number | null;
    }) => setWorkDocumentLink(selectedUserId!, staffingLineId, documentType, documentId),
    onSuccess: async (registry) => {
      queryClient.setQueryData(["hr-documents", selectedUserId, "work"], registry);
      setAssigningDocumentKey(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["audit", selectedUserId, "work"] }),
        queryClient.invalidateQueries({ queryKey: ["hr-analytics", selectedUserId, "work"] }),
      ]);
    },
    onError: () => setAssigningDocumentKey(null),
  });
  const documentUploadMutation = useMutation({
    mutationFn: ({
      file,
      documentCode,
      documentType,
      title,
      version,
    }: {
      file: File;
      documentCode: string;
      documentType: "job_instruction" | "unit_regulation" | "professional_standard";
      title: string;
      version: string;
    }) =>
      uploadWorkDocument(selectedUserId!, file, {
        documentCode,
        documentType,
        title,
        version,
      }),
    onSuccess: async (registry) => {
      queryClient.setQueryData(["hr-documents", selectedUserId, "work"], registry);
      setOperationMessage("Оригинал документа загружен. Проверьте текст перед подтверждением связи.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["audit", selectedUserId, "work"] }),
        queryClient.invalidateQueries({ queryKey: ["hr-analytics", selectedUserId, "work"] }),
      ]);
    },
  });
  const documentQualityMutation = useMutation({
    mutationFn: ({
      documentId,
      status,
      text,
    }: {
      documentId: number;
      status: "good" | "warning";
      text: string;
    }) => reviewWorkDocumentQuality(selectedUserId!, documentId, status, text),
    onSuccess: async (registry) => {
      queryClient.setQueryData(["hr-documents", selectedUserId, "work"], registry);
      setReviewingDocumentId(null);
      setOperationMessage("Результат проверки текста сохранён в аудите.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["audit", selectedUserId, "work"] }),
        queryClient.invalidateQueries({ queryKey: ["hr-analytics", selectedUserId, "work"] }),
      ]);
    },
    onError: () => setReviewingDocumentId(null),
  });
  const saveDraftMutation = useMutation({
    mutationFn: ({
      profileId,
      answers,
      aiUsage,
    }: {
      profileId: number;
      answers: Record<string, string>;
      aiUsage: ProfileAiUsagePayload;
    }) => saveProfileDraft(selectedUserId!, profileId, answers, aiUsage),
    onSuccess: (updated) => {
      queryClient.setQueryData<EmployeeProfile[]>(
        ["my-profiles", selectedUserId],
        (existing) => existing?.map((profile) => (profile.id === updated.id ? updated : profile)) ?? [updated],
      );
      void queryClient.invalidateQueries({ queryKey: ["hr-analytics"] });
    },
  });
  const submitProfileMutation = useMutation({
    mutationFn: ({
      profileId,
      answers,
      aiUsage,
    }: {
      profileId: number;
      answers: Record<string, string>;
      aiUsage: ProfileAiUsagePayload;
    }) => submitProfile(selectedUserId!, profileId, answers, aiUsage),
    onSuccess: (updated) => {
      queryClient.setQueryData<EmployeeProfile[]>(
        ["my-profiles", selectedUserId],
        (existing) => existing?.map((profile) => (profile.id === updated.id ? updated : profile)) ?? [updated],
      );
      void queryClient.invalidateQueries({ queryKey: ["hr-analytics"] });
    },
  });
  const aiCheckMutation = useMutation({
    mutationFn: ({
      profileId,
      questionKey,
      answers,
    }: {
      profileId: number;
      questionKey: string;
      answers: Record<string, string>;
    }) => {
      const previous = aiCheckResults[questionKey];
      return checkProfileAnswer(selectedUserId!, profileId, questionKey, answers, {
        previous_answer: previous ? aiAnswerSnapshots[questionKey] ?? null : null,
        previous_followup_question: previous?.followup_question ?? null,
        previous_clarity_percent: previous?.clarity_percent ?? null,
      });
    },
    onSuccess: (result, variables) => {
      setAiCheckResults((existing) => ({ ...existing, [result.question_key]: result }));
      setAiAnswerSnapshots((existing) => ({
        ...existing,
        [result.question_key]: variables.answers[result.question_key] ?? "",
      }));
      setAiCheckingKey(null);
      setAiCheckErrorKey(null);
    },
    onError: (_error, variables) => {
      setAiCheckingKey(null);
      setAiCheckErrorKey(variables.questionKey);
    },
  });
  async function refreshReviewViews() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["manager-reviews", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["manager-overview", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["my-profiles"] }),
      queryClient.invalidateQueries({ queryKey: ["audit"] }),
      queryClient.invalidateQueries({ queryKey: ["hr-analytics"] }),
    ]);
  }
  const takeReviewMutation = useMutation({
    mutationFn: (profileId: number) => takeProfileForReview(selectedUserId!, profileId),
    onSuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» взят на проверку.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onError: () => setReviewActionProfileId(null),
  });
  const returnReviewMutation = useMutation({
    mutationFn: ({ profileId, reason }: { profileId: number; reason: string }) =>
      returnProfileForRevision(selectedUserId!, profileId, reason),
    onSuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» возвращен на доработку.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onError: () => setReviewActionProfileId(null),
  });
  const bulkReturnReviewMutation = useMutation({
    mutationFn: ({
      selection,
      reason,
    }: {
      selection: { profile_ids?: number[]; org_unit_id?: number };
      reason: string;
    }) => bulkReturnProfilesForRevision(selectedUserId!, selection, reason),
    onSuccess: async (result) => {
      setReviewMessage(`На доработку возвращено профилей: ${result.returned_count}.`);
      await refreshReviewViews();
    },
  });
  const verifyReviewMutation = useMutation({
    mutationFn: (profileId: number) => verifyProfileByManager(selectedUserId!, profileId),
    onSuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» подтвержден.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onError: () => setReviewActionProfileId(null),
  });
  async function refreshHrDecisionViews() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["hr-profile-reviews", selectedUserId] }),
      queryClient.invalidateQueries({ queryKey: ["campaigns", selectedUserId, dataScope] }),
      queryClient.invalidateQueries({ queryKey: ["audit", selectedUserId, dataScope] }),
      queryClient.invalidateQueries({ queryKey: ["hr-analytics", selectedUserId, dataScope] }),
      queryClient.invalidateQueries({ queryKey: ["manager-reviews"] }),
      queryClient.invalidateQueries({ queryKey: ["manager-overview"] }),
      queryClient.invalidateQueries({ queryKey: ["my-profiles"] }),
    ]);
  }
  const acceptHrMutation = useMutation({
    mutationFn: (profileId: number) => acceptProfileByHr(selectedUserId!, profileId, dataScope),
    onSuccess: async (profile) => {
      setHrDecisionMessage(`Профиль сотрудника «${profile.employee_name}» принят HR.`);
      setHrDecisionProfileId(null);
      await refreshHrDecisionViews();
    },
    onError: () => setHrDecisionProfileId(null),
  });
  const returnHrMutation = useMutation({
    mutationFn: ({ profileId, reason }: { profileId: number; reason: string }) =>
      returnProfileByHr(selectedUserId!, profileId, reason, dataScope),
    onSuccess: async (profile) => {
      setHrDecisionMessage(`Профиль сотрудника «${profile.employee_name}» возвращен руководителю.`);
      setHrDecisionProfileId(null);
      await refreshHrDecisionViews();
    },
    onError: () => setHrDecisionProfileId(null),
  });
  const bulkReturnHrMutation = useMutation({
    mutationFn: ({
      selection,
      reason,
    }: {
      selection: { profile_ids?: number[]; org_unit_id?: number };
      reason: string;
    }) => bulkReturnProfilesByHr(selectedUserId!, selection, reason, dataScope),
    onSuccess: async (result) => {
      setHrDecisionMessage(`Руководителям возвращено профилей: ${result.returned_count}.`);
      await refreshHrDecisionViews();
    },
  });

  function includeUnit(unit: OrgNode) {
    if (!activeCampaignId || !activeWaveId) return;
    setIncludingUnitId(unit.id);
    includeMutation.mutate({ campaignId: activeCampaignId, unitId: unit.id, waveId: activeWaveId });
  }

  function excludeUnit(unit: OrgNode) {
    if (!activeCampaignId || !activeWaveId) return;
    setExcludingUnitId(unit.id);
    excludeMutation.mutate({ campaignId: activeCampaignId, unitId: unit.id, waveId: activeWaveId });
  }

  function openEmployeeModal(position: Position) {
    addEmployeesMutation.reset();
    setEmployeeTarget(position);
  }

  async function savePersonalDraft(
    profileId: number,
    answers: Record<string, string>,
    aiUsage: ProfileAiUsagePayload,
  ) {
    saveDraftMutation.reset();
    return saveDraftMutation.mutateAsync({ profileId, answers, aiUsage });
  }

  async function submitPersonalProfile(
    profileId: number,
    answers: Record<string, string>,
    aiUsage: ProfileAiUsagePayload,
  ) {
    submitProfileMutation.reset();
    return submitProfileMutation.mutateAsync({ profileId, answers, aiUsage });
  }

  async function checkPersonalAnswer(
    profileId: number,
    questionKey: string,
    answers: Record<string, string>,
  ) {
    aiCheckMutation.reset();
    setAiCheckingKey(questionKey);
    setAiCheckErrorKey(null);
    return aiCheckMutation.mutateAsync({ profileId, questionKey, answers });
  }

  function takeReview(profileId: number) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    takeReviewMutation.reset();
    takeReviewMutation.mutate(profileId);
  }

  function returnReview(profileId: number, reason: string) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    returnReviewMutation.reset();
    returnReviewMutation.mutate({ profileId, reason });
  }

  function bulkReturnReviewSelected(profileIds: number[], reason: string) {
    setReviewMessage(null);
    bulkReturnReviewMutation.reset();
    bulkReturnReviewMutation.mutate({ selection: { profile_ids: profileIds }, reason });
  }

  function bulkReturnReviewUnit(orgUnitId: number, reason: string) {
    setReviewMessage(null);
    bulkReturnReviewMutation.reset();
    bulkReturnReviewMutation.mutate({ selection: { org_unit_id: orgUnitId }, reason });
  }

  function verifyReview(profileId: number) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    verifyReviewMutation.reset();
    verifyReviewMutation.mutate(profileId);
  }

  function acceptByHr(profileId: number) {
    setHrDecisionProfileId(profileId);
    setHrDecisionMessage(null);
    acceptHrMutation.reset();
    acceptHrMutation.mutate(profileId);
  }

  function returnByHr(profileId: number, reason: string) {
    setHrDecisionProfileId(profileId);
    setHrDecisionMessage(null);
    returnHrMutation.reset();
    returnHrMutation.mutate({ profileId, reason });
  }

  function bulkReturnByHrSelected(profileIds: number[], reason: string) {
    setHrDecisionMessage(null);
    bulkReturnHrMutation.reset();
    bulkReturnHrMutation.mutate({ selection: { profile_ids: profileIds }, reason });
  }

  function bulkReturnByHrUnit(orgUnitId: number, reason: string) {
    setHrDecisionMessage(null);
    bulkReturnHrMutation.reset();
    bulkReturnHrMutation.mutate({ selection: { org_unit_id: orgUnitId }, reason });
  }

  async function exportHrData(kind: "profiles" | "campaigns", format: "csv" | "json") {
    if (!selectedUserId) return;
    setExportError(null);
    try {
      await downloadHrExport(selectedUserId, kind, format);
      setOperationMessage(
        `Выгрузка ${kind === "profiles" ? "профилей" : "кампаний"} ${format.toUpperCase()} подготовлена.`,
      );
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Не удалось подготовить выгрузку.");
    }
  }

  async function exportPersonalProfile(profileId: number) {
    if (!selectedUserId) return;
    await downloadProfileTemplateExport(selectedUserId, profileId);
  }

  async function prepareIssuedCredentialsFile() {
    if (!selectedUserId || !activeCampaignId || !activeWaveId) {
      setExportError("Выберите кампанию и волну для формирования доступов.");
      return;
    }
    setPreparingCredentials(true);
    setExportError(null);
    setCredentialsFileBlob(null);
    try {
      const blob = await issueWaveCredentialsExport(selectedUserId, dataScope, activeCampaignId, activeWaveId);
      setCredentialsFileBlob(blob);
      setOperationMessage("Файл с доступами для новых участников сформирован.");
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Не удалось сформировать доступы.");
    } finally {
      setPreparingCredentials(false);
    }
  }

  function exportIssuedCredentials() {
    if (!credentialsFileBlob) return;
    const url = window.URL.createObjectURL(credentialsFileBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "credentials_new_participants.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  function assignWorkDocument(
    staffingLineId: number,
    documentType: "job_instruction" | "unit_regulation" | "professional_standard",
    documentId: number | null,
  ) {
    setAssigningDocumentKey(`${staffingLineId}:${documentType}`);
    documentLinkMutation.mutate({ staffingLineId, documentType, documentId });
  }

  function addWorkDocument(
    file: File,
    documentCode: string,
    documentType: "job_instruction" | "unit_regulation" | "professional_standard",
    title: string,
    version: string,
  ) {
    setDocumentDownloadError(null);
    documentUploadMutation.mutate({ file, documentCode, documentType, title, version });
  }

  function reviewWorkDocument(documentId: number, status: "good" | "warning", text: string) {
    setReviewingDocumentId(documentId);
    documentQualityMutation.mutate({ documentId, status, text });
  }

  async function downloadWorkDocument(documentId: number) {
    if (!selectedUserId) return;
    setDocumentDownloadError(null);
    try {
      await downloadWorkDocumentSource(selectedUserId, documentId);
    } catch (error) {
      setDocumentDownloadError(
        error instanceof Error ? error.message : "Не удалось скачать оригинал документа.",
      );
    }
  }

  function setAssignmentParticipation(assignmentId: number, included: boolean) {
    if (!activeCampaignId || !activeWaveId) return;
    setChangingAssignmentId(assignmentId);
    campaignAssignmentMutation.mutate({ assignmentId, included });
  }

  const activePersonalProfile = personalProfiles.data?.[0] ?? null;
  const authError =
    passwordLoginMutation.error?.message ??
    consumeMagicLinkMutation.error?.message ??
    logoutMutation.error?.message ??
    null;

  if (!authToken && !activeUser) {
    return (
      <LoginScreen
        authError={authError}
        authMessage={authMessage}
        isRequesting={passwordLoginMutation.isPending || consumeMagicLinkMutation.isPending}
        onLogin={(username, password) => {
          setAuthMessage(null);
          passwordLoginMutation.mutate({ username, password });
        }}
      />
    );
  }

  if (authToken && !activeUser) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-slate-700">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 text-sm shadow-sm">
          Проверяю рабочую сессию...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-5 px-6 py-5">
          <div className="flex items-center gap-4">
            <div className="rounded-xl bg-blue-950 px-3 py-2 font-bold text-white">МГТУ</div>
            <div>
              <h1 className="text-xl font-bold text-slate-950">Профилирование должностей</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
              <span className="font-semibold">
                {authMe.data
                  ? `${roleLabels[authMe.data.role]}: ${authMe.data.full_name}`
                  : "Проверяю рабочую сессию..."}
              </span>
              <button
                className="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm"
                disabled={logoutMutation.isPending}
                onClick={() => logoutMutation.mutate()}
                type="button"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-6 py-7">
        {(authMessage || authError) && (
          <div className="mb-4 rounded-2xl border border-blue-100 bg-white px-5 py-3 text-sm shadow-sm">
            {authMessage && <p className="text-blue-950">{authMessage}</p>}
            {authError && <p className="mt-1 text-red-700">{authError}</p>}
          </div>
        )}
        <section className="mb-6 rounded-2xl border border-blue-100 bg-white p-2 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <p className="px-3 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              Рабочая область
            </p>
            <nav className="flex flex-1 flex-wrap gap-2 text-sm">
              {navItems.map((item) => (
                <button
                  className={`rounded-xl px-4 py-2.5 text-left ${
                    activeSection === item.id
                      ? "bg-blue-950 font-semibold text-white shadow-sm"
                      : item.disabled
                        ? "cursor-not-allowed bg-slate-100 text-slate-400"
                        : "bg-slate-50 text-slate-700 hover:bg-blue-50 hover:text-blue-950"
                  }`}
                  disabled={item.disabled}
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  type="button"
                >
                  {item.label}
                  <span
                    className={`ml-2 text-xs font-normal ${
                      activeSection === item.id ? "text-blue-100" : "text-slate-400"
                    }`}
                  >
                    {item.note}
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </section>

        <section className="space-y-6">
          {dataScope === "work" && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
              <p className="font-semibold">Рабочий контур из штатного расписания</p>
              <p className="mt-1 text-amber-800">
                Подразделения и штатные строки загружены в рабочий контур. Сотрудники и руководители
                добавляются HR вручную через структуру; документы сопоставляются отдельно.
              </p>
            </div>
          )}

          {isHr && activeSection === "settings" && (
            <SettingsPanel
              configuration={aiSettings.data ?? null}
              error={aiSettings.error?.message ?? aiSettingsMutation.error?.message ?? null}
              questionnaire={questionnaireSettings.data ?? null}
              questionnaireError={
                questionnaireSettings.error?.message ?? questionnaireSettingsMutation.error?.message ?? null
              }
              isLoading={aiSettings.isLoading}
              isQuestionnaireLoading={questionnaireSettings.isLoading}
              isSaving={aiSettingsMutation.isPending}
              isQuestionnaireSaving={questionnaireSettingsMutation.isPending}
              onSave={(payload) => aiSettingsMutation.mutate(payload)}
              onSaveQuestionnaire={(payload) => questionnaireSettingsMutation.mutate(payload)}
            />
          )}

          {dataScope === "work" && isHr && activeSection === "structure" && (
            <>
              {workSummary.data && <Metrics profile={null} summary={workSummary.data} />}
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Рабочая структура
                  </p>
                  <h2 className="mt-1 text-2xl font-bold text-slate-950">
                    ШР по уровням на 15.05.2026
                  </h2>
                </div>
                <p className="rounded-full bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
                  {workSummary.data?.employees
                    ? `Загружено сотрудников: ${workSummary.data.employees}`
                    : "Персональные данные не загружены"}
                </p>
              </div>
              {workTree.isLoading && <p className="text-slate-500">Загружаю рабочую структуру...</p>}
              {workTree.error && <p className="text-red-700">Не удалось загрузить рабочую структуру.</p>}
              {workTree.data && (
                <OrganizationTreePanel
                  activeCampaign={activeCampaignForTree}
                  canAddEmployees={Boolean(!activeCampaignForTree || activeWave?.can_edit)}
                  canManage={Boolean(activeCampaignForTree && activeWave?.can_edit)}
                  excludingUnitId={excludingUnitId}
                  includingUnitId={includingUnitId}
                  nodes={workTree.data.nodes}
                  onAdd={openEmployeeModal}
                  onExclude={excludeUnit}
                  onInclude={includeUnit}
                  onSetAssignment={setAssignmentParticipation}
                />
              )}
            </>
          )}

          {dataScope === "demo" && isHr && activeSection === "structure" && (
            <DemoResetPanel
              error={demoResetMutation.error?.message ?? null}
              isResetting={demoResetMutation.isPending}
              onReset={() => demoResetMutation.mutate()}
              result={demoResetMutation.data ?? null}
            />
          )}

          {dataScope === "work" && isHr && activeSection === "documents" && (
            <DocumentPanel
              assigningKey={assigningDocumentKey}
              canEdit
              error={
                documents.error?.message ??
                documentLinkMutation.error?.message ??
                documentUploadMutation.error?.message ??
                documentQualityMutation.error?.message ??
                documentDownloadError ??
                null
              }
              isLoading={documents.isLoading}
              isUploading={documentUploadMutation.isPending}
              onDownloadSource={(documentId) => void downloadWorkDocument(documentId)}
              onReviewQuality={reviewWorkDocument}
              onSetLink={assignWorkDocument}
              onUpload={addWorkDocument}
              registry={documents.data ?? null}
              reviewingDocumentId={reviewingDocumentId}
              tree={workTree.data?.nodes ?? []}
            />
          )}

          {dataScope === "work" && isHr && activeSection === "campaigns" && (
            <>
              <CampaignPanel
                scope="work"
                activeCampaignId={activeCampaignId}
                activeWaveId={activeWaveId}
                campaigns={campaigns.data ?? []}
                error={
                  createCampaignMutation.error?.message ??
                  createWaveMutation.error?.message ??
                  launchWaveMutation.error?.message ??
                  editWaveMutation.error?.message ??
                  includeMutation.error?.message ??
                  excludeMutation.error?.message ??
                  campaignAssignmentMutation.error?.message ??
                  exportError ??
                  null
                }
                events={audit.data ?? []}
                credentialsFileReady={Boolean(credentialsFileBlob)}
                isPreparingCredentials={preparingCredentials}
                isCreating={createCampaignMutation.isPending}
                isCreatingWave={createWaveMutation.isPending}
                isLaunchingWave={launchWaveMutation.isPending}
                isEditingWave={editWaveMutation.isPending}
                message={operationMessage}
                onActiveChange={(id) => {
                  setActiveCampaignId(id);
                  setActiveWaveId(null);
                }}
                onCreate={(name, dueAt) => createCampaignMutation.mutate({ name, dueAt })}
                onExport={exportHrData}
                onPrepareCredentialsFile={prepareIssuedCredentialsFile}
                onDownloadCredentials={exportIssuedCredentials}
                onCreateWave={(campaignId, name, dueAt) =>
                  createWaveMutation.mutate({ campaignId, name, dueAt })
                }
                onLaunchWave={(campaignId, waveId) =>
                  launchWaveMutation.mutate({ campaignId, waveId })
                }
                onEditWave={(campaignId, waveId) =>
                  editWaveMutation.mutate({ campaignId, waveId })
                }
                onWaveChange={setActiveWaveId}
              />
              {workTree.data && (
                <OrganizationTreePanel
                  activeCampaign={activeCampaignForTree}
                  canManage={Boolean(activeCampaignForTree && activeWave?.can_edit)}
                  canAddEmployees={false}
                  changingAssignmentId={changingAssignmentId}
                  excludingUnitId={excludingUnitId}
                  includingUnitId={includingUnitId}
                  nodes={workTree.data.nodes}
                  onAdd={openEmployeeModal}
                  onExclude={excludeUnit}
                  onInclude={includeUnit}
                  onSetAssignment={setAssignmentParticipation}
                />
              )}
            </>
          )}

          {dataScope === "work" && isHr && activeSection === "analytics" && (
            <HrAnalyticsPanel
              analytics={hrAnalytics.data ?? null}
              error={hrAnalytics.error?.message ?? null}
              isLoading={hrAnalytics.isLoading}
            />
          )}

          {dataScope === "work" && isHr && activeSection === "hr-reviews" && (
            <HrReviewPanel
              activeProfileId={hrDecisionProfileId}
              bulkActive={bulkReturnHrMutation.isPending}
              error={acceptHrMutation.error?.message ?? returnHrMutation.error?.message ?? bulkReturnHrMutation.error?.message ?? null}
              message={hrDecisionMessage}
              onAccept={acceptByHr}
              onBulkReturnSelected={bulkReturnByHrSelected}
              onBulkReturnUnit={bulkReturnByHrUnit}
              onReturn={returnByHr}
              reviews={hrReviews.data ?? []}
            />
          )}

          {dataScope === "work" && !isHr && activeSection === "structure" && activeUser?.role !== "employee" && (
            <>
              {workSummary.data && <Metrics profile={activePersonalProfile} summary={workSummary.data} />}
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Видимость роли
                  </p>
                  <h2 className="mt-1 text-2xl font-bold text-slate-950">
                    {activeUser ? roleLabels[activeUser.role] : "Загрузка"}:{" "}
                    {activeUser?.full_name}
                  </h2>
                </div>
                <p className="rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900">
                  Структура в разрешённой зоне
                </p>
              </div>
              {workTree.isLoading && <p className="text-slate-500">Загружаю структуру...</p>}
              {workTree.error && <p className="text-red-700">Не удалось загрузить структуру.</p>}
              {workTree.data && (
                <OrganizationTreePanel
                  activeCampaign={null}
                  canManage={false}
                  excludingUnitId={null}
                  includingUnitId={null}
                  nodes={workTree.data.nodes}
                  onAdd={openEmployeeModal}
                  onExclude={excludeUnit}
                  onInclude={includeUnit}
                  onSetAssignment={setAssignmentParticipation}
                />
              )}
            </>
          )}

          {dataScope === "work" && activeUser?.role !== "employee" && activeSection !== "structure" && activeSection !== "documents" && activeSection !== "campaigns" && activeSection !== "analytics" && activeSection !== "hr-reviews" && activeSection !== "settings" && activeSection !== "profile" && activeSection !== "manager-overview" && activeSection !== "manager-reviews" && (
            <WorkContourPlaceholder />
          )}

          {activeSection === "profile" && (
            <>
              {summary.data && <Metrics profile={activePersonalProfile} summary={summary.data} />}
              {activePersonalProfile ? (
                <ProfileWorkspace
                  ai={health.data?.ai}
                  aiCheckError={
                    aiCheckErrorKey ? aiCheckMutation.error?.message ?? null : null
                  }
                  aiCheckResults={aiCheckResults}
                  aiAnswerSnapshots={aiAnswerSnapshots}
                  aiCheckingKey={aiCheckingKey}
                  error={saveDraftMutation.error?.message ?? submitProfileMutation.error?.message ?? null}
                  isSaving={saveDraftMutation.isPending}
                  isSubmitting={submitProfileMutation.isPending}
                  onAiCheck={checkPersonalAnswer}
                  key={activePersonalProfile.id}
                  onSave={savePersonalDraft}
                  onSubmit={submitPersonalProfile}
                  onExport={exportPersonalProfile}
                  profile={activePersonalProfile}
                />
              ) : (
                <div className="rounded-2xl border border-blue-100 bg-white p-5 text-sm text-slate-600 shadow-sm">
                  Анкета появится после включения вашего назначения в активную кампанию профилирования.
                </div>
              )}
            </>
          )}

          {dataScope === "demo" && activeSection === "structure" && selectedUser?.role !== "employee" && (
            <>
              {summary.data && <Metrics profile={activePersonalProfile} summary={summary.data} />}
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Видимость роли
                  </p>
                  <h2 className="mt-1 text-2xl font-bold text-slate-950">
                    {selectedUser ? roleLabels[selectedUser.role] : "Загрузка"}:{" "}
                    {selectedUser?.full_name}
                  </h2>
                </div>
                <p className="rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900">
                  Структура в разрешённой зоне
                </p>
              </div>
              {tree.isLoading && <p className="text-slate-500">Загружаю структуру...</p>}
              {tree.error && <p className="text-red-700">Не удалось загрузить структуру.</p>}
              {tree.data && (
                <OrganizationTreePanel
                  activeCampaign={activeCampaignForTree}
                  canManage={Boolean(isHr)}
                  changingAssignmentId={changingAssignmentId}
                  excludingUnitId={excludingUnitId}
                  includingUnitId={includingUnitId}
                  nodes={tree.data.nodes}
                  onAdd={openEmployeeModal}
                  onExclude={excludeUnit}
                  onInclude={includeUnit}
                  onSetAssignment={setAssignmentParticipation}
                />
              )}
            </>
          )}

          {dataScope === "demo" && isHr && activeSection === "campaigns" && (
            <>
              <CampaignPanel
                scope="demo"
                activeCampaignId={activeCampaignId}
                activeWaveId={activeWaveId}
                campaigns={campaigns.data ?? []}
                error={
                  createCampaignMutation.error?.message ??
                  createWaveMutation.error?.message ??
                  launchWaveMutation.error?.message ??
                  editWaveMutation.error?.message ??
                  includeMutation.error?.message ??
                  excludeMutation.error?.message ??
                  campaignAssignmentMutation.error?.message ??
                  exportError ??
                  null
                }
                events={audit.data ?? []}
                credentialsFileReady={Boolean(credentialsFileBlob)}
                isPreparingCredentials={preparingCredentials}
                isCreating={createCampaignMutation.isPending}
                isCreatingWave={createWaveMutation.isPending}
                isLaunchingWave={launchWaveMutation.isPending}
                isEditingWave={editWaveMutation.isPending}
                message={operationMessage}
                onActiveChange={(id) => {
                  setActiveCampaignId(id);
                  setActiveWaveId(null);
                }}
                onCreate={(name, dueAt) => createCampaignMutation.mutate({ name, dueAt })}
                onExport={exportHrData}
                onPrepareCredentialsFile={prepareIssuedCredentialsFile}
                onDownloadCredentials={exportIssuedCredentials}
                onCreateWave={(campaignId, name, dueAt) =>
                  createWaveMutation.mutate({ campaignId, name, dueAt })
                }
                onLaunchWave={(campaignId, waveId) =>
                  launchWaveMutation.mutate({ campaignId, waveId })
                }
                onEditWave={(campaignId, waveId) =>
                  editWaveMutation.mutate({ campaignId, waveId })
                }
                onWaveChange={setActiveWaveId}
              />
              {tree.data && (
                <OrganizationTreePanel
                  activeCampaign={activeCampaignForTree}
                  canManage={Boolean(activeCampaignForTree && activeWave?.can_edit)}
                  changingAssignmentId={changingAssignmentId}
                  excludingUnitId={excludingUnitId}
                  includingUnitId={includingUnitId}
                  nodes={tree.data.nodes}
                  onAdd={openEmployeeModal}
                  onExclude={excludeUnit}
                  onInclude={includeUnit}
                  onSetAssignment={setAssignmentParticipation}
                />
              )}
            </>
          )}

          {dataScope === "demo" && isHr && activeSection === "hr-reviews" && (
            <HrReviewPanel
              activeProfileId={hrDecisionProfileId}
              bulkActive={bulkReturnHrMutation.isPending}
              error={acceptHrMutation.error?.message ?? returnHrMutation.error?.message ?? bulkReturnHrMutation.error?.message ?? null}
              message={hrDecisionMessage}
              onAccept={acceptByHr}
              onBulkReturnSelected={bulkReturnByHrSelected}
              onBulkReturnUnit={bulkReturnByHrUnit}
              onReturn={returnByHr}
              reviews={hrReviews.data ?? []}
            />
          )}

          {dataScope === "demo" && isHr && activeSection === "documents" && (
            <DocumentPanel
              error={documents.error?.message ?? null}
              isLoading={documents.isLoading}
              registry={documents.data ?? null}
              tree={tree.data?.nodes ?? []}
            />
          )}

          {dataScope === "demo" && isHr && activeSection === "analytics" && (
            <HrAnalyticsPanel
              analytics={hrAnalytics.data ?? null}
              error={hrAnalytics.error?.message ?? null}
              isLoading={hrAnalytics.isLoading}
            />
          )}

          {isManager && activeSection === "manager-overview" && (
            <ManagerOverviewPanel
              error={managerOverview.error?.message ?? null}
              isLoading={managerOverview.isLoading}
              overview={managerOverview.data ?? null}
            />
          )}

          {isManager && activeSection === "manager-reviews" && (
            <ManagerReviewPanel
              activeProfileId={reviewActionProfileId}
              bulkActive={bulkReturnReviewMutation.isPending}
              error={
                takeReviewMutation.error?.message ??
                returnReviewMutation.error?.message ??
                bulkReturnReviewMutation.error?.message ??
                verifyReviewMutation.error?.message ??
                null
              }
              message={reviewMessage}
              onBulkReturnSelected={bulkReturnReviewSelected}
              onBulkReturnUnit={bulkReturnReviewUnit}
              onReturn={returnReview}
              onTake={takeReview}
              onVerify={verifyReview}
              reviews={managerReviews.data ?? []}
            />
          )}

          {isManager && activeSection === "documents" && (
            <DocumentPanel
              error={managerDocuments.error?.message ?? null}
              isLoading={managerDocuments.isLoading}
              registry={managerDocuments.data ?? null}
              tree={tree.data?.nodes ?? []}
              viewer="manager"
            />
          )}

        </section>
      </div>
      {isHr && (
        <EmployeeModal
          allowRoleSelection={dataScope === "work"}
          error={addEmployeesMutation.error?.message ?? null}
          isSaving={addEmployeesMutation.isPending}
          managers={dataScope === "work" ? workManagers.data ?? [] : managers.data ?? []}
          onClose={() => setEmployeeTarget(null)}
          onSave={(rows) => addEmployeesMutation.mutate(rows)}
          target={employeeTarget}
        />
      )}
    </main>
  );
}
