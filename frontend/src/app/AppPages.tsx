import { WorkContourPlaceholder } from "../components/WorkContourPlaceholder";
import { AnalyticsPage } from "../pages/AnalyticsPage";
import { CampaignsPage } from "../pages/CampaignsPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { HrReviewsPage } from "../pages/HrReviewsPage";
import { ManagerOverviewPage } from "../pages/ManagerOverviewPage";
import { ManagerReviewsPage } from "../pages/ManagerReviewsPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SettingsPage } from "../pages/SettingsPage";
import { StructurePage } from "../pages/StructurePage";
import type { AiConfigurationInput, QuestionnaireSettingsInput } from "../types";
import type { AppControllerContext } from "./types";

interface AppPagesProps {
  context: AppControllerContext;
}

export function AppPages({ context }: AppPagesProps) {
  const {
    acceptByHr,
    acceptHrMutation,
    activeCampaignForTree,
    activeCampaignId,
    activePersonalProfile,
    activeSection,
    activeUser,
    activeWave,
    activeWaveId,
    aiAnswerSnapshots,
    aiCheckErrorKey,
    aiCheckMutation,
    aiCheckResults,
    aiCheckingKey,
    aiSettings,
    aiSettingsMutation,
    audit,
    bulkReturnByHrSelected,
    bulkReturnByHrUnit,
    bulkReturnHrMutation,
    bulkReturnReviewMutation,
    bulkReturnReviewSelected,
    bulkReturnReviewUnit,
    campaignAssignmentMutation,
    campaigns,
    changingAssignmentId,
    checkPersonalAnswer,
    createCampaignMutation,
    createWaveMutation,
    dataScope,
    demoResetMutation,
    documentDownloadError,
    documentLinkMutation,
    documentQualityMutation,
    documents,
    documentUploadMutation,
    downloadWorkDocument,
    editWaveMutation,
    excludeMutation,
    excludeUnit,
    excludingUnitId,
    exportError,
    exportHrData,
    exportIssuedCredentials,
    exportPersonalProfile,
    health,
    hrAnalytics,
    hrDecisionMessage,
    hrDecisionProfileId,
    hrReviews,
    includeMutation,
    includeUnit,
    includingUnitId,
    isHr,
    isManager,
    launchWaveMutation,
    managerDocuments,
    managerOverview,
    managerReviews,
    openEmployeeEditModal,
    openEmployeeModal,
    openStaffingLineModal,
    operationMessage,
    prepareIssuedCredentialsFile,
    preparingCredentials,
    questionnaireSettings,
    questionnaireSettingsMutation,
    requestDeleteAssignment,
    requestDeletePosition,
    returnByHr,
    returnHrMutation,
    returnReview,
    returnReviewMutation,
    reviewActionProfileId,
    reviewMessage,
    reviewWorkDocument,
    reviewingDocumentId,
    saveDraftMutation,
    savePersonalDraft,
    selectedUser,
    setActiveCampaignId,
    setActiveWaveId,
    setAssignmentParticipation,
    submitPersonalProfile,
    submitProfileMutation,
    summary,
    takeReview,
    takeReviewMutation,
    tree,
    verifyReview,
    verifyReviewMutation,
    workSummary,
    workTree,
  } = context;

  const credentialsFileReady = Boolean(context.credentialsFileBlob);

  return (
    <>
      <SettingsPage
        activeSection={activeSection}
        aiSettings={aiSettings}
        aiSettingsError={aiSettingsMutation.error?.message ?? null}
        isHr={isHr}
        isQuestionnaireLoading={questionnaireSettings.isLoading}
        isQuestionnaireSaving={questionnaireSettingsMutation.isPending}
        isSaving={aiSettingsMutation.isPending}
        onSave={(payload: AiConfigurationInput) => aiSettingsMutation.mutate(payload)}
        onSaveQuestionnaire={(payload: QuestionnaireSettingsInput) =>
          questionnaireSettingsMutation.mutate(payload)
        }
        questionnaireError={questionnaireSettingsMutation.error?.message ?? null}
        questionnaireSettings={questionnaireSettings}
      />

      <StructurePage
        activeCampaignForTree={activeCampaignForTree}
        activePersonalProfile={activePersonalProfile}
        activeSection={activeSection}
        activeUser={activeUser}
        changingAssignmentId={changingAssignmentId}
        dataScope={dataScope}
        demoResetError={demoResetMutation.error?.message ?? null}
        demoResetResult={demoResetMutation.data ?? null}
        excludingUnitId={excludingUnitId}
        includingUnitId={includingUnitId}
        isDemoResetting={demoResetMutation.isPending}
        isHr={isHr}
        onAddEmployee={openEmployeeModal}
        onCreatePosition={openStaffingLineModal}
        onDeleteAssignment={requestDeleteAssignment}
        onDeletePosition={requestDeletePosition}
        onEditAssignment={openEmployeeEditModal}
        onExcludeUnit={excludeUnit}
        onIncludeUnit={includeUnit}
        onResetDemo={() => demoResetMutation.mutate()}
        onSetAssignment={setAssignmentParticipation}
        selectedUser={selectedUser}
        summary={summary}
        tree={tree}
        workSummary={workSummary}
        workTree={workTree}
      />

      <DocumentsPage
        activeSection={activeSection}
        assigningDocumentKey={context.assigningDocumentKey}
        dataScope={dataScope}
        documentDownloadError={documentDownloadError}
        documentLinkError={documentLinkMutation.error?.message ?? null}
        documentQualityError={documentQualityMutation.error?.message ?? null}
        documents={documents}
        documentUploadError={documentUploadMutation.error?.message ?? null}
        isHr={isHr}
        isManager={isManager}
        isUploading={documentUploadMutation.isPending}
        managerDocuments={managerDocuments}
        onDownloadSource={(documentId: number) => void downloadWorkDocument(documentId)}
        onReviewQuality={reviewWorkDocument}
        onSetLink={context.assignWorkDocument}
        onUpload={context.addWorkDocument}
        reviewingDocumentId={reviewingDocumentId}
        tree={tree}
        workTree={workTree}
      />

      <CampaignsPage
        activeCampaignForTree={activeCampaignForTree}
        activeCampaignId={activeCampaignId}
        activeSection={activeSection}
        activeWave={activeWave}
        activeWaveId={activeWaveId}
        campaigns={campaigns}
        canAddEmployees={dataScope === "work" ? false : undefined}
        changingAssignmentId={changingAssignmentId}
        createCampaignError={createCampaignMutation.error?.message ?? null}
        createWaveError={createWaveMutation.error?.message ?? null}
        credentialsFileReady={credentialsFileReady}
        dataScope={dataScope}
        editWaveError={editWaveMutation.error?.message ?? null}
        events={audit}
        excludeError={excludeMutation.error?.message ?? null}
        excludingUnitId={excludingUnitId}
        exportError={exportError}
        includeError={includeMutation.error?.message ?? null}
        includingUnitId={includingUnitId}
        isCreating={createCampaignMutation.isPending}
        isCreatingWave={createWaveMutation.isPending}
        isEditingWave={editWaveMutation.isPending}
        isHr={isHr}
        isLaunchingWave={launchWaveMutation.isPending}
        isPreparingCredentials={preparingCredentials}
        launchWaveError={launchWaveMutation.error?.message ?? null}
        message={operationMessage}
        onActiveChange={(id: number) => {
          setActiveCampaignId(id);
          setActiveWaveId(null);
        }}
        onAddEmployee={openEmployeeModal}
        onCreate={(name: string, dueAt: string | null) => createCampaignMutation.mutate({ name, dueAt })}
        onCreateWave={(campaignId: number, name: string, dueAt: string | null) =>
          createWaveMutation.mutate({ campaignId, name, dueAt })
        }
        onDownloadCredentials={exportIssuedCredentials}
        onEditWave={(campaignId: number, waveId: number) => editWaveMutation.mutate({ campaignId, waveId })}
        onExcludeUnit={excludeUnit}
        onExport={exportHrData}
        onIncludeUnit={includeUnit}
        onLaunchWave={(campaignId: number, waveId: number) => launchWaveMutation.mutate({ campaignId, waveId })}
        onPrepareCredentialsFile={prepareIssuedCredentialsFile}
        onSetAssignment={setAssignmentParticipation}
        onWaveChange={setActiveWaveId}
        participantError={campaignAssignmentMutation.error?.message ?? null}
        tree={tree}
        workTree={workTree}
      />

      <AnalyticsPage
        activeSection={activeSection}
        dataScope={dataScope}
        hrAnalytics={hrAnalytics}
        isHr={isHr}
      />

      <HrReviewsPage
        acceptError={acceptHrMutation.error?.message ?? null}
        activeProfileId={hrDecisionProfileId}
        activeSection={activeSection}
        bulkActive={bulkReturnHrMutation.isPending}
        bulkError={bulkReturnHrMutation.error?.message ?? null}
        dataScope={dataScope}
        hrReviews={hrReviews}
        isHr={isHr}
        message={hrDecisionMessage}
        onAccept={acceptByHr}
        onBulkReturnSelected={bulkReturnByHrSelected}
        onBulkReturnUnit={bulkReturnByHrUnit}
        onReturn={returnByHr}
        returnError={returnHrMutation.error?.message ?? null}
      />

      {dataScope === "work" && activeUser?.role !== "employee" && activeSection !== "structure" && activeSection !== "documents" && activeSection !== "campaigns" && activeSection !== "analytics" && activeSection !== "hr-reviews" && activeSection !== "settings" && activeSection !== "profile" && activeSection !== "manager-overview" && activeSection !== "manager-reviews" && (
        <WorkContourPlaceholder />
      )}

      <ProfilePage
        activeSection={activeSection}
        activePersonalProfile={activePersonalProfile}
        aiAnswerSnapshots={aiAnswerSnapshots}
        aiCheckError={aiCheckErrorKey ? (aiCheckMutation.error instanceof Error ? aiCheckMutation.error.message : null) : null}
        aiCheckResults={aiCheckResults}
        aiCheckingKey={aiCheckingKey}
        health={health}
        isSaving={saveDraftMutation.isPending}
        isSubmitting={submitProfileMutation.isPending}
        onAiCheck={checkPersonalAnswer}
        onExport={exportPersonalProfile}
        onSave={savePersonalDraft}
        onSubmit={submitPersonalProfile}
        saveError={saveDraftMutation.error?.message ?? null}
        submitError={submitProfileMutation.error?.message ?? null}
        summary={summary}
      />

      <ManagerOverviewPage
        activeSection={activeSection}
        isManager={isManager}
        managerOverview={managerOverview}
      />

      <ManagerReviewsPage
        activeProfileId={reviewActionProfileId}
        activeSection={activeSection}
        bulkActive={bulkReturnReviewMutation.isPending}
        bulkError={bulkReturnReviewMutation.error?.message ?? null}
        isManager={isManager}
        managerReviews={managerReviews}
        message={reviewMessage}
        onBulkReturnSelected={bulkReturnReviewSelected}
        onBulkReturnUnit={bulkReturnReviewUnit}
        onReturn={returnReview}
        onTake={takeReview}
        onVerify={verifyReview}
        returnError={returnReviewMutation.error?.message ?? null}
        takeError={takeReviewMutation.error?.message ?? null}
        verifyError={verifyReviewMutation.error?.message ?? null}
      />
    </>
  );
}
