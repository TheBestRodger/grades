import { useMemo, useState } from "react";

interface BulkReturnCandidate {
  id: number;
  employee_name: string;
  org_unit_id: number;
  unit_name: string;
}

interface BulkReturnBoxProps {
  candidates: BulkReturnCandidate[];
  busy: boolean;
  destination: string;
  onReturnSelected: (profileIds: number[], reason: string) => void;
  onReturnUnit: (orgUnitId: number, reason: string) => void;
}

const quickReason =
  "Нужно одновременно уточнить результаты и измеримые критерии в выбранных профилях.";

export function BulkReturnBox({
  candidates,
  busy,
  destination,
  onReturnSelected,
  onReturnUnit,
}: BulkReturnBoxProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [unitId, setUnitId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const candidateIds = new Set(candidates.map((candidate) => candidate.id));
  const activeSelectedIds = selectedIds.filter((id) => candidateIds.has(id));
  const units = useMemo(
    () =>
      Array.from(
        new Map(candidates.map((candidate) => [candidate.org_unit_id, candidate.unit_name])),
      ),
    [candidates],
  );
  const reasonReady = reason.trim().length >= 5;

  function toggleProfile(profileId: number) {
    setSelectedIds((existing) =>
      existing.includes(profileId)
        ? existing.filter((id) => id !== profileId)
        : [...existing, profileId],
    );
  }

  return (
    <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50/50 p-4">
      <h3 className="font-bold text-slate-950">Массовый возврат</h3>
      <p className="mt-1 text-sm text-slate-600">
        Выберите профили или подразделение. Одна причина будет записана для каждого возврата {destination}.
      </p>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-xl bg-white p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-800">Отдельные сотрудники</p>
            <button
              className="text-xs font-semibold text-indigo-700"
              onClick={() => setSelectedIds(candidates.map((candidate) => candidate.id))}
              type="button"
            >
              Выбрать всех
            </button>
          </div>
          <div className="mt-3 max-h-36 space-y-2 overflow-auto">
            {candidates.map((candidate) => (
              <label className="flex items-center gap-2 text-sm text-slate-700" key={candidate.id}>
                <input
                  checked={activeSelectedIds.includes(candidate.id)}
                  onChange={() => toggleProfile(candidate.id)}
                  type="checkbox"
                />
                <span>{candidate.employee_name} / {candidate.unit_name}</span>
              </label>
            ))}
          </div>
          <button
            className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 disabled:opacity-50"
            disabled={busy || !reasonReady || activeSelectedIds.length === 0}
            onClick={() => onReturnSelected(activeSelectedIds, reason)}
            type="button"
          >
            Вернуть выбранных ({activeSelectedIds.length})
          </button>
        </div>
        <div className="rounded-xl bg-white p-3">
          <p className="text-sm font-semibold text-slate-800">Все доступные в подразделении</p>
          <select
            className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            onChange={(event) => setUnitId(event.target.value ? Number(event.target.value) : null)}
            value={unitId ?? ""}
          >
            <option value="">Выберите подразделение</option>
            {units.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <button
            className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 disabled:opacity-50"
            disabled={busy || !reasonReady || unitId === null}
            onClick={() => unitId !== null && onReturnUnit(unitId, reason)}
            type="button"
          >
            Вернуть подразделение
          </button>
        </div>
      </div>
      <label className="mt-4 block text-sm font-medium text-slate-700">
        Общая причина возврата
        <textarea
          className="mt-2 min-h-20 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-amber-500"
          onChange={(event) => setReason(event.target.value)}
          placeholder="Причина будет сохранена в истории каждого выбранного профиля."
          value={reason}
        />
      </label>
      <button
        className="mt-2 rounded-full border border-amber-200 bg-white px-3 py-2 text-xs text-amber-900"
        onClick={() => setReason(quickReason)}
        type="button"
      >
        Подставить пример причины
      </button>
    </div>
  );
}
