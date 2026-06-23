import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import type { Campaign } from "../../types";
import { CampaignList } from "./CampaignList";

export function CampaignCreateForm({
  isWork,
  campaigns,
  activeCampaignId,
  isCreating,
  onActiveChange,
  onCreate,
  children,
}: {
  isWork: boolean;
  campaigns: Campaign[];
  activeCampaignId: number | null;
  isCreating: boolean;
  onActiveChange: (id: number) => void;
  onCreate: (name: string, dueAt: string | null) => void;
  children?: ReactNode;
}) {
  const [name, setName] = useState(isWork ? "Рабочая кампания профилирования" : "Кампания профилирования");
  const [dueAt, setDueAt] = useState("");

  useEffect(() => {
    setName(isWork ? "Рабочая кампания профилирования" : "Кампания профилирования");
  }, [isWork]);

  function submit(event: FormEvent) {
    event.preventDefault();
    onCreate(name, dueAt || null);
  }

  return (
    <form className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={submit}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
        HR: {isWork ? "рабочая кампания" : "кампания"}
      </p>
      <h3 className="mt-2 text-lg font-bold text-slate-950">Назначить профилирование</h3>
      <p className="mt-1 text-sm text-slate-500">
        Кампания - общий цикл профилирования. Волны внутри кампании позволяют проходить
        подразделения этапами.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_155px]">
        <input
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
          onChange={(event) => setName(event.target.value)}
          placeholder="Название кампании"
          required
          value={name}
        />
        <input
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-700"
          onChange={(event) => setDueAt(event.target.value)}
          type="date"
          value={dueAt}
        />
      </div>
      <button
        className="mt-4 rounded-xl bg-blue-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        disabled={isCreating}
        type="submit"
      >
        {isCreating ? "Создаю..." : "Создать кампанию"}
      </button>
      <CampaignList
        activeCampaignId={activeCampaignId}
        campaigns={campaigns}
        isWork={isWork}
        onActiveChange={onActiveChange}
      />
      {children}
    </form>
  );
}
