import { SettingsPanel } from "../features/settings";
import type { AppControllerContext } from "../app/types";
import type { AiConfigurationInput, QuestionnaireSettingsInput } from "../types";

interface SettingsPageProps
  extends Pick<
    AppControllerContext,
    "activeSection" | "aiSettings" | "isHr" | "questionnaireSettings"
  > {
  aiSettingsError: string | null;
  isQuestionnaireLoading: boolean;
  isQuestionnaireSaving: boolean;
  isSaving: boolean;
  onSave: (payload: AiConfigurationInput) => void;
  onSaveQuestionnaire: (payload: QuestionnaireSettingsInput) => void;
  questionnaireError: string | null;
}

export function SettingsPage({
  activeSection,
  aiSettings,
  aiSettingsError,
  isHr,
  isQuestionnaireLoading,
  isQuestionnaireSaving,
  isSaving,
  onSave,
  onSaveQuestionnaire,
  questionnaireError,
  questionnaireSettings,
}: SettingsPageProps) {
  if (!isHr || activeSection !== "settings") return null;

  return (
    <SettingsPanel
      configuration={aiSettings.data ?? null}
      error={aiSettings.error?.message ?? aiSettingsError ?? null}
      questionnaire={questionnaireSettings.data ?? null}
      questionnaireError={questionnaireSettings.error?.message ?? questionnaireError ?? null}
      isLoading={aiSettings.isLoading}
      isQuestionnaireLoading={isQuestionnaireLoading}
      isSaving={isSaving}
      isQuestionnaireSaving={isQuestionnaireSaving}
      onSave={onSave}
      onSaveQuestionnaire={onSaveQuestionnaire}
    />
  );
}
