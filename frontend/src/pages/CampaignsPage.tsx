import { CampaignPanel } from "../features/campaigns";
import { OrganizationTreePanel } from "../features/organization";
import type { AppControllerContext } from "../app/types";

interface CampaignsPageProps
  extends Pick<
    AppControllerContext,
    | "activeCampaignForTree"
    | "activeCampaignId"
    | "activeSection"
    | "activeWave"
    | "activeWaveId"
    | "campaigns"
    | "changingAssignmentId"
    | "dataScope"
    | "excludingUnitId"
    | "includingUnitId"
    | "isHr"
    | "tree"
    | "workTree"
  > {
  canAddEmployees?: boolean;
  createCampaignError: string | null;
  createWaveError: string | null;
  credentialsFileReady: boolean;
  editWaveError: string | null;
  events: AppControllerContext["audit"];
  excludeError: string | null;
  exportError: string | null;
  includeError: string | null;
  isCreating: boolean;
  isCreatingWave: boolean;
  isEditingWave: boolean;
  isLaunchingWave: boolean;
  isPreparingCredentials: boolean;
  launchWaveError: string | null;
  message: AppControllerContext["operationMessage"];
  onActiveChange: (id: number) => void;
  onAddEmployee: AppControllerContext["openEmployeeModal"];
  onCreate: (name: string, dueAt: string | null) => void;
  onCreateWave: (campaignId: number, name: string, dueAt: string | null) => void;
  onDownloadCredentials: AppControllerContext["exportIssuedCredentials"];
  onEditWave: (campaignId: number, waveId: number) => void;
  onExcludeUnit: AppControllerContext["excludeUnit"];
  onExport: AppControllerContext["exportHrData"];
  onIncludeUnit: AppControllerContext["includeUnit"];
  onLaunchWave: (campaignId: number, waveId: number) => void;
  onPrepareCredentialsFile: AppControllerContext["prepareIssuedCredentialsFile"];
  onSetAssignment: AppControllerContext["setAssignmentParticipation"];
  onWaveChange: AppControllerContext["setActiveWaveId"];
  participantError: string | null;
}

export function CampaignsPage({
  activeCampaignForTree,
  activeCampaignId,
  activeSection,
  activeWave,
  activeWaveId,
  campaigns,
  canAddEmployees,
  changingAssignmentId,
  createCampaignError,
  createWaveError,
  credentialsFileReady,
  dataScope,
  editWaveError,
  events,
  excludeError,
  excludingUnitId,
  exportError,
  includeError,
  includingUnitId,
  isCreating,
  isCreatingWave,
  isEditingWave,
  isHr,
  isLaunchingWave,
  isPreparingCredentials,
  launchWaveError,
  message,
  onActiveChange,
  onAddEmployee,
  onCreate,
  onCreateWave,
  onDownloadCredentials,
  onEditWave,
  onExcludeUnit,
  onExport,
  onIncludeUnit,
  onLaunchWave,
  onPrepareCredentialsFile,
  onSetAssignment,
  onWaveChange,
  participantError,
  tree,
  workTree,
}: CampaignsPageProps) {
  if (!isHr || activeSection !== "campaigns") return null;
  if (dataScope !== "work" && dataScope !== "demo") return null;

  const sourceTree = dataScope === "work" ? workTree : tree;

  return (
    <>
      <CampaignPanel
        scope={dataScope}
        activeCampaignId={activeCampaignId}
        activeWaveId={activeWaveId}
        campaigns={campaigns.data ?? []}
        error={
          createCampaignError ??
          createWaveError ??
          launchWaveError ??
          editWaveError ??
          includeError ??
          excludeError ??
          participantError ??
          exportError ??
          null
        }
        events={events.data ?? []}
        credentialsFileReady={credentialsFileReady}
        isPreparingCredentials={isPreparingCredentials}
        isCreating={isCreating}
        isCreatingWave={isCreatingWave}
        isLaunchingWave={isLaunchingWave}
        isEditingWave={isEditingWave}
        message={message}
        onActiveChange={onActiveChange}
        onCreate={onCreate}
        onExport={onExport}
        onPrepareCredentialsFile={onPrepareCredentialsFile}
        onDownloadCredentials={onDownloadCredentials}
        onCreateWave={onCreateWave}
        onLaunchWave={onLaunchWave}
        onEditWave={onEditWave}
        onWaveChange={onWaveChange}
      />
      {sourceTree.data && (
        <OrganizationTreePanel
          activeCampaign={activeCampaignForTree}
          canManage={Boolean(activeCampaignForTree && activeWave?.can_edit)}
          canAddEmployees={canAddEmployees}
          changingAssignmentId={changingAssignmentId}
          excludingUnitId={excludingUnitId}
          includingUnitId={includingUnitId}
          nodes={sourceTree.data.nodes}
          onAdd={onAddEmployee}
          onExclude={onExcludeUnit}
          onInclude={onIncludeUnit}
          onSetAssignment={onSetAssignment}
        />
      )}
    </>
  );
}
