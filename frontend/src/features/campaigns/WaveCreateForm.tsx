import { useEffect, useState, type FormEvent } from "react";

import type { Campaign } from "../../types";

export function WaveCreateForm({
  active,
  isCreatingWave,
  onCreateWave,
}: {
  active: Campaign | undefined;
  isCreatingWave: boolean;
  onCreateWave: (campaignId: number, name: string, dueAt: string | null) => void;
}) {
  const [waveName, setWaveName] = useState("");
  const [waveDueAt, setWaveDueAt] = useState("");

  useEffect(() => {
    if (!active) {
      setWaveName("");
      return;
    }
    setWaveName(`Волна ${active.waves.length + 1}`);
    setWaveDueAt("");
  }, [active?.id, active?.waves.length]);

  function submitWave(event: FormEvent) {
    event.preventDefault();
    if (!active) return;
    onCreateWave(active.id, waveName, waveDueAt || null);
  }

  if (!active) return null;

  return (
    <form className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={submitWave}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Волны кампании</p>
      <h3 className="mt-2 text-lg font-bold text-slate-950">Создать следующую волну</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_155px]">
        <input
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
          onChange={(event) => setWaveName(event.target.value)}
          placeholder="Название волны"
          required
          value={waveName}
        />
        <input
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
          onChange={(event) => setWaveDueAt(event.target.value)}
          type="date"
          value={waveDueAt}
        />
      </div>
      <button
        className="mt-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-900 disabled:opacity-50"
        disabled={isCreatingWave}
        type="submit"
      >
        {isCreatingWave ? "Создаю..." : "Создать волну"}
      </button>
    </form>
  );
}
