import { type FormEvent, useEffect, useMemo, useState } from "react";

import type { ManagerOption, NewEmployee, Position } from "../../types";

interface EmployeeModalProps {
  target: Position | null;
  managers: ManagerOption[];
  allowRoleSelection?: boolean;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (rows: NewEmployee[]) => void;
}

function emptyRow(managerAssignmentId: number | null): NewEmployee {
  return {
    full_name: "",
    email: "",
    fte: 1,
    system_role: "employee",
    is_hr: false,
    manager_assignment_id: managerAssignmentId,
  };
}

export function EmployeeModal({
  target,
  managers,
  allowRoleSelection = false,
  isSaving,
  error,
  onClose,
  onSave,
}: EmployeeModalProps) {
  const defaultManager =
    null;
  const [count, setCount] = useState(1);
  const [managerId, setManagerId] = useState<number | null>(defaultManager);
  const [managerQuery, setManagerQuery] = useState("");
  const [rows, setRows] = useState<NewEmployee[]>([emptyRow(defaultManager)]);
  const availableSlots =
    target && (target.vacancy_fte ?? 0) > 0
      ? Math.floor(target.vacancy_fte ?? 1)
      : Math.max(1, Math.floor(target?.approved_fte ?? 1));

  useEffect(() => {
    setCount(1);
    setManagerId(defaultManager);
    setManagerQuery("");
    setRows([emptyRow(defaultManager)]);
  }, [target?.id, defaultManager]);

  const filteredManagers = useMemo(() => {
    const query = managerQuery.trim().toLowerCase();
    if (!query) return managers;
    const matched = managers.filter((manager) => {
      const haystack = `${manager.employee_name} ${manager.position_title} ${manager.unit_name}`.toLowerCase();
      return haystack.includes(query);
    });
    if (managerId !== null && !matched.some((item) => item.assignment_id === managerId)) {
      const selected = managers.find((item) => item.assignment_id === managerId);
      if (selected) return [selected, ...matched];
    }
    return matched;
  }, [managerId, managerQuery, managers]);

  const rowsAreValid = rows.every((row) => row.full_name.trim() && row.email.trim());

  if (!target) return null;

  function resize(next: number) {
    const safeCount = Math.max(1, Math.min(next, availableSlots));
    setCount(safeCount);
    setRows((existing) =>
      Array.from({ length: safeCount }, (_, index) => existing[index] ?? emptyRow(managerId)),
    );
  }

  function chooseManager(next: number | null) {
    setManagerId(next);
    setRows((existing) =>
      existing.map((row) => ({
        ...row,
        manager_assignment_id: next,
      })),
    );
  }

  function updateRow(index: number, patch: Partial<NewEmployee>) {
    setRows((existing) =>
      existing.map((row, current) => (current === index ? { ...row, ...patch } : row)),
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave(rows);
  }

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-slate-950/40 px-4">
      <form
        className="max-h-[92vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl"
        onSubmit={submit}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              HR: добавление сотрудников
            </p>
            <h3 className="mt-1 text-xl font-bold text-slate-950">{target.title}</h3>
            <p className="mt-1 text-sm text-slate-500">
              Доступно ставок: {target.vacancy_fte}. Все новые записи сохраняются в выбранном контуре.
            </p>
          </div>
          <button className="rounded-xl px-3 py-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>

        <div className="mt-6 grid gap-4 rounded-2xl bg-slate-50 p-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">
            Сколько людей добавить
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              max={availableSlots}
              min={1}
              onChange={(event) => resize(Number(event.target.value))}
              type="number"
              value={count}
            />
          </label>
          <div className="text-sm font-medium text-slate-700">
            <div className="flex items-center justify-between gap-3">
              <span>Непосредственный руководитель</span>
              {managerId !== null && (
                <button
                  className="text-xs font-semibold text-blue-700 hover:text-blue-900"
                  onClick={() => chooseManager(null)}
                  type="button"
                >
                  Сбросить выбор
                </button>
              )}
            </div>
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none transition focus:border-blue-700 focus:ring-4 focus:ring-blue-100"
              onChange={(event) => setManagerQuery(event.target.value)}
              placeholder="Поиск по ФИО, должности или подразделению"
              value={managerQuery}
            />
            <div className="mt-3 max-h-56 overflow-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
              {filteredManagers.length === 0 ? (
                <p className="px-3 py-4 text-sm text-slate-500">Ничего не найдено.</p>
              ) : (
                filteredManagers.map((manager) => {
                  const selected = manager.assignment_id === managerId;
                  return (
                    <button
                      className={`flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left transition ${
                        selected ? "bg-blue-50 ring-1 ring-inset ring-blue-200" : "hover:bg-slate-50"
                      }`}
                      key={manager.assignment_id}
                      onClick={() => chooseManager(manager.assignment_id)}
                      type="button"
                    >
                      <span className={`mt-1 h-2.5 w-2.5 rounded-full ${selected ? "bg-blue-700" : "bg-slate-300"}`} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold text-slate-900">
                          {manager.employee_name}
                        </span>
                        <span className="block truncate text-sm text-slate-600">
                          {manager.position_title}
                        </span>
                        <span className="block truncate text-xs text-slate-500">{manager.unit_name}</span>
                      </span>
                      {selected && (
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800">
                          Выбран
                        </span>
                      )}
                    </button>
                  );
                })
              )}
            </div>
            <span className="mt-2 block text-xs font-normal text-slate-500">
              Если руководитель не выбран, система попробует вычислить его по иерархии. Если
              начальник не найден, анкета уйдет сразу на финальную проверку HR.
            </span>
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {rows.map((row, index) => (
            <div
              className={`grid gap-3 rounded-xl border border-slate-200 p-3 ${
                allowRoleSelection
                  ? "md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_110px_150px_120px]"
                  : "md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_110px_120px]"
              }`}
              key={index}
            >
              <input
                aria-label={`ФИО сотрудника ${index + 1}`}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                onChange={(event) => updateRow(index, { full_name: event.target.value })}
                placeholder="ФИО"
                required
                value={row.full_name}
              />
              <input
                aria-label={`Email сотрудника ${index + 1}`}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                onChange={(event) => updateRow(index, { email: event.target.value })}
                placeholder="name@example.local"
                required
                type="email"
                value={row.email}
              />
              <label className="relative block">
                <span className="pointer-events-none absolute left-3 top-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                  Ставка
                </span>
                <input
                  aria-label={`Ставка сотрудника ${index + 1}`}
                  className="h-full min-h-[42px] w-full rounded-lg border border-slate-200 px-3 pb-1 pt-5 text-sm outline-none focus:border-blue-700"
                  min={0.1}
                  onChange={(event) => updateRow(index, { fte: Number(event.target.value) })}
                  step={0.1}
                  type="number"
                  value={row.fte}
                />
              </label>
              {allowRoleSelection && (
                <select
                  aria-label={`Роль сотрудника ${index + 1}`}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-700"
                  onChange={(event) =>
                    updateRow(index, {
                      system_role: event.target.value as "employee" | "manager",
                      manager_assignment_id:
                        event.target.value === "manager" ? null : row.manager_assignment_id ?? managerId,
                    })
                  }
                  value={row.system_role}
                >
                  <option value="employee">Сотрудник</option>
                  <option value="manager">Руководитель</option>
                </select>
              )}
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700">
                <input
                  checked={row.is_hr}
                  className="h-4 w-4 accent-blue-900"
                  onChange={(event) => updateRow(index, { is_hr: event.target.checked })}
                  type="checkbox"
                />
                HR
              </label>
            </div>
          ))}
        </div>

        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium" onClick={onClose} type="button">
            Отмена
          </button>
          <button
            className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            disabled={isSaving || !rowsAreValid}
            type="submit"
          >
            {isSaving ? "Сохраняю..." : `Добавить ${count} сотрудника(ов)`}
          </button>
        </div>
      </form>
    </div>
  );
}
