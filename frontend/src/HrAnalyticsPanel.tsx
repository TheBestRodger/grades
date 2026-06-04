import type { HrAnalytics } from "./types";

interface HrAnalyticsPanelProps {
  analytics: HrAnalytics | null;
  error: string | null;
  isLoading: boolean;
}

function KpiCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-blue-700">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  );
}

export function HrAnalyticsPanel({ analytics, error, isLoading }: HrAnalyticsPanelProps) {
  if (isLoading) {
    return <p className="text-sm text-slate-500">Считаю показатели аналитики...</p>;
  }
  if (error) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }
  if (!analytics) return null;
  const coverage = Object.values(analytics.documents.coverage);

  return (
    <section className="space-y-5">
      <div className="rounded-3xl border border-blue-100 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">HR: аналитика</p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-950">Единый dashboard профилирования</h2>
            <p className="mt-1 text-sm text-slate-500">{analytics.note}</p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-2 text-sm font-medium text-blue-800">
            {analytics.scope === "demo" ? "Текущий контур" : "Рабочий контур"}
          </span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Кампании"
          note={`Активных: ${analytics.active_campaigns}`}
          value={String(analytics.campaigns_total)}
        />
        <KpiCard
          label="Ожидаются профили"
          note={`Сданы версии: ${analytics.profiles_with_revisions}`}
          value={String(analytics.profiles_expected)}
        />
        <KpiCard
          label="Средний прогресс"
          note={`Принято HR: ${analytics.accepted_profiles}`}
          value={`${Math.round(analytics.average_progress_percent)}%`}
        />
        <KpiCard
          label="Возвраты"
          note={`Событий возврата: ${analytics.return_events}`}
          value={String(analytics.returned_profiles)}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-bold text-slate-950">Воронка статусов</h3>
          <p className="mt-1 text-sm text-slate-500">Текущий статус каждого включенного профиля.</p>
          <div className="mt-4 space-y-3">
            {analytics.funnel.map((row) => (
              <div key={row.status}>
                <div className="mb-1 flex justify-between text-sm text-slate-700">
                  <span>{row.label}</span>
                  <span className="font-semibold">{row.count} / {analytics.profiles_expected}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-blue-700"
                    style={{ width: `${Math.min(100, row.percent)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-bold text-slate-950">Версии и документы</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <KpiCard label="Редакции сдачи" note={`Повторно сдавали: ${analytics.resubmitted_profiles}`} value={String(analytics.revision_count)} />
            <KpiCard label="Документы" note={`Подтверждено: ${analytics.documents.confirmed_documents}`} value={String(analytics.documents.documents_total)} />
          </div>
          <div className="mt-4 space-y-3">
            {coverage.map((item) => (
              <div className="rounded-xl bg-slate-50 px-3 py-2" key={item.label}>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-700">{item.label}</span>
                  <strong>{Math.round(item.percent)}%</strong>
                </div>
                <p className="mt-1 text-xs text-slate-500">Связано: {item.covered} / {item.total}; пробелов: {item.missing}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-bold text-slate-950">Прогресс по подразделениям</h3>
        {analytics.units.length === 0 ? (
          <p className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            В этом контуре пока нет включенных участников с профилями.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="pb-3 pr-4">Подразделение</th>
                  <th className="pb-3 pr-4">Профили</th>
                  <th className="pb-3 pr-4">Прогресс</th>
                  <th className="pb-3 pr-4">Принято HR</th>
                  <th className="pb-3">С возвратами</th>
                </tr>
              </thead>
              <tbody>
                {analytics.units.map((unit) => (
                  <tr className="border-t border-slate-100 text-slate-700" key={unit.unit_id}>
                    <td className="py-3 pr-4 font-medium text-slate-950">{unit.unit_name}</td>
                    <td className="py-3 pr-4">{unit.profiles_expected}</td>
                    <td className="py-3 pr-4">{Math.round(unit.average_progress_percent)}%</td>
                    <td className="py-3 pr-4">{unit.accepted}</td>
                    <td className="py-3">{unit.returned}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
