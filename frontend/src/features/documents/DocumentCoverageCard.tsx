import type { DocumentCoverageItem } from "../../types";

export function DocumentCoverageCard({ item }: { item: DocumentCoverageItem }) {
  return (
    <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700">{item.label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{item.covered} / {item.total}</p>
        </div>
        <span className="rounded-full bg-white px-3 py-1.5 text-sm font-semibold text-indigo-900">
          {Math.round(item.percent)}%
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-600">
        Без подтвержденной связи: <strong>{item.missing}</strong>
      </p>
    </div>
  );
}
