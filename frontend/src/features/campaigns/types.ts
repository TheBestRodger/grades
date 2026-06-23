import type { AuditEvent, Campaign } from "../../types";

export interface CampaignPanelProps {
  scope: "demo" | "work";
  campaigns: Campaign[];
  activeCampaignId: number | null;
  activeWaveId: number | null;
  events: AuditEvent[];
  message: string | null;
  error: string | null;
  isCreating: boolean;
  isCreatingWave: boolean;
  isLaunchingWave: boolean;
  isEditingWave: boolean;
  credentialsFileReady: boolean;
  isPreparingCredentials: boolean;
  onActiveChange: (id: number) => void;
  onWaveChange: (id: number) => void;
  onCreate: (name: string, dueAt: string | null) => void;
  onCreateWave: (campaignId: number, name: string, dueAt: string | null) => void;
  onLaunchWave: (campaignId: number, waveId: number) => void;
  onEditWave: (campaignId: number, waveId: number) => void;
  onExport: (kind: "profiles" | "campaigns", format: "csv" | "json") => void;
  onPrepareCredentialsFile: () => void;
  onDownloadCredentials: () => void;
}

export type WaveAction = "launch" | "edit";
