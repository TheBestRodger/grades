import type {
  AiConfiguration,
  AiConfigurationInput,
  AiConfigurationMode,
  AiProvider,
  QuestionnaireQuestionSettingInput,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
} from "../../types";

export type {
  AiConfiguration,
  AiConfigurationInput,
  AiConfigurationMode,
  AiProvider,
  QuestionnaireQuestionSettingInput,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
};

export interface SettingsPanelProps {
  configuration: AiConfiguration | null;
  questionnaire: QuestionnaireSettings | null;
  error: string | null;
  questionnaireError: string | null;
  isLoading: boolean;
  isQuestionnaireLoading: boolean;
  isSaving: boolean;
  isQuestionnaireSaving: boolean;
  onSave: (payload: AiConfigurationInput) => void;
  onSaveQuestionnaire: (payload: QuestionnaireSettingsInput) => void;
}
