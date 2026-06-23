import type { Campaign } from "../../types";
import { statusLabels } from "./campaignConstants";

export function ParticipantsControls({ activeWave, isWork }: { activeWave: Campaign["waves"][number] | null; isWork: boolean }) {
  if (!activeWave) return null;

  if (isWork) {
    return (
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
    );
  }

  return (
    <>
      <p className="mt-3">
        В волне «{activeWave.name}» ожидаем заполнение: <strong>{activeWave.participants_expected}</strong> сотрудника(ов).
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(activeWave.status_counts ?? {}).map(([status, count]) => (
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
      </div>
    </>
  );
}
