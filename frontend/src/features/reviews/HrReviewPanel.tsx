import { useState } from "react";

import type { HrReviewProfile, ProfileQuestion, ProfileRevision } from "../../types";
import { BulkReturnBox } from "../../components/BulkReturnBox";

const statusLabels: Record<string, string> = {
  not_started: "Не начат",
  draft: "Черновик",
  submitted: "У руководителя",
  under_review: "Проверяется руководителем",
  returned_for_revision: "Возвращен сотруднику",
  manager_verified: "Ожидает решения HR",
  returned_by_hr: "Возвращен руководителю",
  hr_accepted: "Принят HR",
};

const quickReason =
  "Необходимо дополнительно уточнить соответствие заявленных обязанностей результатам подразделения.";

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

interface HrReviewPanelProps {
  reviews: HrReviewProfile[];
  error: string | null;
  message: string | null;
  activeProfileId: number | null;
  bulkActive: boolean;
  onAccept: (profileId: number) => void;
  onReturn: (profileId: number, reason: string) => void;
  onBulkReturnSelected: (profileIds: number[], reason: string) => void;
  onBulkReturnUnit: (orgUnitId: number, reason: string) => void;
}

export function HrReviewPanel({
  reviews,
  error,
  message,
  activeProfileId,
  bulkActive,
  onAccept,
  onReturn,
  onBulkReturnSelected,
  onBulkReturnUnit,
}: HrReviewPanelProps) {
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const waiting = reviews.filter((review) => review.workflow_status === "manager_verified");
  const accepted = reviews.filter((review) => review.workflow_status === "hr_accepted").length;

  return (
    <section className="rounded-3xl border border-emerald-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
            HR: финальная проверка
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">Принятие профилей</h2>
          <p className="mt-1 text-sm text-slate-500">
            HR принимает профиль или возвращает его на предыдущий этап доработки.
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="rounded-full bg-amber-50 px-3 py-2 text-amber-800">
            Ждут HR: {waiting.length}
          </span>
          <span className="rounded-full bg-emerald-50 px-3 py-2 text-emerald-800">
            Принято: {accepted}
          </span>
        </div>
      </div>

      {message && <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</p>}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {waiting.length === 0 && accepted === 0 && (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-4 text-sm text-slate-600">
          Профилей, подтвержденных руководителем, пока нет.
        </p>
      )}
      {waiting.length > 0 && (
        <BulkReturnBox
          busy={bulkActive}
          candidates={waiting}
          destination="на предыдущий этап"
          onReturnSelected={onBulkReturnSelected}
          onReturnUnit={onBulkReturnUnit}
        />
      )}

      <div className="mt-5 space-y-4">
        {reviews
          .filter((review) => review.can_decide || review.workflow_status === "hr_accepted" || review.workflow_status === "returned_by_hr")
          .map((review) => {
            const active = activeProfileId === review.id;
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

                {review.latest_revision && (
                  <div className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    <p>
                      Последняя версия: <strong>{review.latest_revision.revision_no}</strong>.{" "}
                      {assistantUsageLabel(review.latest_revision)}.
                    </p>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      {review.questions.map((question) => (
                        <div key={question.key}>
                          <p className="text-xs font-semibold text-slate-500">{question.title}</p>
                          <p className="mt-1 text-sm text-slate-700">
                            {formatAnswer(question, review.latest_revision?.answers[question.key])}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {review.can_decide && (
                  <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
                    <label className="text-sm font-medium text-slate-700">
                      Причина возврата на доработку
                      <textarea
                        aria-label={`Причина возврата HR: ${review.employee_name}`}
                        className="mt-2 min-h-20 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-700"
                        onChange={(event) =>
                          setReasons((existing) => ({ ...existing, [review.id]: event.target.value }))
                        }
                        placeholder="Заполняется только при возврате."
                        value={reasons[review.id] ?? ""}
                      />
                    </label>
                    <button
                      className="mt-2 rounded-full border border-emerald-200 bg-white px-3 py-2 text-xs text-emerald-800"
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
                        disabled={active || !(reasons[review.id] ?? "").trim()}
                        onClick={() => onReturn(review.id, reasons[review.id] ?? "")}
                        type="button"
                      >
                        Вернуть на доработку
                      </button>
                      <button
                        className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                        disabled={active}
                        onClick={() => onAccept(review.id)}
                        type="button"
                      >
                        Принять профиль
                      </button>
                    </div>
                  </div>
                )}
                {review.workflow_status === "returned_by_hr" && (
                  <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    Профиль возвращен руководителю для решения о дальнейшей доработке.
                  </p>
                )}
                {review.workflow_status === "hr_accepted" && (
                  <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                    Профиль принят HR и завершен в рамках текущей кампании.
                  </p>
                )}
              </article>
            );
          })}
      </div>
    </section>
  );
}
