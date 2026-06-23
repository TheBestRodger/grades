import { useState } from "react";

import type { DemoResetResult } from "../../types";

interface DemoResetPanelProps {
  isResetting: boolean;
  error: string | null;
  result: DemoResetResult | null;
  onReset: () => void;
}

export function DemoResetPanel({ isResetting, error, result, onReset }: DemoResetPanelProps) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <section className="rounded-2xl border border-amber-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
        HR: сброс контура
      </p>
      <h3 className="mt-2 text-lg font-bold text-slate-950">Сбросить текущий контур</h3>
      <p className="mt-1 text-sm text-slate-600">
        Будут заново созданы пользователи, кампания, профили и документы выбранного контура.
        Рабочий контур, импортированное ШР, рабочие сотрудники и рабочие документы не удаляются.
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm text-slate-700">
        <input
          checked={confirmed}
          className="mt-1"
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        <span>Понимаю, что текущие черновики, кампании и аудит выбранного контура будут пересозданы.</span>
      </label>
      <button
        className="mt-4 rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        disabled={!confirmed || isResetting}
        onClick={onReset}
        type="button"
      >
        {isResetting ? "Сбрасываю..." : "Сбросить контур"}
      </button>
      {result && (
        <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Контур пересоздан. Рабочий контур {result.work_unchanged ? "не изменился" : "требует проверки"}.
        </p>
      )}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
    </section>
  );
}
