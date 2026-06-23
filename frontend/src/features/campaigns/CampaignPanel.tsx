import { useState } from "react";

import { AuditPanel } from "./AuditPanel";
import { CampaignCreateForm } from "./CampaignCreateForm";
import { ExportPanel } from "./ExportPanel";
import type { CampaignPanelProps, WaveAction } from "./types";
import { WaveActionConfirmModal } from "./WaveActionConfirmModal";
import { WaveControls } from "./WaveControls";
import { WaveCreateForm } from "./WaveCreateForm";

export function CampaignPanel({
  scope,
  campaigns,
  activeCampaignId,
  activeWaveId,
  events,
  message,
  error,
  isCreating,
  isCreatingWave,
  isLaunchingWave,
  isEditingWave,
  credentialsFileReady,
  isPreparingCredentials,
  onActiveChange,
  onWaveChange,
  onCreate,
  onCreateWave,
  onLaunchWave,
  onEditWave,
  onExport,
  onPrepareCredentialsFile,
  onDownloadCredentials,
}: CampaignPanelProps) {
  const isWork = scope === "work";
  const [confirmWaveAction, setConfirmWaveAction] = useState<WaveAction | null>(null);
  const active = campaigns.find((campaign) => campaign.id === activeCampaignId);
  const activeWave =
    active?.waves.find((wave) => wave.id === activeWaveId) ??
    active?.waves.find((wave) => wave.id === active?.active_wave_id) ??
    active?.waves[0] ??
    null;
  const isConfirmingWaveAction = confirmWaveAction === "launch" ? isLaunchingWave : isEditingWave;

  function confirmWaveChange() {
    if (!active || !activeWave || !confirmWaveAction) return;
    if (confirmWaveAction === "launch") {
      onLaunchWave(active.id, activeWave.id);
    } else {
      onEditWave(active.id, activeWave.id);
    }
    setConfirmWaveAction(null);
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
      <div className="space-y-5">
        <CampaignCreateForm
          activeCampaignId={activeCampaignId}
          campaigns={campaigns}
          isCreating={isCreating}
          isWork={isWork}
          onActiveChange={onActiveChange}
          onCreate={onCreate}
        >
          <WaveControls
            active={active}
            activeWave={activeWave}
            activeWaveId={activeWaveId}
            credentialsFileReady={credentialsFileReady}
            isEditingWave={isEditingWave}
            isLaunchingWave={isLaunchingWave}
            isPreparingCredentials={isPreparingCredentials}
            isWork={isWork}
            onDownloadCredentials={onDownloadCredentials}
            onPrepareCredentialsFile={onPrepareCredentialsFile}
            onRequestWaveAction={setConfirmWaveAction}
            onWaveChange={onWaveChange}
          />
          {message && <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>}
          {error && <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        </CampaignCreateForm>
        {!isWork && <ExportPanel onExport={onExport} />}
        <WaveCreateForm active={active} isCreatingWave={isCreatingWave} onCreateWave={onCreateWave} />
      </div>

      <AuditPanel events={events} />
      {confirmWaveAction && (
        <WaveActionConfirmModal
          action={confirmWaveAction}
          activeWave={activeWave}
          isConfirming={isConfirmingWaveAction}
          onCancel={() => setConfirmWaveAction(null)}
          onConfirm={confirmWaveChange}
        />
      )}
    </section>
  );
}
