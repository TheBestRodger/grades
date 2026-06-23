import { SummaryMetrics } from "../components/SummaryMetrics";
import { ProfileWorkspace } from "../features/profile";
import type { AppControllerContext } from "../app/types";

interface ProfilePageProps
  extends Pick<
    AppControllerContext,
    | "activeSection"
    | "activePersonalProfile"
    | "aiAnswerSnapshots"
    | "aiCheckResults"
    | "aiCheckingKey"
    | "health"
    | "summary"
  > {
  aiCheckError: string | null;
  isSaving: boolean;
  isSubmitting: boolean;
  onAiCheck: AppControllerContext["checkPersonalAnswer"];
  onExport: AppControllerContext["exportPersonalProfile"];
  onSave: AppControllerContext["savePersonalDraft"];
  onSubmit: AppControllerContext["submitPersonalProfile"];
  saveError: string | null;
  submitError: string | null;
}

export function ProfilePage({
  activeSection,
  activePersonalProfile,
  aiAnswerSnapshots,
  aiCheckError,
  aiCheckResults,
  aiCheckingKey,
  health,
  onAiCheck,
  onExport,
  onSave,
  onSubmit,
  saveError,
  isSaving,
  isSubmitting,
  submitError,
  summary,
}: ProfilePageProps) {
  if (activeSection !== "profile") return null;

  return (
    <>
      {summary.data && <SummaryMetrics profile={activePersonalProfile} summary={summary.data} />}
      {activePersonalProfile ? (
        <ProfileWorkspace
          ai={health.data?.ai}
          aiCheckError={aiCheckError}
          aiCheckResults={aiCheckResults}
          aiAnswerSnapshots={aiAnswerSnapshots}
          aiCheckingKey={aiCheckingKey}
          error={saveError ?? submitError ?? null}
          isSaving={isSaving}
          isSubmitting={isSubmitting}
          onAiCheck={onAiCheck}
          key={activePersonalProfile.id}
          onSave={onSave}
          onSubmit={onSubmit}
          onExport={onExport}
          profile={activePersonalProfile}
        />
      ) : (
        <div className="rounded-2xl border border-blue-100 bg-white p-5 text-sm text-slate-600 shadow-sm">
          Анкета появится после включения вашего назначения в активную кампанию профилирования.
        </div>
      )}
    </>
  );
}
