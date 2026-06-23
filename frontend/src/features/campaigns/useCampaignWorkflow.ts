import { useEffect, useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

import { issueWaveCredentialsExport } from "../../api";
import type { DataScope } from "../../app/navigation";
import { invalidateHrViews } from "../../shared/invalidation";
import type { Campaign, OrgNode } from "../../types";
import { useActiveCampaignSelection } from "./useActiveCampaignSelection";
import { useCampaignMutations } from "./useCampaignMutations";

interface UseCampaignWorkflowOptions {
  campaignsData: Campaign[] | undefined;
  dataScope: DataScope;
  queryClient: QueryClient;
  selectedUserId: number | null;
  setExportError: (message: string | null) => void;
  setOperationMessage: (message: string | null) => void;
}

export function useCampaignWorkflow({
  campaignsData,
  dataScope,
  queryClient,
  selectedUserId,
  setExportError,
  setOperationMessage,
}: UseCampaignWorkflowOptions) {
  const [includingUnitId, setIncludingUnitId] = useState<number | null>(null);
  const [excludingUnitId, setExcludingUnitId] = useState<number | null>(null);
  const [changingAssignmentId, setChangingAssignmentId] = useState<number | null>(null);
  const [credentialsFileBlob, setCredentialsFileBlob] = useState<Blob | null>(null);
  const [preparingCredentials, setPreparingCredentials] = useState(false);

  const {
    activeCampaignForTree,
    activeCampaignId,
    activeWave,
    activeWaveId,
    setActiveCampaignId,
    setActiveWaveId,
  } = useActiveCampaignSelection(campaignsData);

  useEffect(() => {
    setCredentialsFileBlob(null);
  }, [activeCampaignId, activeWaveId]);

  async function refreshHrViews() {
    await invalidateHrViews(queryClient, selectedUserId, dataScope);
  }

  const {
    createCampaignMutation,
    createWaveMutation,
    editWaveMutation,
    launchWaveMutation,
    includeMutation,
    excludeMutation,
    campaignAssignmentMutation,
  } = useCampaignMutations({
    selectedUserId,
    dataScope,
    getActiveCampaignId: () => activeCampaignId!,
    getActiveWaveId: () => activeWaveId!,
    onCreateCampaignSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.active_wave_id);
      setOperationMessage(`Кампания «${campaign.name}» создана. Теперь выберите ветку.`);
      await refreshHrViews();
    },
    onCreateWaveSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.new_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`В кампании «${campaign.name}» создана волна «${campaign.new_wave_name}».`);
      await refreshHrViews();
    },
    onLaunchWaveSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.launched_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`Волна «${campaign.launched_wave_name}» запущена.`);
      await refreshHrViews();
    },
    onEditWaveSuccess: async (campaign) => {
      setActiveCampaignId(campaign.id);
      setActiveWaveId(campaign.editing_wave_id ?? campaign.active_wave_id);
      setOperationMessage(`Волна «${campaign.editing_wave_name}» взята в редакцию.`);
      await refreshHrViews();
    },
    onIncludeSuccess: async (campaign) => {
      setOperationMessage(
        campaign.scope === "work"
          ? `Ветка «${campaign.included_unit_name}» включена в волну «${campaign.included_wave_name}»: новых участников ${campaign.new_participants ?? 0}.`
          : `Ветка «${campaign.included_unit_name}» включена в волну «${campaign.included_wave_name}»: новых участников ${campaign.new_participants}.`,
      );
      setIncludingUnitId(null);
      await refreshHrViews();
    },
    onIncludeError: () => setIncludingUnitId(null),
    onExcludeSuccess: async (campaign) => {
      setOperationMessage(
        campaign.scope === "work"
          ? `Ветка «${campaign.excluded_unit_name}» снята из плана волны «${campaign.excluded_wave_name}».`
          : `Ветка «${campaign.excluded_unit_name}» выключена из волны «${campaign.excluded_wave_name}»: участников снято ${campaign.excluded_participants}.`,
      );
      setExcludingUnitId(null);
      await refreshHrViews();
    },
    onExcludeError: () => setExcludingUnitId(null),
    onAssignmentSuccess: async (campaign) => {
      setOperationMessage(
        campaign.participant_action === "include"
          ? "Назначение включено в выбранную волну."
          : "Назначение исключено из выбранной волны.",
      );
      setChangingAssignmentId(null);
      await refreshHrViews();
    },
    onAssignmentError: () => setChangingAssignmentId(null),
  });

  function includeUnit(unit: OrgNode) {
    if (!activeCampaignId || !activeWaveId) return;
    setIncludingUnitId(unit.id);
    includeMutation.mutate({ campaignId: activeCampaignId, unitId: unit.id, waveId: activeWaveId });
  }

  function excludeUnit(unit: OrgNode) {
    if (!activeCampaignId || !activeWaveId) return;
    setExcludingUnitId(unit.id);
    excludeMutation.mutate({ campaignId: activeCampaignId, unitId: unit.id, waveId: activeWaveId });
  }

  function setAssignmentParticipation(assignmentId: number, included: boolean) {
    if (!activeCampaignId || !activeWaveId) return;
    setChangingAssignmentId(assignmentId);
    campaignAssignmentMutation.mutate({ assignmentId, included });
  }

  async function prepareIssuedCredentialsFile() {
    if (!selectedUserId || !activeCampaignId || !activeWaveId) {
      setExportError("Выберите кампанию и волну для формирования доступов.");
      return;
    }
    setPreparingCredentials(true);
    setExportError(null);
    setCredentialsFileBlob(null);
    try {
      const blob = await issueWaveCredentialsExport(selectedUserId, dataScope, activeCampaignId, activeWaveId);
      setCredentialsFileBlob(blob);
      setOperationMessage("Файл с доступами для новых участников сформирован.");
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Не удалось сформировать доступы.");
    } finally {
      setPreparingCredentials(false);
    }
  }

  function exportIssuedCredentials() {
    if (!credentialsFileBlob) return;
    const url = window.URL.createObjectURL(credentialsFileBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "credentials_new_participants.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return {
    activeCampaignForTree,
    activeCampaignId,
    activeWave,
    activeWaveId,
    campaignAssignmentMutation,
    changingAssignmentId,
    createCampaignMutation,
    createWaveMutation,
    credentialsFileBlob,
    editWaveMutation,
    excludeMutation,
    excludeUnit,
    excludingUnitId,
    exportIssuedCredentials,
    includeMutation,
    includeUnit,
    includingUnitId,
    launchWaveMutation,
    prepareIssuedCredentialsFile,
    preparingCredentials,
    setActiveCampaignId,
    setActiveWaveId,
    setAssignmentParticipation,
    setCredentialsFileBlob,
  };
}
