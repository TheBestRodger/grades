export type AiConfigurationMode = "default" | "off" | "local" | "token";
export type AiProvider = "off" | "ollama" | "lm_studio" | "openai_compatible";

export interface AiConfiguration {
  mode: AiConfigurationMode;
  mode_label: string;
  provider: AiProvider;
  provider_label: string;
  base_url: string | null;
  model_name: string | null;
  api_token_configured: boolean;
  clarity_threshold: number;
  followup_strictness: "soft" | "balanced" | "strict";
  effective_mode: string;
  effective_provider: string;
  available: boolean;
  connection_status: string;
  note: string;
  updated_at: string | null;
  updated_by_id: number | null;
}

export interface AiConfigurationInput {
  mode: AiConfigurationMode;
  provider: AiProvider;
  base_url: string | null;
  model_name: string | null;
  api_token?: string | null;
  clear_api_token?: boolean;
  clarity_threshold: number;
  followup_strictness: "soft" | "balanced" | "strict";
}

export interface QuestionnaireQuestionSetting {
  question_key: string;
  section: string;
  title: string;
  input_type: "text" | "textarea" | "table";
  question: string;
  base_example: string;
  ai_check_enabled: boolean;
  good_example: string;
  bad_example: string | null;
  requirements: string | null;
  updated_at: string | null;
  updated_by_id: number | null;
}

export interface QuestionnaireSettings {
  scope: "global_current_questionnaire";
  versioning_status: "not_versioned_yet";
  questions: QuestionnaireQuestionSetting[];
}

export interface QuestionnaireQuestionSettingInput {
  question_key: string;
  ai_check_enabled: boolean;
  good_example: string | null;
  bad_example: string | null;
  requirements: string | null;
}

export interface QuestionnaireSettingsInput {
  questions: QuestionnaireQuestionSettingInput[];
}
