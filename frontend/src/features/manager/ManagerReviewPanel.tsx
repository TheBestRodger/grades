import { useState } from "react";

import type { ManagerReviewProfile, ProfileQuestion, ProfileRevision } from "../../types";
import { BulkReturnBox } from "../../components/BulkReturnBox";

const statusLabels: Record<string, string> = {
  not_started: "Не начат",
  draft: "Черновик сотрудника",
  submitted: "Ожидает проверки",
  under_review: "На вашей проверке",
  returned_for_revision: "Возвращен сотруднику",
  manager_verified: "Подтвержден руководителем",
  returned_by_hr: "Возвращен HR руководителю",
  hr_accepted: "Принят HR",
};

const eventLabels: Record<string, string> = {
  taken: "Взят на проверку",
  returned: "Возвращен на доработку",
  verified: "Подтвержден",
  hr_returned: "Возвращен HR",
  hr_accepted: "Принят HR",
};

const quickReason = "Уточните результат обязанностей и критерии, по которым можно оценить выполнение.";

function formatTimestamp(value: string | null): string {
  if (!value) return "";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("ru-RU");
}

function formatAnswer(question: ProfileQuestion, value: string | undefined): string {
  if (!value?.trim()) return "Не заполнено";
  if (question.input_type !== "table") return value;
  try {
    const rows = JSON.parse(value) as unknown;
    if (!Array.isArray(rows)) return value;
    const textRows = rows
      .filter(Array.isArray)
      .map((row) => row.filter((cell) => typeof cell === "string" && cell.trim()).join(" / "))
      .filter(Boolean);
    return textRows.length ? textRows.join("; ") : "Не заполнено";
  } catch {
    return value;
  }
}

function assistantUsageLabel(revision: ProfileRevision): string {
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

interface ManagerReviewPanelProps {
  reviews: ManagerReviewProfile[];
  error: string | null;
  message: string | null;
  activeProfileId: number | null;
  bulkActive: boolean;
  onTake: (profileId: number) => void;
  onReturn: (profileId: number, reason: string) => void;
  onBulkReturnSelected: (profileIds: number[], reason: string) => void;
  onBulkReturnUnit: (orgUnitId: number, reason: string) => void;
  onVerify: (profileId: number) => void;
}

export function ManagerReviewPanel({
  reviews,
  error,
  message,
  activeProfileId,
  bulkActive,
  onTake,
  onReturn,
  onBulkReturnSelected,
  onBulkReturnUnit,
  onVerify,
}: ManagerReviewPanelProps) {
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const submitted = reviews.filter((review) => review.workflow_status === "submitted").length;
  const inReview = reviews.filter((review) => review.workflow_status === "under_review").length;
  const returnable = reviews.filter((review) => review.can_decide);

  return (
    <section className="rounded-3xl border border-indigo-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-700">
            Кабинет руководителя
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">Проверка профилей подчиненных</h2>
          <p className="mt-1 text-sm text-slate-500">
            В работу берется последняя отправленная версия непосредственного подчиненного.
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="rounded-full bg-amber-50 px-3 py-2 text-amber-800">
            Ожидают: {submitted}
          </span>
          <span className="rounded-full bg-indigo-50 px-3 py-2 text-indigo-800">
            В проверке: {inReview}
          </span>
        </div>
      </div>

      {message && <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</p>}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {reviews.length === 0 && (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-4 text-sm text-slate-600">
          В активной кампании нет профилей непосредственных подчиненных.
        </p>
      )}
      {returnable.length > 0 && (
        <BulkReturnBox
          busy={bulkActive}
          candidates={returnable}
          destination="сотрудникам"
          onReturnSelected={onBulkReturnSelected}
          onReturnUnit={onBulkReturnUnit}
        />
      )}

      <div className="mt-5 space-y-4">
        {reviews.map((review) => {
          const latest = review.latest_revision;
          const returnReason = review.review_events.find((event) => event.action === "returned")?.comment;
          const hrReturnReason = review.review_events.find((event) => event.action === "hr_returned")?.comment;
          const acting = activeProfileId === review.id;
          return (
            <article className="rounded-2xl border border-slate-200 p-4" key={review.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-950">{review.employee_name}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {review.position_title} / {review.unit_name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Маршрут: {review.route_path.join(" → ")} · Сейчас: {review.route_current}
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">
                  {statusLabels[review.workflow_status] ?? review.workflow_status}
                </span>
              </div>

              {latest ? (
                <div className="mt-4 rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Последняя сдача: версия {latest.revision_no} / {assistantUsageLabel(latest)}
                  </p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {review.questions.map((question) => (
                      <div key={question.key}>
                        <p className="text-xs font-semibold text-slate-500">{question.title}</p>
                        <p className="mt-1 text-sm text-slate-700">
                          {formatAnswer(question, latest.answers[question.key])}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  Сотрудник еще не отправил версию на проверку.
                </p>
              )}

              {review.can_take && (
                <button
                  className="mt-4 rounded-xl bg-indigo-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                  disabled={acting}
                  onClick={() => onTake(review.id)}
                  type="button"
                >
                  {acting ? "Беру в работу..." : "Взять на проверку"}
                </button>
              )}

              {review.can_decide && (
                <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
                  <p className="text-sm font-semibold text-indigo-950">
                    {review.returned_by_hr
                      ? "HR вернул профиль вам. Сотрудник пока не может его изменять."
                      : "Версия заблокирована для сотрудника до вашего решения."}
                  </p>
                  {review.returned_by_hr && hrReturnReason && (
                    <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      Причина HR: {hrReturnReason}
                    </p>
                  )}
                  <label className="mt-4 block text-sm font-medium text-slate-700">
                    Причина возврата на доработку
                    <textarea
                      aria-label={`Причина возврата: ${review.employee_name}`}
                      className="mt-2 min-h-20 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-700"
                      onChange={(event) =>
                        setReasons((existing) => ({ ...existing, [review.id]: event.target.value }))
                      }
                      placeholder="Укажите, что сотруднику необходимо уточнить."
                      value={reasons[review.id] ?? ""}
                    />
                  </label>
                  <button
                    className="mt-2 rounded-full border border-indigo-200 bg-white px-3 py-2 text-xs text-indigo-800"
                    onClick={() =>
                      setReasons((existing) => ({ ...existing, [review.id]: quickReason }))
                    }
                    type="button"
                  >
                    Подставить пример причины
                  </button>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-900 disabled:opacity-50"
                      disabled={acting || !(reasons[review.id] ?? "").trim()}
                      onClick={() => onReturn(review.id, reasons[review.id] ?? "")}
                      type="button"
                    >
                      Вернуть на доработку
                    </button>
                    <button
                      className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                      disabled={acting}
                      onClick={() => onVerify(review.id)}
                      type="button"
                    >
                      {review.returned_by_hr ? "Повторно подтвердить для HR" : "Подтвердить профиль"}
                    </button>
                  </div>
                </div>
              )}

              {review.workflow_status === "returned_for_revision" && returnReason && (
                <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Возвращено сотруднику: {returnReason}
                </p>
              )}
              {review.workflow_status === "manager_verified" && (
                <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  Последняя версия подтверждена и готова для следующего этапа HR.
                </p>
              )}
              {review.workflow_status === "hr_accepted" && (
                <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  HR принял профиль. Обработка в текущей кампании завершена.
                </p>
              )}

              {review.review_events.length > 0 && (
                <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
                  {review.review_events.slice(0, 3).map((event) => (
                    <p className="mt-1" key={event.id}>
                      {eventLabels[event.action] ?? event.action}, версия {event.revision_no},{" "}
                      {formatTimestamp(event.created_at)}
                    </p>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
