import type { Campaign } from "../../types";
import type { WaveAction } from "./types";

export function WaveActionConfirmModal({
  action,
  activeWave,
  isConfirming,
  onCancel,
  onConfirm,
}: {
  action: WaveAction;
  activeWave: Campaign["waves"][number] | null;
  isConfirming: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const confirmTitle = action === "launch" ? "Запустить волну?" : "Взять волну в редакцию?";
  const confirmText =
    action === "launch"
      ? `Будет запущена волна «${activeWave?.name ?? ""}». Проверьте выбранные подразделения и участников перед запуском.`
      : `Волна «${activeWave?.name ?? ""}» перейдет в режим редактирования. После этого состав участников можно будет изменить.`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Подтверждение действия</p>
        <h3 className="mt-3 text-2xl font-bold text-slate-950">{confirmTitle}</h3>
        <p className="mt-3 text-base leading-7 text-slate-600">{confirmText}</p>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700"
            onClick={onCancel}
            type="button"
          >
            Отмена
          </button>
          <button
            className="rounded-xl bg-blue-900 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
            disabled={isConfirming}
            onClick={onConfirm}
            type="button"
          >
            {action === "launch" ? "Запустить волну" : "Взять в редакцию"}
          </button>
        </div>
      </div>
    </div>
  );
}
