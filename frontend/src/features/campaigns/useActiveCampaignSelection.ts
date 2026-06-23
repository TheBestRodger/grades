import { useEffect, useMemo, useState } from "react";

import type { Campaign } from "../../types";

export function useActiveCampaignSelection(campaigns: Campaign[] | undefined) {
  const [activeCampaignId, setActiveCampaignId] = useState<number | null>(null);
  const [activeWaveId, setActiveWaveId] = useState<number | null>(null);

  useEffect(() => {
    if (!campaigns?.length) {
      setActiveCampaignId(null);
      return;
    }
    if (!activeCampaignId || !campaigns.some((campaign) => campaign.id === activeCampaignId)) {
      setActiveCampaignId(campaigns[0].id);
    }
  }, [activeCampaignId, campaigns]);

  const activeCampaign = campaigns?.find((campaign) => campaign.id === activeCampaignId) ?? null;
  const activeWave =
    activeCampaign?.waves.find((wave) => wave.id === activeWaveId) ??
    activeCampaign?.waves.find((wave) => wave.id === activeCampaign.active_wave_id) ??
    activeCampaign?.waves[0] ??
    null;

  const activeCampaignForTree = useMemo<Campaign | null>(() => {
    if (!activeCampaign || !activeWave) return activeCampaign;
    return {
      ...activeCampaign,
      active_wave_id: activeWave.id,
      active_wave_name: activeWave.name,
      participants_expected: activeWave.participants_expected,
      participant_assignment_ids: activeWave.participant_assignment_ids,
      selected_org_unit_ids: activeWave.selected_org_unit_ids,
      selected_units_count: activeWave.selected_units_count,
      selected_staffing_lines: activeWave.selected_staffing_lines,
      selected_approved_fte: activeWave.selected_approved_fte,
      status_counts: activeWave.status_counts,
    };
  }, [activeCampaign, activeWave]);

  useEffect(() => {
    if (!activeCampaign) {
      setActiveWaveId(null);
      return;
    }
    const waveIds = activeCampaign.waves.map((wave) => wave.id);
    if (!activeWaveId || !waveIds.includes(activeWaveId)) {
      setActiveWaveId(activeCampaign.active_wave_id ?? waveIds[0] ?? null);
    }
  }, [activeCampaign, activeWaveId]);

  return {
    activeCampaign,
    activeCampaignForTree,
    activeCampaignId,
    activeWave,
    activeWaveId,
    setActiveCampaignId,
    setActiveWaveId,
  };
}
