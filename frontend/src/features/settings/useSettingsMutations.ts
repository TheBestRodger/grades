import { useMutation } from "@tanstack/react-query";

import { updateAiSettings, updateQuestionnaireSettings } from "../../api";
import type {
  AiConfiguration,
  AiConfigurationInput,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
} from "../../types";

interface SettingsMutationOptions {
  selectedUserId: number | null;
  onAiSettingsSuccess?: (configuration: AiConfiguration) => void | Promise<void>;
  onQuestionnaireSettingsSuccess?: (settings: QuestionnaireSettings) => void | Promise<void>;
}

export function useSettingsMutations(options: SettingsMutationOptions) {
  const aiSettingsMutation = useMutation({
    mutationFn: (payload: AiConfigurationInput) => updateAiSettings(options.selectedUserId!, payload),
    onSuccess: options.onAiSettingsSuccess,
  });
  const questionnaireSettingsMutation = useMutation({
    mutationFn: (payload: QuestionnaireSettingsInput) =>
      updateQuestionnaireSettings(options.selectedUserId!, payload),
    onSuccess: options.onQuestionnaireSettingsSuccess,
  });

  return { aiSettingsMutation, questionnaireSettingsMutation };
}
