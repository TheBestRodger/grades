import type { EmployeeProfile } from "../../types";
import { assistantUsageLabel, submittedAt } from "./answerStatus";

interface ProfileHistoryProps {
  profile: EmployeeProfile;
}

export function ProfileHistory({ profile }: ProfileHistoryProps) {
  return (
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
                          ? "Возвращено HR"
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
  );
}
