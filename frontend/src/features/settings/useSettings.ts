import { useQuery } from "@tanstack/react-query";

import { getAiSettings, getQuestionnaireSettings } from "../../api";
import { queryKeys } from "../../shared/queryKeys";

export function useSettings(userId: number | null, enabled: boolean) {
  const aiSettings = useQuery({
    queryKey: queryKeys.aiSettings(userId),
    queryFn: () => getAiSettings(userId!),
    enabled: userId !== null && enabled,
  });
  const questionnaireSettings = useQuery({
    queryKey: queryKeys.questionnaireSettings(userId),
    queryFn: () => getQuestionnaireSettings(userId!),
    enabled: userId !== null && enabled,
  });
  return { aiSettings, questionnaireSettings };
}
