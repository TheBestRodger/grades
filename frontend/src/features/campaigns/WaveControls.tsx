import type { Campaign } from "../../types";
import { waveStatusTone } from "./campaignConstants";
import { CredentialsExportPanel } from "./CredentialsExportPanel";
import { ParticipantsControls } from "./ParticipantsControls";
import type { WaveAction } from "./types";

export function WaveControls({
  active,
  activeWave,
  isWork,
  activeWaveId,
  isLaunchingWave,
  isEditingWave,
  credentialsFileReady,
  isPreparingCredentials,
  onWaveChange,
  onRequestWaveAction,
  onPrepareCredentialsFile,
  onDownloadCredentials,
}: {
  active: Campaign | undefined;
  activeWave: Campaign["waves"][number] | null;
  isWork: boolean;
  activeWaveId: number | null;
  isLaunchingWave: boolean;
  isEditingWave: boolean;
  credentialsFileReady: boolean;
  isPreparingCredentials: boolean;
  onWaveChange: (id: number) => void;
  onRequestWaveAction: (action: WaveAction) => void;
  onPrepareCredentialsFile: () => void;
  onDownloadCredentials: () => void;
}) {
  if (!active) return null;

  return (
    <div className="mt-3 rounded-xl bg-blue-50 px-3 py-3 text-sm text-blue-900">
      <p>
        Выберите волну, затем включите подразделение целиком или отдельных сотрудников.
        Изменения применяются только к выбранной волне
        {isWork ? ": выбор подразделения дополнительно сохраняет охват ШР." : "."}
      </p>
      <label className="mt-3 block text-sm font-medium text-blue-950">
        Активная волна
        <select
          className="mt-2 block w-full rounded-xl border border-blue-100 bg-white px-3 py-2 text-sm"
          onChange={(event) => onWaveChange(Number(event.target.value))}
          value={activeWave?.id ?? activeWaveId ?? ""}
        >
          {active.waves.map((wave) => (
            <option key={wave.id} value={wave.id}>
              {wave.name} / {wave.status_label} / {isWork
                ? `участников: ${wave.participants_expected}, подразделений: ${wave.selected_units_count}`
                : `ожидаем: ${wave.participants_expected}`}
            </option>
          ))}
        </select>
      </label>
      {activeWave && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${waveStatusTone[activeWave.status] ?? "bg-slate-100 text-slate-700"}`}>
            {activeWave.status_label}
          </span>
          <button
            className="rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={
              !activeWave.can_launch ||
              isLaunchingWave
            }
            onClick={() => onRequestWaveAction("launch")}
            type="button"
          >
            {isLaunchingWave ? "Запускаю..." : "Запустить волну"}
          </button>
          <button
            className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={activeWave.status !== "active" || isEditingWave}
            onClick={() => onRequestWaveAction("edit")}
            type="button"
          >
            {isEditingWave ? "Открываю редакцию..." : "Взять в редакцию"}
          </button>
          {!activeWave.can_edit && (
            <span className="text-xs text-slate-500">Состав запущенной волны заблокирован для изменений.</span>
          )}
        </div>
      )}
      <ParticipantsControls activeWave={activeWave} isWork={isWork} />
      <CredentialsExportPanel
        active={active}
        activeWave={activeWave}
        credentialsFileReady={credentialsFileReady}
        isPreparingCredentials={isPreparingCredentials}
        onDownloadCredentials={onDownloadCredentials}
        onPrepareCredentialsFile={onPrepareCredentialsFile}
      />
    </div>
  );
}
