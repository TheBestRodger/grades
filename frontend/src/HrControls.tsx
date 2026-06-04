import { type FormEvent, useEffect, useState } from "react";

import type {
  AuditEvent,
  Campaign,
  DemoResetResult,
  ManagerOption,
  NewEmployee,
  Position,
} from "./types";

interface EmployeeModalProps {
  target: Position | null;
  managers: ManagerOption[];
  allowRoleSelection?: boolean;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (rows: NewEmployee[]) => void;
}

function emptyRow(managerAssignmentId: number | null): NewEmployee {
  return {
    full_name: "",
    email: "",
    fte: 1,
    system_role: "employee",
    manager_assignment_id: managerAssignmentId,
  };
}

export function EmployeeModal({
  target,
  managers,
  allowRoleSelection = false,
  isSaving,
  error,
  onClose,
  onSave,
}: EmployeeModalProps) {
  const defaultManager =
    managers.find((manager) => manager.position_title === "Начальник отдела сопровождения процессов")
      ?.assignment_id ??
    managers[0]?.assignment_id ??
    null;
  const [count, setCount] = useState(1);
  const [managerId, setManagerId] = useState<number | null>(defaultManager);
  const [rows, setRows] = useState<NewEmployee[]>([emptyRow(defaultManager)]);
  const availableSlots =
    target && (target.vacancy_fte ?? 0) > 0
      ? Math.floor(target.vacancy_fte ?? 1)
      : Math.max(1, Math.floor(target?.approved_fte ?? 1));

  useEffect(() => {
    setCount(1);
    setManagerId(defaultManager);
    setRows([emptyRow(defaultManager)]);
  }, [target?.id, defaultManager]);

  if (!target) return null;

  function resize(next: number) {
    const safeCount = Math.max(1, Math.min(next, availableSlots));
    setCount(safeCount);
    setRows((existing) =>
      Array.from({ length: safeCount }, (_, index) => existing[index] ?? emptyRow(managerId)),
    );
  }

  function chooseManager(next: number | null) {
    setManagerId(next);
    setRows((existing) =>
      existing.map((row) => ({
        ...row,
        manager_assignment_id: row.system_role === "manager" ? null : next,
      })),
    );
  }

  function updateRow(index: number, patch: Partial<NewEmployee>) {
    setRows((existing) =>
      existing.map((row, current) => (current === index ? { ...row, ...patch } : row)),
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave(rows);
  }

  const rowsAreValid = rows.every(
    (row) => row.full_name.trim() && row.email.trim() && (row.system_role === "manager" || row.manager_assignment_id),
  );

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-slate-950/40 px-4">
      <form
        className="max-h-[92vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl"
        onSubmit={submit}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              HR: добавление сотрудников
            </p>
            <h3 className="mt-1 text-xl font-bold text-slate-950">{target.title}</h3>
            <p className="mt-1 text-sm text-slate-500">
              Доступно ставок: {target.vacancy_fte}. Все новые записи сохраняются в выбранном контуре.
            </p>
          </div>
          <button className="rounded-xl px-3 py-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>

        <div className="mt-6 grid gap-4 rounded-2xl bg-slate-50 p-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">
            Сколько людей добавить
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              max={availableSlots}
              min={1}
              onChange={(event) => resize(Number(event.target.value))}
              type="number"
              value={count}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Непосредственный руководитель
            <select
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              onChange={(event) => chooseManager(event.target.value ? Number(event.target.value) : null)}
              value={managerId ?? ""}
            >
              <option value="">Не выбран</option>
              {managers.map((manager) => (
                <option key={manager.assignment_id} value={manager.assignment_id}>
                  {manager.employee_name} / {manager.position_title}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 space-y-3">
          {rows.map((row, index) => (
            <div
              className={`grid gap-3 rounded-xl border border-slate-200 p-3 ${
                allowRoleSelection ? "md:grid-cols-[1fr_1fr_110px_150px]" : "md:grid-cols-[1fr_1fr_110px]"
              }`}
              key={index}
            >
              <input
                aria-label={`ФИО сотрудника ${index + 1}`}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                onChange={(event) => updateRow(index, { full_name: event.target.value })}
                placeholder="ФИО"
                required
                value={row.full_name}
              />
              <input
                aria-label={`Email сотрудника ${index + 1}`}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                onChange={(event) => updateRow(index, { email: event.target.value })}
                placeholder="name@example.local"
                required
                type="email"
                value={row.email}
              />
              <input
                aria-label={`Ставка сотрудника ${index + 1}`}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                min={0.1}
                onChange={(event) => updateRow(index, { fte: Number(event.target.value) })}
                step={0.1}
                type="number"
                value={row.fte}
              />
              {allowRoleSelection && (
                <select
                  aria-label={`Роль сотрудника ${index + 1}`}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                  onChange={(event) =>
                    updateRow(index, {
                      system_role: event.target.value as "employee" | "manager",
                      manager_assignment_id:
                        event.target.value === "manager" ? null : row.manager_assignment_id ?? managerId,
                    })
                  }
                  value={row.system_role}
                >
                  <option value="employee">Сотрудник</option>
                  <option value="manager">Руководитель</option>
                </select>
              )}
            </div>
          ))}
        </div>

        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium" onClick={onClose} type="button">
            Отмена
          </button>
          <button
            className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            disabled={isSaving || !rowsAreValid}
            type="submit"
          >
            {isSaving ? "Сохраняю..." : `Добавить ${count} сотрудника(ов)`}
          </button>
        </div>
      </form>
    </div>
  );
}

interface DemoResetPanelProps {
  isResetting: boolean;
  error: string | null;
  result: DemoResetResult | null;
  onReset: () => void;
}

export function DemoResetPanel({ isResetting, error, result, onReset }: DemoResetPanelProps) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <section className="rounded-2xl border border-amber-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
        HR: сброс контура
      </p>
      <h3 className="mt-2 text-lg font-bold text-slate-950">Сбросить текущий контур</h3>
      <p className="mt-1 text-sm text-slate-600">
        Будут заново созданы пользователи, кампания, профили и документы выбранного контура.
        Рабочий контур, импортированное ШР, рабочие сотрудники и рабочие документы не удаляются.
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm text-slate-700">
        <input
          checked={confirmed}
          className="mt-1"
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        <span>Понимаю, что текущие черновики, кампании и аудит выбранного контура будут пересозданы.</span>
      </label>
      <button
        className="mt-4 rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        disabled={!confirmed || isResetting}
        onClick={onReset}
        type="button"
      >
        {isResetting ? "Сбрасываю..." : "Сбросить контур"}
      </button>
      {result && (
        <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Контур пересоздан. Рабочий контур {result.work_unchanged ? "не изменился" : "требует проверки"}.
        </p>
      )}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
    </section>
  );
}

interface CampaignPanelProps {
  scope: "demo" | "work";
  campaigns: Campaign[];
  activeCampaignId: number | null;
  activeWaveId: number | null;
  events: AuditEvent[];
  message: string | null;
  error: string | null;
  isCreating: boolean;
  isCreatingWave: boolean;
  isLaunchingWave: boolean;
  isEditingWave: boolean;
  credentialsFileReady: boolean;
  isPreparingCredentials: boolean;
  onActiveChange: (id: number) => void;
  onWaveChange: (id: number) => void;
  onCreate: (name: string, dueAt: string | null) => void;
  onCreateWave: (campaignId: number, name: string, dueAt: string | null) => void;
  onLaunchWave: (campaignId: number, waveId: number) => void;
  onEditWave: (campaignId: number, waveId: number) => void;
  onExport: (kind: "profiles" | "campaigns", format: "csv" | "json") => void;
  onPrepareCredentialsFile: () => void;
  onDownloadCredentials: () => void;
}

const auditLabels: Record<string, string> = {
  "campaign.created": "Создана кампания",
  "campaign.wave_created": "Создана волна кампании",
  "campaign.wave_launched": "Волна запущена",
  "campaign.wave_editing_started": "Волна взята в редакцию",
  "campaign.branch_included": "В кампанию включена ветка",
  "campaign.branch_excluded": "Ветка выключена из кампании",
  "document.link_updated": "Обновлена связь документа",
  "employees.work_imported": "Импортированы рабочие сотрудники",
  "staffing_line.work_created": "Создана рабочая штатная строка",
  "employees.bulk_added": "Добавлены сотрудники",
  "campaign.assignments_included": "Включены отдельные назначения",
  "campaign.assignments_excluded": "Выключены отдельные назначения",
  "profile.draft_saved": "Сотрудник сохранил черновик",
  "profile.submitted": "Сотрудник отправил профиль",
  "profile.review_started": "Руководитель взял профиль на проверку",
  "profile.returned_for_revision": "Профиль возвращен на доработку",
  "profile.manager_verified": "Профиль подтвержден руководителем",
  "profile.returned_by_hr": "HR вернул профиль руководителю",
  "profile.hr_accepted": "HR принял профиль",
  "profiles.bulk_returned_for_revision": "Руководитель массово вернул профили",
  "profiles.bulk_returned_by_hr": "HR массово вернул профили",
  "demo.reset_completed": "Контур сброшен",
};

export function CampaignPanel({
  scope,
  campaigns,
  activeCampaignId,
  activeWaveId,
  events,
  message,
  error,
  isCreating,
  isCreatingWave,
  isLaunchingWave,
  isEditingWave,
  credentialsFileReady,
  isPreparingCredentials,
  onActiveChange,
  onWaveChange,
  onCreate,
  onCreateWave,
  onLaunchWave,
  onEditWave,
  onExport,
  onPrepareCredentialsFile,
  onDownloadCredentials,
}: CampaignPanelProps) {
  const isWork = scope === "work";
  const [name, setName] = useState(isWork ? "Рабочая кампания профилирования" : "Кампания профилирования");
  const [dueAt, setDueAt] = useState("");
  const [waveName, setWaveName] = useState("");
  const [waveDueAt, setWaveDueAt] = useState("");
  const [confirmWaveAction, setConfirmWaveAction] = useState<"launch" | "edit" | null>(null);
  const active = campaigns.find((campaign) => campaign.id === activeCampaignId);
  const activeWave =
    active?.waves.find((wave) => wave.id === activeWaveId) ??
    active?.waves.find((wave) => wave.id === active?.active_wave_id) ??
    active?.waves[0] ??
    null;
  const statusLabels: Record<string, string> = {
    not_started: "Не начали",
    draft: "Черновики",
    submitted: "Сдали",
    under_review: "На проверке",
    returned_for_revision: "На доработке",
    manager_verified: "Ждут HR",
    returned_by_hr: "Возвращены HR",
    hr_accepted: "Приняты HR",
  };
  const waveStatusTone: Record<string, string> = {
    draft: "bg-slate-100 text-slate-700",
    active: "bg-emerald-50 text-emerald-800",
    editing: "bg-amber-50 text-amber-800",
  };
  const hasWaveParticipants = Boolean(activeWave && activeWave.participants_expected > 0);
  const confirmTitle = confirmWaveAction === "launch" ? "Запустить волну?" : "Взять волну в редакцию?";
  const confirmText =
    confirmWaveAction === "launch"
      ? `Будет запущена волна «${activeWave?.name ?? ""}». Проверьте выбранные подразделения и участников перед запуском.`
      : `Волна «${activeWave?.name ?? ""}» перейдет в режим редактирования. После этого состав участников можно будет изменить.`;
  const isConfirmingWaveAction = confirmWaveAction === "launch" ? isLaunchingWave : isEditingWave;

  useEffect(() => {
    setName(isWork ? "Рабочая кампания профилирования" : "Кампания профилирования");
  }, [isWork]);

  function submit(event: FormEvent) {
    event.preventDefault();
    onCreate(name, dueAt || null);
  }

  useEffect(() => {
    if (!active) {
      setWaveName("");
      return;
    }
    setWaveName(`Волна ${active.waves.length + 1}`);
    setWaveDueAt("");
  }, [active?.id, active?.waves.length]);

  function submitWave(event: FormEvent) {
    event.preventDefault();
    if (!active) return;
    onCreateWave(active.id, waveName, waveDueAt || null);
  }

  function launchWave() {
    if (!active || !activeWave) return;
    setConfirmWaveAction("launch");
  }

  function editWave() {
    if (!active || !activeWave) return;
    setConfirmWaveAction("edit");
  }

  function confirmWaveChange() {
    if (!active || !activeWave || !confirmWaveAction) return;
    if (confirmWaveAction === "launch") {
      onLaunchWave(active.id, activeWave.id);
    } else {
      onEditWave(active.id, activeWave.id);
    }
    setConfirmWaveAction(null);
  }

  function formatTimestamp(value: string | null): string {
    if (!value) return "";
    const normalized = value.endsWith("Z") ? value : `${value}Z`;
    return new Date(normalized).toLocaleString("ru-RU");
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
      <div className="space-y-5">
        <form className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={submit}>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
          HR: {isWork ? "рабочая кампания" : "кампания"}
        </p>
        <h3 className="mt-2 text-lg font-bold text-slate-950">Назначить профилирование</h3>
        <p className="mt-1 text-sm text-slate-500">
          Кампания - общий цикл профилирования. Волны внутри кампании позволяют проходить
          подразделения этапами.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_155px]">
          <input
            className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
            onChange={(event) => setName(event.target.value)}
            placeholder="Название кампании"
            required
            value={name}
          />
          <input
            className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
            onChange={(event) => setDueAt(event.target.value)}
            type="date"
            value={dueAt}
          />
        </div>
        <button
          className="mt-4 rounded-xl bg-blue-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          disabled={isCreating}
          type="submit"
        >
          {isCreating ? "Создаю..." : "Создать кампанию"}
        </button>

        {campaigns.length > 0 && (
          <div className="mt-5 border-t border-slate-100 pt-4">
            <label className="text-sm font-medium text-slate-700">
              Активная кампания
              <select
                className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                onChange={(event) => onActiveChange(Number(event.target.value))}
                value={activeCampaignId ?? ""}
              >
                {campaigns.map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name} / {isWork
                      ? `подразделений: ${campaign.selected_units_count}`
                      : `всего ожидаем: ${campaign.total_participants_expected}`}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {active && (
          <div className="mt-3 rounded-xl bg-blue-50 px-3 py-3 text-sm text-blue-900">
            <p>
              Выберите волну ниже, затем ветку в структуре. Включение и выключение применяются
              к выбранной волне{isWork ? ": сохраняется охват ШР и включаются уже загруженные назначения." : "."}
            </p>
            <label className="mt-3 block text-sm font-medium text-blue-950">
              Активная волна
              <select
                className="mt-2 block w-full rounded-xl border border-blue-100 bg-white px-3 py-2 text-sm"
                onChange={(event) => onWaveChange(Number(event.target.value))}
                value={activeWave?.id ?? ""}
              >
                {active.waves.map((wave) => (
                  <option key={wave.id} value={wave.id}>
                    {wave.name} / {wave.status_label} / {isWork
                      ? `подразделений: ${wave.selected_units_count}`
                      : `ожидаем: ${wave.participants_expected}`}
                  </option>
                ))}
              </select>
            </label>
            {activeWave && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${waveStatusTone[activeWave.status] ?? "bg-slate-100 text-slate-700"}`}>
                  {activeWave.status_label}
                </span>
                <button
                  className="rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={
                    !activeWave.can_launch ||
                    activeWave.participants_expected < 1 ||
                    (isWork && activeWave.selected_units_count < 1) ||
                    isLaunchingWave
                  }
                  onClick={launchWave}
                  type="button"
                >
                  {isLaunchingWave ? "Запускаю..." : "Запустить волну"}
                </button>
                <button
                  className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={activeWave.status !== "active" || isEditingWave}
                  onClick={editWave}
                  type="button"
                >
                  {isEditingWave ? "Открываю редакцию..." : "Взять в редакцию"}
                </button>
                {!activeWave.can_edit && (
                  <span className="text-xs text-slate-500">
                    Состав запущенной волны заблокирован для изменений.
                  </span>
                )}
              </div>
            )}
            {activeWave && !isWork && (
              <p className="mt-3">
                В волне «{activeWave.name}» ожидаем заполнение:{" "}
                <strong>{activeWave.participants_expected}</strong> сотрудника(ов).
              </p>
            )}
            {activeWave && isWork && (
              <div className="mt-3 grid gap-2 sm:grid-cols-4">
                <div className="rounded-lg bg-white px-3 py-2">
                  <p className="text-xs text-blue-700">Подразделения</p>
                  <p className="font-semibold">{activeWave.selected_units_count}</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-2">
                  <p className="text-xs text-blue-700">Штатные строки</p>
                  <p className="font-semibold">{activeWave.selected_staffing_lines}</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-2">
                  <p className="text-xs text-blue-700">Ставки по ШР</p>
                  <p className="font-semibold">{activeWave.selected_approved_fte.toLocaleString("ru-RU")}</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-2">
                  <p className="text-xs text-blue-700">Участники</p>
                  <p className="font-semibold">{activeWave.participants_expected}</p>
                </div>
              </div>
            )}
            {!isWork && <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(activeWave?.status_counts ?? {}).map(([status, count]) => (
                <span
                  className={`rounded-full px-2.5 py-1 text-xs ${
                    status === "hr_accepted" || status === "manager_verified"
                      ? "bg-emerald-50 text-emerald-800"
                      : status === "not_started" || status === "returned_by_hr"
                        ? "bg-red-50 text-red-800"
                        : status === "draft" || status === "returned_for_revision"
                          ? "bg-amber-50 text-amber-800"
                          : "bg-white text-blue-900"
                  }`}
                  key={status}
                >
                  {statusLabels[status] ?? status}: <strong>{count}</strong>
                </span>
              ))}
            </div>}
            <div className="mt-4 rounded-xl border border-emerald-100 bg-white px-3 py-3 text-sm text-emerald-950">
              <p className="font-semibold">Доступы участников</p>
              <p className="mt-1 text-xs text-emerald-800">
                Участников в выбранной волне: <strong>{activeWave?.participants_expected ?? 0}</strong>.
                Файл формируется для новых участников.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 disabled:opacity-50"
                  disabled={!active || !activeWave || !hasWaveParticipants || isPreparingCredentials}
                  onClick={onPrepareCredentialsFile}
                  type="button"
                >
                  {isPreparingCredentials ? "Формирую..." : "Сформировать доступы для новых участников"}
                </button>
                {credentialsFileReady && (
                  <button
                    className="rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white"
                    onClick={onDownloadCredentials}
                    type="button"
                  >
                    Скачать XLSX
                  </button>
                )}
              </div>
              {!hasWaveParticipants && (
                <p className="mt-2 text-xs text-emerald-800">
                  Сначала добавьте участников в выбранную волну.
                </p>
              )}
            </div>
          </div>
        )}
        {message && <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>}
        {error && <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        </form>

        {!isWork && <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Выгрузки
          </p>
          <h3 className="mt-2 text-lg font-bold text-slate-950">Экспорт для HR</h3>
          <p className="mt-1 text-sm text-slate-500">
            Быстрый срез данных: профили с последней версией и сводка кампаний по волнам.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-900"
              onClick={() => onExport("profiles", "csv")}
              type="button"
            >
              Профили CSV
            </button>
            <button
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"
              onClick={() => onExport("profiles", "json")}
              type="button"
            >
              Профили JSON
            </button>
            <button
              className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-900"
              onClick={() => onExport("campaigns", "csv")}
              type="button"
            >
              Кампании CSV
            </button>
            <button
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"
              onClick={() => onExport("campaigns", "json")}
              type="button"
            >
              Кампании JSON
            </button>
          </div>
        </div>}

        {active && (
          <form className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={submitWave}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Волны кампании
            </p>
            <h3 className="mt-2 text-lg font-bold text-slate-950">Создать следующую волну</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_155px]">
              <input
                className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
                onChange={(event) => setWaveName(event.target.value)}
                placeholder="Название волны"
                required
                value={waveName}
              />
              <input
                className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
                onChange={(event) => setWaveDueAt(event.target.value)}
                type="date"
                value={waveDueAt}
              />
            </div>
            <button
              className="mt-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-900 disabled:opacity-50"
              disabled={isCreatingWave}
              type="submit"
            >
              {isCreatingWave ? "Создаю..." : "Создать волну"}
            </button>
          </form>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Аудит действий</p>
        <h3 className="mt-2 text-lg font-bold text-slate-950">Последние операции процесса</h3>
        <div className="mt-4 space-y-3">
          {events.length === 0 && <p className="text-sm text-slate-500">Операций пока нет.</p>}
          {events.slice(0, 5).map((event) => (
            <div className="rounded-xl bg-slate-50 px-3 py-2 text-sm" key={event.id}>
              <p className="font-medium text-slate-800">{auditLabels[event.action] ?? event.action}</p>
              <p className="text-xs text-slate-500">{formatTimestamp(event.created_at)}</p>
            </div>
          ))}
        </div>
      </div>
      {confirmWaveAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              Подтверждение действия
            </p>
            <h3 className="mt-3 text-2xl font-bold text-slate-950">{confirmTitle}</h3>
            <p className="mt-3 text-base leading-7 text-slate-600">{confirmText}</p>
            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700"
                onClick={() => setConfirmWaveAction(null)}
                type="button"
              >
                Отмена
              </button>
              <button
                className="rounded-xl bg-blue-900 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
                disabled={isConfirmingWaveAction}
                onClick={confirmWaveChange}
                type="button"
              >
                {confirmWaveAction === "launch" ? "Запустить волну" : "Взять в редакцию"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
