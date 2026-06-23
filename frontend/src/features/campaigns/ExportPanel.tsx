import type { CampaignPanelProps } from "./types";

export function ExportPanel({ onExport }: { onExport: CampaignPanelProps["onExport"] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Выгрузки</p>
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
    </div>
  );
}
