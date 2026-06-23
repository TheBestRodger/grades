import type { QueryClient } from "@tanstack/react-query";

import { invalidateQuestionnaireViews } from "../../shared/invalidation";
import { queryKeys } from "../../shared/queryKeys";
import { useSettingsMutations } from "./useSettingsMutations";

interface UseSettingsWorkflowOptions {
  queryClient: QueryClient;
  selectedUserId: number | null;
  setOperationMessage: (message: string | null) => void;
}

export function useSettingsWorkflow({ queryClient, selectedUserId, setOperationMessage }: UseSettingsWorkflowOptions) {
  return useSettingsMutations({
    selectedUserId,
    onAiSettingsSuccess: async (configuration) => {
      queryClient.setQueryData(queryKeys.aiSettings(selectedUserId), configuration);
      setOperationMessage("Настройки ИИ сохранены. Реальные вызовы LLM пока остаются отключёнными.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.health() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(null) }),
      ]);
    },
    onQuestionnaireSettingsSuccess: async (settings) => {
      queryClient.setQueryData(queryKeys.questionnaireSettings(selectedUserId), settings);
      setOperationMessage("Настройки открытых ответов сохранены.");
      await invalidateQuestionnaireViews(queryClient);
    },
  });
}
