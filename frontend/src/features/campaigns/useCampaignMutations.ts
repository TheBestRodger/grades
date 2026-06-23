import { useMutation } from "@tanstack/react-query";

import {
  createCampaign,
  createCampaignWave,
  editCampaignWave,
  excludeBranch,
  includeBranch,
  launchCampaignWave,
  setCampaignAssignments,
} from "../../api";
import type { DataScope } from "../../app/navigation";
import type { Campaign } from "../../types";

interface CampaignMutationOptions {
  selectedUserId: number | null;
  dataScope: DataScope;
  getActiveCampaignId: () => number;
  getActiveWaveId: () => number;
  onCreateCampaignSuccess?: (campaign: Campaign) => void | Promise<void>;
  onCreateWaveSuccess?: (campaign: Campaign & { new_wave_id?: number | null; new_wave_name?: string | null }) => void | Promise<void>;
  onEditWaveSuccess?: (campaign: Campaign & { editing_wave_id?: number | null; editing_wave_name?: string | null }) => void | Promise<void>;
  onLaunchWaveSuccess?: (campaign: Campaign & { launched_wave_id?: number | null; launched_wave_name?: string | null }) => void | Promise<void>;
  onIncludeSuccess?: (campaign: Campaign & { included_unit_name?: string; included_wave_name?: string; new_participants?: number | null; scope?: string }) => void | Promise<void>;
  onIncludeError?: () => void;
  onExcludeSuccess?: (campaign: Campaign & { excluded_unit_name?: string; excluded_wave_name?: string; excluded_participants?: number; scope?: string }) => void | Promise<void>;
  onExcludeError?: () => void;
  onAssignmentSuccess?: (campaign: Campaign & { participant_action?: "include" | "exclude" }) => void | Promise<void>;
  onAssignmentError?: () => void;
}

export function useCampaignMutations(options: CampaignMutationOptions) {
  const createCampaignMutation = useMutation({
    mutationFn: ({ name, dueAt }: { name: string; dueAt: string | null }) =>
      createCampaign(options.selectedUserId!, name, dueAt, options.dataScope),
    onSuccess: options.onCreateCampaignSuccess,
  });
  const createWaveMutation = useMutation({
    mutationFn: ({ campaignId, name, dueAt }: { campaignId: number; name: string; dueAt: string | null }) =>
      createCampaignWave(options.selectedUserId!, campaignId, name, dueAt, options.dataScope),
    onSuccess: options.onCreateWaveSuccess,
  });
  const editWaveMutation = useMutation({
    mutationFn: ({ campaignId, waveId }: { campaignId: number; waveId: number }) =>
      editCampaignWave(options.selectedUserId!, campaignId, waveId, options.dataScope),
    onSuccess: options.onEditWaveSuccess,
  });
  const launchWaveMutation = useMutation({
    mutationFn: ({ campaignId, waveId }: { campaignId: number; waveId: number }) =>
      launchCampaignWave(options.selectedUserId!, campaignId, waveId, options.dataScope),
    onSuccess: options.onLaunchWaveSuccess,
  });
  const includeMutation = useMutation({
    mutationFn: ({ campaignId, unitId, waveId }: { campaignId: number; unitId: number; waveId: number | null }) =>
      includeBranch(options.selectedUserId!, campaignId, unitId, waveId, options.dataScope),
    onSuccess: options.onIncludeSuccess,
    onError: options.onIncludeError,
  });
  const excludeMutation = useMutation({
    mutationFn: ({ campaignId, unitId, waveId }: { campaignId: number; unitId: number; waveId: number | null }) =>
      excludeBranch(options.selectedUserId!, campaignId, unitId, waveId, options.dataScope),
    onSuccess: options.onExcludeSuccess,
    onError: options.onExcludeError,
  });
  const campaignAssignmentMutation = useMutation({
    mutationFn: ({ assignmentId, included }: { assignmentId: number; included: boolean }) =>
      setCampaignAssignments(
        options.selectedUserId!,
        options.getActiveCampaignId(),
        options.getActiveWaveId(),
        [assignmentId],
        included ? "include" : "exclude",
        options.dataScope,
      ),
    onSuccess: options.onAssignmentSuccess,
    onError: options.onAssignmentError,
  });

  return {
    createCampaignMutation,
    createWaveMutation,
    editWaveMutation,
    launchWaveMutation,
    includeMutation,
    excludeMutation,
    campaignAssignmentMutation,
  };
}
