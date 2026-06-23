import type { StructureDeleteTarget } from "../app/types";

export function StructureDeleteConfirm({
  error,
  isDeleting,
  target,
  onCancel,
  onConfirm,
}: {
  error: string | null;
  isDeleting: boolean;
  target: StructureDeleteTarget | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!target) return null;
  const isPosition = target.kind === "position";

  return (
    <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 px-4">
      <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-700">
          HR: изменение структуры
        </p>
        <h3 className="mt-2 text-xl font-bold text-slate-950">
          {isPosition ? "Удалить штатную единицу?" : "Удалить сотрудника из структуры?"}
        </h3>
        <p className="mt-3 text-sm text-slate-600">
          {target.label}
        </p>
        {target.warning ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p className="font-semibold">Объект участвует в активной волне</p>
            <p className="mt-1">{target.warning}</p>
          </div>
        ) : (
          <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Если у объекта есть анкеты или участие в кампаниях, они будут удалены из отчетов после подтверждения.
          </p>
        )}
        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            disabled={isDeleting}
            onClick={onCancel}
            type="button"
          >
            Отмена
          </button>
          <button
            className="rounded-xl bg-red-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50"
            disabled={isDeleting}
            onClick={onConfirm}
            type="button"
          >
            {isDeleting ? "Удаляю..." : target.warning ? "Подтвердить удаление" : "Удалить"}
          </button>
        </div>
      </div>
    </div>
  );
}
