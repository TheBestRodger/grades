import { useEffect, useMemo, useState } from "react";

import type { AiAnswerCheckResult, AiStatus, EmployeeProfile, ProfileQuestion } from "./types";

const statusLabels: Record<string, string> = {
  not_started: "Не начат",
  draft: "Черновик",
  submitted: "Отправлен на проверку",
  returned_for_revision: "Возвращен на доработку",
  under_review: "На проверке",
  manager_verified: "Подтвержден руководителем",
  returned_by_hr: "Возвращен HR руководителю",
  hr_accepted: "Принят HR",
};

const HIDDEN_QUESTION_KEYS = new Set(["completion_date"]);

function localDraftStorageKey(profileId: number): string {
  return `grades-profile-draft-v2:${profileId}`;
}

function currentDateValue(): string {
  return new Date().toLocaleDateString("ru-RU");
}

function isHiddenQuestion(question: ProfileQuestion): boolean {
  return HIDDEN_QUESTION_KEYS.has(question.key);
}

interface ProfileWorkspaceProps {
  profile: EmployeeProfile;
  ai: AiStatus | undefined;
  error: string | null;
  isSaving: boolean;
  isSubmitting: boolean;
  aiCheckResults: Record<string, AiAnswerCheckResult>;
  aiAnswerSnapshots: Record<string, string>;
  aiCheckingKey: string | null;
  aiCheckError: string | null;
  onSave: (profileId: number, answers: Record<string, string>, aiUsage: AiUsage) => Promise<EmployeeProfile>;
  onSubmit: (profileId: number, answers: Record<string, string>, aiUsage: AiUsage) => Promise<EmployeeProfile>;
  onExport: (profileId: number) => Promise<void>;
  onAiCheck: (
    profileId: number,
    questionKey: string,
    answers: Record<string, string>,
  ) => Promise<AiAnswerCheckResult>;
}

interface AiUsage {
  ai_checked_questions: string[];
  ai_ignored_questions: string[];
  ai_without_ai_questions: string[];
  ai_answer_statuses: Record<string, "accepted" | "ignored" | "rejected" | "without_ai">;
}

interface ProfileSection {
  title: string;
  questions: ProfileQuestion[];
}

type AnswerReviewState = "empty" | "draft" | "accepted" | "rejected" | "ignored" | "without_ai";

type SaveAction =
  | { type: "next" }
  | { type: "exit" }
  | { type: "navigate"; index: number };

function submittedAt(value: string | null): string {
  if (!value) return "";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("ru-RU");
}

function groupQuestionsBySection(questions: ProfileQuestion[]): ProfileSection[] {
  const sections: ProfileSection[] = [];
  const lookup = new Map<string, ProfileSection>();

  questions.forEach((question) => {
    let section = lookup.get(question.section);
    if (!section) {
      section = { title: question.section, questions: [] };
      lookup.set(question.section, section);
      sections.push(section);
    }
    section.questions.push(question);
  });

  return sections;
}

function parseTableAnswer(question: ProfileQuestion, value: string | undefined): string[][] {
  const rowCount = question.rows ?? 1;
  const columnCount = question.columns?.length ?? 1;
  const fallback = Array.from({ length: rowCount }, (_, index) =>
    Array.from({ length: columnCount }, (__, columnIndex) =>
      columnIndex === 0 && question.row_labels?.[index] ? question.row_labels[index] : "",
    ),
  );
  if (!value) return fallback;
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) return fallback;
    return fallback.map((row, rowIndex) =>
      row.map((cell, columnIndex) => {
        const parsedRow = parsed[rowIndex];
        const parsedCell = Array.isArray(parsedRow) ? parsedRow[columnIndex] : undefined;
        if (columnIndex === 0 && question.row_labels?.[rowIndex]) {
          return question.row_labels[rowIndex];
        }
        return typeof parsedCell === "string" ? parsedCell : cell;
      }),
    );
  } catch {
    return fallback;
  }
}

function isQuestionFilled(question: ProfileQuestion, value: string | undefined): boolean {
  if (!value?.trim()) return false;
  if (question.input_type === "single_choice") {
    return Boolean(question.options?.some((option) => option.label === value));
  }
  if (question.input_type !== "table") return true;
  return parseTableAnswer(question, value).some((row) =>
    row.some((cell, columnIndex) => {
      if (columnIndex === 0 && question.row_labels) return false;
      return cell.trim();
    }),
  );
}

function formatAnswer(question: ProfileQuestion, value: string | undefined): string {
  if (!value?.trim()) return "Еще не заполнено";
  if (question.input_type === "single_choice" && !question.options?.some((option) => option.label === value)) {
    return "Еще не заполнено";
  }
  if (question.input_type !== "table") return value;
  const rows = parseTableAnswer(question, value)
    .map((row) => row.filter((cell) => cell.trim()).join(" / "))
    .filter(Boolean);
  return rows.length ? rows.join("; ") : "Еще не заполнено";
}

function isOpenQuestion(question: ProfileQuestion): boolean {
  return question.input_type !== "single_choice";
}

function isAiCheckableQuestion(question: ProfileQuestion): boolean {
  return isOpenQuestion(question) && question.ai_check_enabled !== false;
}

function answerReviewState({
  question,
  value,
  aiAvailable,
  aiUnavailable,
  aiResult,
  aiResultCurrent,
  aiIgnored,
}: {
  question: ProfileQuestion;
  value: string | undefined;
  aiAvailable: boolean;
  aiUnavailable: boolean;
  aiResult: AiAnswerCheckResult | undefined;
  aiResultCurrent: boolean;
  aiIgnored: boolean;
}): AnswerReviewState {
  if (!isQuestionFilled(question, value)) return "empty";
  if (!isAiCheckableQuestion(question)) return "accepted";
  if (!aiAvailable || aiUnavailable) return "without_ai";
  if (aiResultCurrent && aiResult?.accepted) return "accepted";
  if (aiResultCurrent && aiResult && aiIgnored) return "ignored";
  if (aiResultCurrent && aiResult && !aiResult.accepted) return "rejected";
  return "draft";
}

function isAcceptedAnswer(state: AnswerReviewState): boolean {
  return state === "accepted" || state === "ignored" || state === "without_ai";
}

function answerBadge(state: AnswerReviewState): { label: string; className: string } {
  switch (state) {
    case "accepted":
      return { label: "✓ Ответ принят", className: "bg-emerald-100 text-emerald-800" };
    case "rejected":
      return { label: "Ответ не принят", className: "bg-red-100 text-red-800" };
    case "ignored":
      return { label: "Заполнено, рекомендация ИИ проигнорирована", className: "bg-amber-100 text-amber-900" };
    case "without_ai":
      return { label: "Заполнено без ИИ", className: "bg-orange-100 text-orange-900" };
    case "draft":
      return { label: "Черновик ответа", className: "bg-slate-100 text-slate-600" };
    default:
      return { label: "Нужно заполнить", className: "bg-slate-100 text-slate-500" };
  }
}

function fieldFrameClass(state: AnswerReviewState): string {
  switch (state) {
    case "accepted":
      return "border-emerald-200 bg-emerald-50/40";
    case "rejected":
      return "border-red-200 bg-red-50/30";
    case "ignored":
      return "border-amber-200 bg-amber-50/40";
    case "without_ai":
      return "border-orange-200 bg-orange-50/30";
    case "draft":
      return "border-slate-200 bg-slate-50/50";
    default:
      return "border-slate-200 bg-white";
  }
}

function assistantUsageLabel(revision: EmployeeProfile["revisions"][number]): string {
  if (revision.assistant_mode === "off") return "ИИ не использовался";
  const checked = revision.assisted_sections?.checked_questions.length ?? 0;
  const ignored = revision.assisted_sections?.ignored_questions.length ?? 0;
  const withoutAi = revision.assisted_sections?.without_ai_questions?.length ?? 0;
  if (checked === 0 && withoutAi === 0) return "ИИ использовался";
  const parts = [`проверено ответов: ${checked}`];
  if (ignored > 0) parts.push(`проигнорировано рекомендаций: ${ignored}`);
  if (withoutAi > 0) parts.push(`принято без ИИ: ${withoutAi}`);
  if (ignored === 0) parts.push("проигнорированных рекомендаций нет");
  return `ИИ использовался. ${parts.join("; ")}`;
}

function TableAnswer({
  question,
  value,
  disabled,
  onChange,
}: {
  question: ProfileQuestion;
  value: string | undefined;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const table = parseTableAnswer(question, value);

  function updateCell(rowIndex: number, columnIndex: number, next: string) {
    const nextTable = table.map((row, currentRow) =>
      row.map((cell, currentColumn) =>
        currentRow === rowIndex && currentColumn === columnIndex ? next : cell,
      ),
    );
    onChange(JSON.stringify(nextTable));
  }

  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200">
      <div
        className="grid bg-slate-100 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
        style={{ gridTemplateColumns: `repeat(${question.columns?.length ?? 1}, minmax(0, 1fr))` }}
      >
        {question.columns?.map((column) => (
          <div className="border-r border-slate-200 px-3 py-2 last:border-r-0" key={column}>
            {column}
          </div>
        ))}
      </div>
      {table.map((row, rowIndex) => (
        <div
          className="grid border-t border-slate-200"
          key={rowIndex}
          style={{ gridTemplateColumns: `repeat(${question.columns?.length ?? 1}, minmax(0, 1fr))` }}
        >
          {row.map((cell, columnIndex) => {
            const locked = columnIndex === 0 && Boolean(question.row_labels?.[rowIndex]);
            return (
              <textarea
                aria-label={`${question.title}: строка ${rowIndex + 1}, колонка ${columnIndex + 1}`}
                className={`min-h-20 resize-y border-r border-slate-100 px-3 py-2 text-sm outline-none last:border-r-0 focus:bg-blue-50 ${
                  locked ? "bg-slate-50 font-medium text-slate-500" : "bg-white"
                }`}
                disabled={disabled || locked}
                key={`${rowIndex}-${columnIndex}`}
                onChange={(event) => updateCell(rowIndex, columnIndex, event.target.value)}
                value={cell}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}

function ProfileField({
  question,
  value,
  canEdit,
  aiEnabled,
  aiUnavailable,
  aiResult,
  aiResultCurrent,
  aiIgnored,
  aiChecking,
  aiCheckError,
  reviewState,
  onChange,
  onAiCheck,
  onIgnoreAiResult,
}: {
  question: ProfileQuestion;
  value: string | undefined;
  canEdit: boolean;
  aiEnabled: boolean;
  aiUnavailable: boolean;
  aiResult: AiAnswerCheckResult | undefined;
  aiResultCurrent: boolean;
  aiIgnored: boolean;
  aiChecking: boolean;
  aiCheckError: string | null;
  reviewState: AnswerReviewState;
  onChange: (value: string) => void;
  onAiCheck: () => void;
  onIgnoreAiResult: () => void;
}) {
  const filled = isQuestionFilled(question, value);
  const [offlineAiNotice, setOfflineAiNotice] = useState(false);
  const badge = answerBadge(reviewState);
  const clarityStyle =
    aiResult && !aiResultCurrent
      ? "border-slate-200 bg-slate-50 text-slate-700"
      : aiResult?.accepted
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : "border-amber-200 bg-amber-50 text-amber-900";
  const aiCheckableQuestion = isAiCheckableQuestion(question);
  const clarityLabel =
    aiResult && `${aiResult.clarity_percent}% / порог ${aiResult.clarity_threshold}%`;
  const canIgnoreAiRecommendation = Boolean(aiResultCurrent && aiResult && !aiResult.accepted);

  return (
    <article
      className={`rounded-2xl border p-4 ${fieldFrameClass(reviewState)}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            Поле шаблона
          </p>
          <h4 className="mt-1 text-lg font-bold text-slate-950">{question.title}</h4>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>

      <p className="mt-3 text-sm font-medium text-slate-800">{question.question}</p>
      <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">{question.example}</p>
      {question.bad_example && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          <p>
            <span className="font-semibold text-slate-800">Слабый пример: </span>
            {question.bad_example}
          </p>
        </div>
      )}

      {question.quick_answers.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {question.quick_answers.map((answer) => (
            <button
              className="rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-900 disabled:opacity-50"
              disabled={!canEdit}
              key={answer}
              onClick={() => onChange(answer)}
              type="button"
            >
              {answer}
            </button>
          ))}
        </div>
      )}

      {question.input_type === "single_choice" ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {question.options?.map((option) => {
            const selected = value === option.label;
            return (
              <button
                className={`rounded-2xl border px-4 py-3 text-left ${
                  selected
                    ? "border-blue-400 bg-blue-50 text-blue-950"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                disabled={!canEdit}
                key={option.label}
                onClick={() => onChange(option.label)}
                type="button"
              >
                <span className="font-semibold">{selected ? "✓ " : "☐ "}{option.label}</span>
                {option.description && (
                  <span className="mt-1 block text-sm text-slate-500">{option.description}</span>
                )}
              </button>
            );
          })}
        </div>
      ) : question.input_type === "table" ? (
        <TableAnswer
          disabled={!canEdit}
          onChange={onChange}
          question={question}
          value={value}
        />
      ) : question.input_type === "text" ? (
        <input
          aria-label={`Ответ: ${question.title}`}
          className="mt-4 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          disabled={!canEdit}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Введите ответ..."
          value={value ?? ""}
        />
      ) : (
        <textarea
          aria-label={`Ответ: ${question.title}`}
          className="mt-4 min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          disabled={!canEdit}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Введите ваш ответ..."
          value={value ?? ""}
        />
      )}

      {aiCheckableQuestion && (
        <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-blue-950">AI-проверка ответа</p>
              {!aiEnabled && (
                <p className="mt-1 text-amber-900">
                  ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос.
                </p>
              )}
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                className="rounded-xl bg-blue-950 px-4 py-2 text-xs font-semibold text-white disabled:bg-slate-300"
                disabled={!filled || aiChecking}
                onClick={() => {
                  if (!aiEnabled) {
                    setOfflineAiNotice(true);
                    return;
                  }
                  setOfflineAiNotice(false);
                  onAiCheck();
                }}
                type="button"
              >
                {aiChecking ? "Отправляю..." : "Ответить"}
              </button>
              {canIgnoreAiRecommendation && (
                <button
                  className={`rounded-xl border px-4 py-2 text-xs font-bold shadow-sm transition ${
                    aiIgnored
                      ? "border-amber-700 bg-amber-700 text-white hover:bg-amber-800"
                      : "border-orange-600 bg-orange-500 text-white hover:bg-orange-600"
                  }`}
                  onClick={onIgnoreAiResult}
                  type="button"
                >
                  {aiIgnored ? "Рекомендация ИИ проигнорирована" : "Игнорировать рекомендацию ИИ"}
                </button>
              )}
            </div>
          </div>
          {offlineAiNotice && !aiEnabled && (
            <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
              ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос.
            </p>
          )}
          {aiCheckError && (
            <p
              className={`mt-3 rounded-xl px-3 py-2 ${
                aiUnavailable ? "border border-amber-200 bg-amber-50 text-amber-900" : "bg-red-50 text-red-700"
              }`}
            >
              {aiUnavailable
                ? "ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос."
                : aiCheckError}
            </p>
          )}
          {aiResult && (
            <div className={`mt-3 rounded-xl border px-3 py-2 ${clarityStyle}`}>
              <p className="font-semibold">
                Понятность: {clarityLabel} ·{" "}
                {!aiResultCurrent
                  ? "ответ изменён после проверки"
                  : aiResult.accepted
                    ? "ответ принят"
                    : "нужно уточнить"}
              </p>
              {!aiResultCurrent ? (
                <p className="mt-1">Проверьте ответ заново, чтобы ИИ оценил текущий текст.</p>
              ) : (
                <p className="mt-1">{aiResult.explanation}</p>
              )}
              {aiResultCurrent && !aiResult.accepted && aiResult.followup_question && (
                <p className="mt-2 font-medium">Уточняющий вопрос: {aiResult.followup_question}</p>
              )}
              {aiResultCurrent && !aiResult.accepted && aiIgnored && (
                <p className="mt-3 text-xs text-amber-800">
                  Ответ будет сохранён как решение пользователя.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

export function ProfileWorkspace({
  profile,
  ai,
  error,
  isSaving,
  isSubmitting,
  aiCheckResults,
  aiAnswerSnapshots,
  aiCheckingKey,
  aiCheckError,
  onSave,
  onSubmit,
  onExport,
  onAiCheck,
}: ProfileWorkspaceProps) {
  const [answers, setAnswers] = useState<Record<string, string>>(profile.answers);
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [paused, setPaused] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [ignoredAiQuestions, setIgnoredAiQuestions] = useState<Set<string>>(new Set());
  const [unavailableAiQuestions, setUnavailableAiQuestions] = useState<Set<string>>(new Set());

  useEffect(() => {
    let nextAnswers = profile.answers;
    let hasLocalDraft = false;
    try {
      const raw = window.localStorage.getItem(localDraftStorageKey(profile.id));
      if (raw && profile.workflow_status !== "hr_accepted") {
        const parsed = JSON.parse(raw) as { answers?: Record<string, string> };
        if (parsed.answers && typeof parsed.answers === "object") {
          nextAnswers = { ...profile.answers, ...parsed.answers };
          hasLocalDraft = true;
        }
      }
    } catch {
      hasLocalDraft = false;
    }
    setAnswers(nextAnswers);
    setDirty(hasLocalDraft);
    setConfirming(false);
    setPaused(false);
    setActiveSectionIndex(0);
    setIgnoredAiQuestions(new Set());
    setUnavailableAiQuestions(new Set());
  }, [profile.id]);

  const visibleQuestions = useMemo(
    () => profile.questions.filter((question) => !isHiddenQuestion(question)),
    [profile.questions],
  );
  const sections = useMemo(() => groupQuestionsBySection(visibleQuestions), [visibleQuestions]);
  const activeSection = sections[activeSectionIndex] ?? sections[0];
  const aiEnabled = Boolean(ai?.available);
  const questionState = (item: ProfileQuestion) => {
    const liveState = answerReviewState({
      question: item,
      value: answers[item.key],
      aiAvailable: aiEnabled,
      aiUnavailable: unavailableAiQuestions.has(item.key),
      aiResult: aiCheckResults[item.key],
      aiResultCurrent: aiAnswerSnapshots[item.key] === answers[item.key],
      aiIgnored: ignoredAiQuestions.has(item.key),
    });
    if (liveState !== "draft") return liveState;
    if ((answers[item.key] ?? "") !== (profile.answers[item.key] ?? "")) return liveState;
    const persistedStatus = profile.draft_assisted_sections?.answer_statuses?.[item.key];
    if (
      persistedStatus === "accepted" ||
      persistedStatus === "ignored" ||
      persistedStatus === "rejected" ||
      persistedStatus === "without_ai"
    ) {
      return persistedStatus;
    }
    return liveState;
  };
  const completed = useMemo(
    () => visibleQuestions.filter((item) => isAcceptedAnswer(questionState(item))).length,
    [
      answers,
      aiAnswerSnapshots,
      aiCheckResults,
      aiEnabled,
      ignoredAiQuestions,
      profile.answers,
      profile.draft_assisted_sections,
      visibleQuestions,
      unavailableAiQuestions,
    ],
  );
  const progress = visibleQuestions.length ? Math.round((completed / visibleQuestions.length) * 100) : 100;
  const latestReturn = profile.review_events.find((event) => event.action === "returned");

  function sectionProgress(section: ProfileSection) {
    const states = section.questions.map((item) => questionState(item));
    const filled = states.filter(isAcceptedAnswer).length;
    return {
      filled,
      total: section.questions.length,
      complete: filled === section.questions.length,
      hasIgnoredAi: states.includes("ignored"),
      hasWithoutAi: states.includes("without_ai"),
      hasRejectedAi: states.includes("rejected"),
      hasDraft: states.includes("draft"),
    };
  }
  const activeSectionStatus = activeSection
    ? sectionProgress(activeSection)
    : { filled: 0, total: 0, complete: false, hasIgnoredAi: false, hasWithoutAi: false, hasRejectedAi: false, hasDraft: false };

  function updateAnswer(questionKey: string, value: string) {
    setAnswers((existing) => ({ ...existing, [questionKey]: value }));
    setDirty(true);
    setNotice(null);
    setLocalError(null);
    setUnavailableAiQuestions((existing) => {
      if (!existing.has(questionKey)) return existing;
      const next = new Set(existing);
      next.delete(questionKey);
      return next;
    });
  }

  function questionnaireAnswers(): Record<string, string> {
    return Object.fromEntries(
      profile.questions.map((question) => {
        const value = isHiddenQuestion(question)
          ? answers[question.key] || currentDateValue()
          : answers[question.key] ?? "";
        if (
          question.input_type === "single_choice" &&
          value &&
          !question.options?.some((option) => option.label === value)
        ) {
          return [question.key, ""];
        }
        return [question.key, value];
      }),
    );
  }

  async function checkAnswer(questionKey: string) {
    setNotice(null);
    setLocalError(null);
    try {
      await onAiCheck(profile.id, questionKey, questionnaireAnswers());
      setUnavailableAiQuestions((existing) => {
        if (!existing.has(questionKey)) return existing;
        const next = new Set(existing);
        next.delete(questionKey);
        return next;
      });
    } catch {
      setUnavailableAiQuestions((existing) => new Set(existing).add(questionKey));
    }
  }

  function aiUsage(): AiUsage {
    const checked = new Set(
      Object.entries(aiAnswerSnapshots)
      .filter(([key, snapshot]) => snapshot === answers[key])
        .map(([key]) => key),
    );
    profile.draft_assisted_sections?.checked_questions.forEach((key) => {
      if ((answers[key] ?? "") === (profile.answers[key] ?? "")) checked.add(key);
    });
    const ignored = new Set([...checked].filter((key) => ignoredAiQuestions.has(key)));
    profile.draft_assisted_sections?.ignored_questions.forEach((key) => {
      if (checked.has(key) && (answers[key] ?? "") === (profile.answers[key] ?? "")) ignored.add(key);
    });
    const answerStatuses: Record<string, "accepted" | "ignored" | "rejected" | "without_ai"> = {};
    visibleQuestions.forEach((question) => {
      const state = questionState(question);
      if (state === "accepted" || state === "ignored" || state === "rejected" || state === "without_ai") {
        answerStatuses[question.key] = state;
      }
    });
    return {
      ai_checked_questions: [...checked],
      ai_ignored_questions: [...ignored],
      ai_without_ai_questions: visibleQuestions
        .filter((question) => {
          if (questionState(question) !== "without_ai") return false;
          return isQuestionFilled(question, answers[question.key]);
        })
        .map((question) => question.key),
      ai_answer_statuses: answerStatuses,
    };
  }

  useEffect(() => {
    if (!dirty) return;
    try {
      window.localStorage.setItem(
        localDraftStorageKey(profile.id),
        JSON.stringify({ answers, updated_at: new Date().toISOString() }),
      );
    } catch {
      // If localStorage is unavailable, the explicit save button still persists the draft.
    }
  }, [answers, dirty, profile.id]);

  async function save(message: string, nextAnswers = questionnaireAnswers()): Promise<boolean> {
    try {
      const result = await onSave(profile.id, nextAnswers, aiUsage());
      setAnswers(result.answers);
      setDirty(false);
      window.localStorage.removeItem(localDraftStorageKey(profile.id));
      setNotice(message);
      return true;
    } catch {
      return false;
    }
  }

  async function completeSaveAction(action: SaveAction) {
    const success = await save("Раздел сохранен как черновик. Незаполненные ответы можно пропустить и вернуться позже.");
    if (!success) return;
    if (action.type === "next" && activeSectionIndex < sections.length - 1) {
      setActiveSectionIndex((value) => value + 1);
    }
    if (action.type === "navigate") {
      setActiveSectionIndex(action.index);
    }
    if (action.type === "exit") {
      setPaused(true);
    }
  }

  function requestSaveAction(action: SaveAction) {
    setNotice(null);
    setLocalError(null);
    void completeSaveAction(action);
  }

  function goNext() {
    requestSaveAction({ type: "next" });
  }

  async function navigateTo(index: number) {
    if (!dirty) {
      setActiveSectionIndex(index);
      return;
    }
    requestSaveAction({ type: "navigate", index });
  }

  async function saveAndExit() {
    requestSaveAction({ type: "exit" });
  }

  async function startSubmit() {
    const missing = visibleQuestions.find((item) => !isAcceptedAnswer(questionState(item)));
    if (missing) {
      const sectionIndex = sections.findIndex((section) =>
        section.questions.some((item) => item.key === missing.key),
      );
      setActiveSectionIndex(Math.max(sectionIndex, 0));
      const state = questionState(missing);
      const message =
        state === "rejected"
          ? "Перед сдачей исправьте ответы, которые не соответствуют критериям ИИ, либо явно проигнорируйте рекомендацию ИИ."
          : state === "draft"
            ? "Перед сдачей проверьте заполненные ответы через ИИ. Если ИИ недоступен, ответы будут приняты без ИИ."
            : "Для сдачи нужно заполнить все обязательные поля шаблона профиля должности.";
      setNotice(message);
      return;
    }
    setConfirming(true);
    setNotice(null);
  }

  async function confirmSubmit() {
    try {
      const result = await onSubmit(profile.id, questionnaireAnswers(), aiUsage());
      setAnswers(result.answers);
      setDirty(false);
      window.localStorage.removeItem(localDraftStorageKey(profile.id));
      setConfirming(false);
      setNotice(`Версия ${result.revisions[0].revision_no} отправлена на проверку.`);
    } catch {
      setConfirming(false);
    }
  }

  async function exportTemplate() {
    try {
      setExporting(true);
      await onExport(profile.id);
      setLocalError(null);
      setNotice("Excel-шаблон с текущей версией профиля подготовлен.");
    } catch {
      setNotice(null);
      setLocalError("Не удалось подготовить Excel-шаблон.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="rounded-3xl border border-blue-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
            Личный профиль должности
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">{profile.position_title}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {profile.unit_name} / кампания «{profile.campaign_name}»
          </p>
        </div>
        <div className="min-w-52 rounded-2xl bg-blue-50 px-4 py-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">{statusLabels[profile.workflow_status] ?? profile.workflow_status}</span>
            <strong className="text-blue-950">{progress}%</strong>
          </div>
          <div className="mt-3 h-2 rounded-full bg-blue-100">
            <div className="h-2 rounded-full bg-blue-800 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Заполнено {completed} из {visibleQuestions.length} полей шаблона
          </p>
        </div>
      </div>

      {profile.workflow_status === "returned_for_revision" && latestReturn?.comment && (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
          <p className="font-semibold">Руководитель вернул профиль на доработку</p>
          <p className="mt-2">{latestReturn.comment}</p>
          <p className="mt-2 text-amber-800">
            Исправьте ответы и отправьте новую версию. Предыдущая версия сохранена в истории.
          </p>
        </div>
      )}
      {profile.workflow_status === "under_review" && (
        <div className="mt-5 rounded-2xl border border-indigo-200 bg-indigo-50 px-5 py-4 text-sm text-indigo-950">
          <p className="font-semibold">Профиль находится на проверке руководителя</p>
          <p className="mt-1">Редактирование временно заблокировано до решения руководителя.</p>
        </div>
      )}
      {profile.workflow_status === "manager_verified" && (
        <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
          <p className="font-semibold">Профиль подтвержден руководителем</p>
          <p className="mt-1">Версия зафиксирована и ожидает следующего этапа обработки HR.</p>
        </div>
      )}
      {profile.workflow_status === "returned_by_hr" && (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">
          <p className="font-semibold">HR вернул профиль вашему руководителю</p>
          <p className="mt-1">
            Редактирование пока закрыто. Руководитель решит, нужна ли новая доработка с вашей стороны.
          </p>
        </div>
      )}
      {profile.workflow_status === "hr_accepted" && (
        <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
          <p className="font-semibold">Профиль принят HR</p>
          <p className="mt-1">Профиль завершен в рамках текущей кампании и сохранен в истории.</p>
        </div>
      )}

      {paused ? (
        <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50 p-5 text-sm text-emerald-900">
          <p className="font-semibold">Черновик сохранен</p>
          <p className="mt-1">Прогресс зафиксирован. Анкету можно продолжить с сохраненными ответами.</p>
          <button
            className="mt-4 rounded-xl bg-blue-900 px-5 py-2.5 font-semibold text-white"
            onClick={() => setPaused(false)}
            type="button"
          >
            Продолжить заполнение
          </button>
        </div>
      ) : (
        <>
        <div className="mt-5 grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
          <nav className="space-y-2" aria-label="Разделы профиля">
            {sections.map((section, index) => {
              const status = sectionProgress(section);
              const active = index === activeSectionIndex;
              return (
                <button
                  className={`flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left text-sm ${
                    status.complete
                      ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                      : active
                        ? "border-blue-300 bg-blue-50 text-blue-950"
                        : "border-slate-100 bg-slate-50 text-slate-700"
                  }`}
                  key={section.title}
                  onClick={() => navigateTo(index)}
                  type="button"
                >
                  <span
                    className={`mt-0.5 h-6 w-6 shrink-0 rounded-full text-center text-xs font-semibold leading-6 ${
                      status.complete ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {status.complete ? "✓" : index + 1}
                  </span>
                  <span className="min-w-0">
                    <span className="flex items-center gap-2 font-semibold">
                      <span>{section.title}</span>
                      {status.hasIgnoredAi && (
                        <span
                          className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800"
                          title="В разделе есть ответы, где пользователь проигнорировал рекомендации ИИ."
                        >
                          !
                        </span>
                      )}
                      {status.hasWithoutAi && (
                        <span
                          className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-orange-100 text-xs font-bold text-orange-800"
                          title="В разделе есть ответы, заполненные без ИИ-проверки."
                        >
                          i
                        </span>
                      )}
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      {status.filled} из {status.total} полей
                    </span>
                  </span>
                </button>
              );
            })}
          </nav>

          <div className="min-w-0">
            <div className="rounded-2xl border border-slate-100 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Раздел {activeSectionIndex + 1} из {sections.length}
                  </p>
                  <h3 className="mt-2 text-xl font-bold text-slate-950">
                    {activeSection?.title ?? "Раздел профиля"}
                  </h3>
                </div>
                <span
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                    activeSectionStatus.hasIgnoredAi
                      ? "bg-amber-100 text-amber-900"
                      : activeSectionStatus.hasWithoutAi
                        ? "bg-orange-100 text-orange-900"
                        : activeSectionStatus.complete
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-600"
                  }`}
                  title={
                    activeSectionStatus.hasIgnoredAi
                      ? "В разделе есть ответы, где пользователь проигнорировал рекомендации ИИ."
                      : activeSectionStatus.hasWithoutAi
                        ? "В разделе есть ответы, заполненные без ИИ-проверки."
                        : undefined
                  }
                >
                  {activeSectionStatus.hasIgnoredAi
                    ? "! Есть игнор рекомендаций ИИ"
                    : activeSectionStatus.hasWithoutAi
                      ? "Заполнено без ИИ"
                      : activeSectionStatus.complete
                        ? "✓ Раздел заполнен"
                        : `${activeSectionStatus.filled} из ${activeSectionStatus.total} заполнено`}
                </span>
              </div>

              {!ai?.available && (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <p className="font-semibold">ИИ-ассистент недоступен</p>
                  <p className="mt-1">{ai?.fallback_message}</p>
                </div>
              )}

              <div className="mt-5 space-y-4">
                {activeSection?.questions.map((item) => (
                  <ProfileField
                    aiCheckError={
                      aiCheckingKey === item.key || unavailableAiQuestions.has(item.key)
                        ? aiCheckError
                        : null
                    }
                    aiChecking={aiCheckingKey === item.key}
                    aiEnabled={aiEnabled}
                    aiUnavailable={unavailableAiQuestions.has(item.key)}
                    aiResult={aiCheckResults[item.key]}
                    aiResultCurrent={aiAnswerSnapshots[item.key] === answers[item.key]}
                    aiIgnored={ignoredAiQuestions.has(item.key)}
                    canEdit={profile.can_edit}
                    key={item.key}
                    onChange={(value) => updateAnswer(item.key, value)}
                    onAiCheck={() => checkAnswer(item.key)}
                    onIgnoreAiResult={() =>
                      setIgnoredAiQuestions((existing) => {
                        const next = new Set(existing);
                        if (next.has(item.key)) {
                          next.delete(item.key);
                        } else {
                          next.add(item.key);
                        }
                        return next;
                      })
                    }
                    question={item}
                    reviewState={questionState(item)}
                    value={answers[item.key]}
                  />
                ))}
              </div>

              <p className="mt-3 text-xs text-slate-500">
                При переходе далее раздел сохраняется как черновик. Ответы можно исправить до проверки руководителем.
              </p>

              {(notice || error || localError) && (
                <p className={`mt-4 rounded-xl px-4 py-3 text-sm ${error || localError ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800"}`}>
                  {error ?? localError ?? notice}
                </p>
              )}

              {confirming && (
                <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
                  <p className="font-semibold">Готовы отправить профиль на проверку?</p>
                  <p className="mt-1">
                    Будет создана новая неизменяемая версия. Если ИИ-проверка использовалась, это будет видно руководителю.
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button
                      className="rounded-lg bg-blue-900 px-4 py-2 font-semibold text-white"
                      disabled={isSubmitting}
                      onClick={confirmSubmit}
                      type="button"
                    >
                      {isSubmitting ? "Отправляю..." : "Подтвердить отправку"}
                    </button>
                    <button
                      className="rounded-lg border border-blue-200 px-4 py-2"
                      onClick={() => setConfirming(false)}
                      type="button"
                    >
                      Вернуться к ответам
                    </button>
                  </div>
                </div>
              )}

              {!confirming && profile.can_edit && (
                <div className="mt-5 flex flex-wrap justify-between gap-3">
                  <div className="flex gap-2">
                    <button
                      className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm disabled:opacity-40"
                      disabled={activeSectionIndex === 0}
                      onClick={() => navigateTo(activeSectionIndex - 1)}
                      type="button"
                    >
                      Назад
                    </button>
                    <button
                      className="rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-medium text-blue-900 disabled:opacity-50"
                      disabled={isSaving || !dirty}
                      onClick={saveAndExit}
                      type="button"
                    >
                      {isSaving ? "Сохраняю..." : "Сохранить и выйти"}
                    </button>
                  </div>
                  {activeSectionIndex < sections.length - 1 ? (
                    <button
                      className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                      disabled={isSaving || Boolean(aiCheckingKey)}
                      onClick={goNext}
                      type="button"
                    >
                      {aiCheckingKey ? "Жду ответ LLM..." : isSaving ? "Сохраняю..." : "Сохранить раздел и далее"}
                    </button>
                  ) : (
                    <button
                      className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white"
                      disabled={Boolean(aiCheckingKey)}
                      onClick={startSubmit}
                      type="button"
                    >
                      {aiCheckingKey ? "Жду ответ LLM..." : "Отправить на проверку"}
                    </button>
                  )}
                </div>
              )}
              {profile.revisions.length > 0 && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <button
                    className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-900 disabled:opacity-50"
                    disabled={exporting}
                    onClick={exportTemplate}
                    type="button"
                  >
                    {exporting ? "Готовлю Excel..." : "Скачать Excel-шаблон"}
                  </button>
                  <p className="mt-2 text-xs text-slate-500">
                    Заполняется исходная форма профиля должности, последняя отправленная версия.
                  </p>
                </div>
              )}
            </div>

          </div>

          <aside className="h-fit rounded-2xl bg-slate-50 p-4">
            <h3 className="font-bold text-slate-900">Краткий просмотр текущего раздела</h3>
            <div className="mt-3 space-y-3">
              {activeSection?.questions.map((item) => (
                <div key={item.key}>
                  <p className="text-xs font-semibold text-slate-500">{item.title}</p>
                  <p className="mt-1 line-clamp-3 text-sm text-slate-700">
                    {formatAnswer(item, answers[item.key])}
                  </p>
                </div>
              ))}
            </div>
          </aside>
        </div>

        <div className="mt-5 rounded-2xl border border-slate-100 bg-white p-4">
          <h3 className="font-bold text-slate-900">История сдачи</h3>
          {profile.revisions.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">Отправленных версий пока нет.</p>
          ) : (
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {profile.revisions.map((revision) => (
                <div className="rounded-xl bg-slate-50 px-3 py-2 text-sm" key={revision.id}>
                  <p className="font-semibold">Версия {revision.revision_no}</p>
                  <p className="text-xs text-slate-500">{submittedAt(revision.submitted_at)}</p>
                  <p className="mt-1 text-xs text-slate-600">{assistantUsageLabel(revision)}</p>
                </div>
              ))}
            </div>
          )}
          {profile.review_events.length > 0 && (
            <div className="mt-4 border-t border-slate-200 pt-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Решения руководителя
              </p>
              <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {profile.review_events.map((event) => (
                  <div className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600" key={event.id}>
                    <p className="font-medium">
                      {event.action === "taken"
                        ? "Взято на проверку"
                        : event.action === "returned"
                          ? "Возвращено на доработку"
                          : event.action === "verified"
                            ? "Подтверждено руководителем"
                            : event.action === "hr_returned"
                              ? "Возвращено HR руководителю"
                              : "Принято HR"}{" "}
                      / версия {event.revision_no}
                    </p>
                    <p>{submittedAt(event.created_at)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        </>
      )}
    </section>
  );
}
