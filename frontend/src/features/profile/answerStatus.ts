import type { AiAnswerCheckResult, EmployeeProfile, ProfileQuestion } from "../../types";
import type { AiUsage, AnswerReviewState } from "./types";

export const statusLabels: Record<string, string> = {
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
const LOCKED_PREFILLED_QUESTION_KEYS = new Set([
  "position_name",
  "org_structure",
  "administrative_manager",
]);

export function currentDateValue(): string {
  return new Date().toLocaleDateString("ru-RU");
}

export function submittedAt(value: string | null): string {
  if (!value) return "";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("ru-RU");
}

export function isHiddenQuestion(question: ProfileQuestion): boolean {
  return HIDDEN_QUESTION_KEYS.has(question.key);
}

export function isLockedPrefilledQuestion(question: ProfileQuestion): boolean {
  return LOCKED_PREFILLED_QUESTION_KEYS.has(question.key);
}

export function parseTableAnswer(question: ProfileQuestion, value: string | undefined): string[][] {
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

export function isQuestionFilled(question: ProfileQuestion, value: string | undefined): boolean {
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

export function formatAnswer(question: ProfileQuestion, value: string | undefined): string {
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

export function isOpenQuestion(question: ProfileQuestion): boolean {
  return question.input_type !== "single_choice";
}

export function isAiCheckableQuestion(question: ProfileQuestion): boolean {
  return isOpenQuestion(question) && question.ai_check_enabled !== false;
}

export function answerReviewState({
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
  if (isLockedPrefilledQuestion(question)) return "accepted";
  if (!isAiCheckableQuestion(question)) return "accepted";
  if (!aiAvailable || aiUnavailable) return "without_ai";
  if (aiResultCurrent && aiResult?.accepted) return "accepted";
  if (aiResultCurrent && aiResult && aiIgnored) return "ignored";
  if (aiResultCurrent && aiResult && !aiResult.accepted) return "rejected";
  return "draft";
}

export function isAcceptedAnswer(state: AnswerReviewState): boolean {
  return state === "accepted" || state === "ignored" || state === "without_ai";
}

export function persistedAnswerState(status: string | undefined): AnswerReviewState | null {
  switch (status) {
    case "accepted":
    case "rejected":
      return status;
    case "ignored":
    case "ignored_ai":
      return "ignored";
    case "without_ai":
    case "filled_without_ai":
      return "without_ai";
    default:
      return null;
  }
}

export function removeAiUsageQuestion(
  usage: Partial<AiUsage> | null,
  questionKey: string,
): Partial<AiUsage> | null {
  if (!usage) return null;
  const answerStatuses = { ...(usage.ai_answer_statuses ?? {}) };
  delete answerStatuses[questionKey];
  return {
    ai_checked_questions: usage.ai_checked_questions?.filter((key) => key !== questionKey),
    ai_ignored_questions: usage.ai_ignored_questions?.filter((key) => key !== questionKey),
    ai_without_ai_questions: usage.ai_without_ai_questions?.filter((key) => key !== questionKey),
    ai_answer_statuses: answerStatuses,
  };
}

export function answerBadge(state: AnswerReviewState): { label: string; className: string } {
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

export function fieldFrameClass(state: AnswerReviewState): string {
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

export function assistantUsageLabel(revision: EmployeeProfile["revisions"][number]): string {
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
