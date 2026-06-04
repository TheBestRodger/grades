import { useState } from "react";

import type { ManagerOverview, ManagerProfileSignal } from "./types";

interface ManagerOverviewPanelProps {
  overview: ManagerOverview | null;
  isLoading: boolean;
  error: string | null;
}

const riskClasses: Record<ManagerProfileSignal["risk_level"], string> = {
  normal: "border-emerald-200 bg-emerald-50 text-emerald-900",
  attention: "border-amber-200 bg-amber-50 text-amber-900",
  critical: "border-red-200 bg-red-50 text-red-900",
};

const riskDotClasses: Record<ManagerProfileSignal["risk_level"], string> = {
  normal: "bg-emerald-500",
  attention: "bg-amber-500",
  critical: "bg-red-500",
};

const heatClasses = {
  green: "border-emerald-200 bg-emerald-500 text-white",
  yellow: "border-amber-200 bg-amber-400 text-amber-950",
  red: "border-red-200 bg-red-500 text-white",
};

const riskOrder: Record<ManagerProfileSignal["risk_level"], number> = {
  critical: 0,
  attention: 1,
  normal: 2,
};

function answerText(value: string | undefined): string {
  if (!value?.trim()) return "Не заполнено";
  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) {
      return parsed
        .map((row) => (Array.isArray(row) ? row.filter(Boolean).join(" / ") : String(row)))
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // Plain text answer.
  }
  return value;
}

function assistantSummary(profile: ManagerProfileSignal): string {
  const revision = profile.latest_revision;
  if (!revision || revision.assistant_mode === "off") return "Ассистент не использовался.";
  const checked = revision.assisted_sections?.checked_questions.length ?? 0;
  const ignored = revision.assisted_sections?.ignored_questions.length ?? 0;
  const withoutAi = revision.assisted_sections?.without_ai_questions?.length ?? 0;
  if (checked === 0 && withoutAi === 0) {
    return "Ассистент отмечен как использованный, детализация по вопросам отсутствует.";
  }
  const parts = [`проверено ответов: ${checked}`];
  if (ignored > 0) parts.push(`проигнорировано рекомендаций: ${ignored}`);
  if (withoutAi > 0) parts.push(`принято без ИИ: ${withoutAi}`);
  if (ignored === 0) parts.push("проигнорированных рекомендаций нет");
  return `Ассистент использовался при заполнении. ${parts.join("; ")}.`;
}

function SignalRow({ profile }: { profile: ManagerProfileSignal }) {
  const [expanded, setExpanded] = useState(false);
  const documentRiskClass = riskClasses[profile.document_signal.risk_level];
  const jobInstruction = profile.document_signal.checks.find((check) => check.document_type === "job_instruction");
  const unitRegulation = profile.document_signal.checks.find((check) => check.document_type === "unit_regulation");
  return (
    <article className={`rounded-2xl border p-4 ${riskClasses[profile.risk_level]}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="font-bold text-slate-950">{profile.employee_name}</h4>
          <p className="mt-1 text-sm text-slate-600">
            {profile.position_title} / {profile.workflow_status_label}
          </p>
        </div>
        <span className="rounded-full bg-white/80 px-3 py-1.5 text-xs font-semibold">
          {profile.risk_label}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-white/80 px-2.5 py-1">
          Прогресс: {Math.round(profile.progress_percent)}%
        </span>
        <span className="rounded-full bg-white/80 px-2.5 py-1">
          Возвратов: {profile.return_count}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-700">{profile.risk_reason}</p>
      <button
        className="mt-3 rounded-xl border border-white/70 bg-white/80 px-3 py-2 text-xs font-semibold text-blue-950"
        onClick={() => setExpanded((value) => !value)}
        type="button"
      >
        {expanded ? "Свернуть анкету и документы" : "Развернуть анкету, ДИ и положение"}
      </button>
      <div className={`mt-3 rounded-xl border p-3 ${documentRiskClass}`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
              Профиль vs документы
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-950">
              {profile.document_signal.risk_label}
            </p>
          </div>
          <span className="rounded-full bg-white/80 px-2.5 py-1 text-xs font-semibold">
            {profile.document_signal.risk_level}
          </span>
        </div>
        <p className="mt-2 text-sm text-slate-700">{profile.document_signal.risk_reason}</p>
        <div className="mt-2 grid gap-2 lg:grid-cols-3">
          {profile.document_signal.checks.map((check) => (
            <div className="rounded-lg bg-white/80 p-2 text-xs text-slate-700" key={check.document_type}>
              <p className="font-semibold text-slate-900">{check.label}</p>
              <p className="mt-1">{check.reason}</p>
              <p className="mt-1 text-slate-500">Совпадение: {Math.round(check.score * 100)}%</p>
              {check.matched_terms.length > 0 && (
                <p className="mt-1 text-slate-500">
                  Термины: {check.matched_terms.slice(0, 5).join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
      {expanded && (
        <div className="mt-3 grid gap-3 xl:grid-cols-3">
          <div className="rounded-xl bg-white/85 p-3 text-sm text-slate-700">
            <p className="font-semibold text-slate-950">Анкета сотрудника</p>
            <p className="mt-1 text-xs text-slate-500">{assistantSummary(profile)}</p>
            <div className="mt-3 max-h-96 space-y-2 overflow-auto pr-1">
              {profile.latest_revision ? (
                profile.questions.map((question) => (
                  <div className="rounded-lg bg-slate-50 p-2" key={question.key}>
                    <p className="text-xs font-semibold text-slate-500">{question.section}</p>
                    <p className="mt-1 font-semibold text-slate-900">{question.title}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-700">
                      {answerText(profile.latest_revision?.answers[question.key])}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">Отправленной версии анкеты пока нет.</p>
              )}
            </div>
          </div>
          <DocumentDetail title="ДИ" check={jobInstruction} />
          <DocumentDetail title="Положение" check={unitRegulation} />
        </div>
      )}
    </article>
  );
}

function DocumentDetail({
  title,
  check,
}: {
  title: string;
  check: ManagerProfileSignal["document_signal"]["checks"][number] | undefined;
}) {
  return (
    <div className="rounded-xl bg-white/85 p-3 text-sm text-slate-700">
      <p className="font-semibold text-slate-950">{title}</p>
      {!check ? (
        <p className="mt-2 text-slate-500">Данные не найдены.</p>
      ) : (
        <>
          <p className="mt-1 text-xs text-slate-500">{check.reason}</p>
          <p className="mt-2 text-xs text-slate-500">Совпадение: {Math.round(check.score * 100)}%</p>
          <div className="mt-3 max-h-96 space-y-2 overflow-auto pr-1">
            {check.documents.length === 0 ? (
              <p className="text-sm text-slate-500">Документ не привязан или не подтверждён.</p>
            ) : (
              check.documents.map((document) => (
                <div className="rounded-lg bg-slate-50 p-2" key={document.document_id}>
                  <p className="font-semibold text-slate-900">{document.title}</p>
                  <p className="text-xs text-slate-500">{document.document_code}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-700">
                    {document.text_excerpt || "Текст документа не загружен или не подтверждён."}
                  </p>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

export function ManagerOverviewPanel({ overview, isLoading, error }: ManagerOverviewPanelProps) {
  const [openUnitId, setOpenUnitId] = useState<number | null>(null);
  const firstUnit = overview?.units[0]?.unit_id ?? null;
  const activeUnitId = openUnitId ?? firstUnit;
  const activeUnit = overview?.units.find((unit) => unit.unit_id === activeUnitId) ?? null;

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
            Обзор руководителя
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">Тепловая карта профилей</h2>
          <p className="mt-1 text-sm text-slate-500">
            Зеленый - 100% без сигналов. Желтый - половина и больше нормальных профилей.
            Красный - меньше 50%, нужен разбор.
          </p>
          {overview?.campaign_name && (
            <p className="mt-2 text-sm font-medium text-slate-700">
              Текущая кампания: {overview.campaign_name}
            </p>
          )}
        </div>
        {overview && (
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="rounded-full bg-emerald-50 px-3 py-2 text-emerald-800">
              Норма: {overview.risk_counts.normal ?? 0}
            </span>
            <span className="rounded-full bg-amber-50 px-3 py-2 text-amber-800">
              Вопросы: {overview.risk_counts.attention ?? 0}
            </span>
            <span className="rounded-full bg-red-50 px-3 py-2 text-red-800">
              Красные: {overview.risk_counts.critical ?? 0}
            </span>
          </div>
        )}
      </div>

      {isLoading && <p className="mt-5 text-sm text-slate-500">Собираю обзор по ветке...</p>}
      {error && <p className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {overview && overview.total_profiles === 0 && (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-4 text-sm text-slate-600">
          В активных кампаниях пока нет профилей подчиненных в вашей ветке.
        </p>
      )}

      {overview && overview.units.length > 0 && (
        <div className="mt-5 space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {overview.units.map((unit) => {
              const isActive = unit.unit_id === activeUnitId;
              return (
                <button
                  className={`min-h-36 rounded-3xl border p-4 text-left shadow-sm transition ${
                    heatClasses[unit.heat_level]
                  } ${isActive ? "ring-4 ring-blue-200" : "hover:scale-[1.01]"}`}
                  key={unit.unit_id}
                  onClick={() => setOpenUnitId(unit.unit_id)}
                  type="button"
                >
                  <div className="flex h-full flex-col justify-between gap-5">
                    <div>
                      <p className="text-lg font-bold">{unit.unit_name}</p>
                      <p className="mt-1 text-sm opacity-90">{unit.heat_label}</p>
                    </div>
                    <div>
                      <p className="text-4xl font-black">{unit.quality_percent}%</p>
                      <p className="text-xs opacity-90">
                        без сигналов: {unit.risk_counts.normal ?? 0} / {unit.total}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {activeUnit && (
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Drill-down
                  </p>
                  <h3 className="mt-2 text-lg font-bold text-slate-950">{activeUnit.unit_name}</h3>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  {(["normal", "attention", "critical"] as const).map((risk) => (
                    <span
                      className="rounded-full bg-white px-2.5 py-1 text-slate-600"
                      key={risk}
                    >
                      <span
                        className={`mr-1 inline-block h-2 w-2 rounded-full ${riskDotClasses[risk]}`}
                      />
                      {risk}: {activeUnit.risk_counts[risk] ?? 0}
                    </span>
                  ))}
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {activeUnit.profiles
                  .slice()
                  .sort((left, right) => riskOrder[left.risk_level] - riskOrder[right.risk_level])
                  .map((profile) => (
                    <SignalRow key={profile.profile_id} profile={profile} />
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
