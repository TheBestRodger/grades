import type { Campaign } from "../../types";

export function CredentialsExportPanel({
  active,
  activeWave,
  credentialsFileReady,
  isPreparingCredentials,
  onPrepareCredentialsFile,
  onDownloadCredentials,
}: {
  active: Campaign | undefined;
  activeWave: Campaign["waves"][number] | null;
  credentialsFileReady: boolean;
  isPreparingCredentials: boolean;
  onPrepareCredentialsFile: () => void;
  onDownloadCredentials: () => void;
}) {
  const hasWaveParticipants = Boolean(activeWave && activeWave.participants_expected > 0);
  return (
    <div className="mt-4 rounded-xl border border-emerald-100 bg-white px-3 py-3 text-sm text-emerald-950">
      <p className="font-semibold">Доступы участников</p>
      <p className="mt-1 text-xs text-emerald-800">
        Участников в выбранной волне: <strong>{activeWave?.participants_expected ?? 0}</strong>.
        Файл формируется для новых участников.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 disabled:opacity-50"
          disabled={!active || !activeWave || !hasWaveParticipants || isPreparingCredentials}
          onClick={onPrepareCredentialsFile}
          type="button"
        >
          {isPreparingCredentials ? "Формирую..." : "Сформировать доступы для новых участников"}
        </button>
        {credentialsFileReady && (
          <button
            className="rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white"
            onClick={onDownloadCredentials}
            type="button"
          >
            Скачать XLSX
          </button>
        )}
      </div>
      {!hasWaveParticipants && (
        <p className="mt-2 text-xs text-emerald-800">Сначала добавьте участников в выбранную волну.</p>
      )}
    </div>
  );
}
