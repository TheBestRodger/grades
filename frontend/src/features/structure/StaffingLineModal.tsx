import { type FormEvent, useEffect, useState } from "react";

import type { OrgNode, WorkStaffingLineInput } from "../../types";

interface StaffingLineModalProps {
  target: OrgNode | null;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (payload: WorkStaffingLineInput) => void;
}

export function StaffingLineModal({
  target,
  isSaving,
  error,
  onClose,
  onSave,
}: StaffingLineModalProps) {
  const [title, setTitle] = useState("");
  const [approvedFte, setApprovedFte] = useState(1);

  useEffect(() => {
    setTitle("");
    setApprovedFte(1);
  }, [target?.id]);

  if (!target) return null;

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({ title, approved_fte: approvedFte, employees: [] });
  }

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-slate-950/40 px-4">
      <form
        className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl"
        onSubmit={submit}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              HR: штатная единица
            </p>
            <h3 className="mt-1 text-xl font-bold text-slate-950">{target.name}</h3>
            <p className="mt-1 text-sm text-slate-500">
              Новая штатная строка появится в этом подразделении. Людей можно добавить после создания.
            </p>
          </div>
          <button className="rounded-xl px-3 py-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>

        <div className="mt-6 grid gap-4 rounded-2xl bg-slate-50 p-4 md:grid-cols-[1fr_160px]">
          <label className="text-sm font-medium text-slate-700">
            Должность
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              minLength={2}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Например: Специалист отдела"
              required
              value={title}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Ставок
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              min={0.1}
              onChange={(event) => setApprovedFte(Number(event.target.value))}
              required
              step={0.1}
              type="number"
              value={approvedFte}
            />
          </label>
        </div>

        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium" onClick={onClose} type="button">
            Отмена
          </button>
          <button
            className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            disabled={isSaving || title.trim().length < 2 || approvedFte <= 0}
            type="submit"
          >
            {isSaving ? "Создаю..." : "Создать штатную единицу"}
          </button>
        </div>
      </form>
    </div>
  );
}
