import { useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

import type { DataScope } from "../../app/navigation";
import type { ProfileAiUsagePayload } from "../../app/types";
import { queryKeys } from "../../shared/queryKeys";
import type { AiAnswerCheckResult, EmployeeProfile } from "../../types";
import { useProfileMutations } from "./useProfileMutations";

interface UseProfileWorkflowOptions {
  dataScope: DataScope;
  queryClient: QueryClient;
  selectedUserId: number | null;
}

export function useProfileWorkflow({ dataScope: _dataScope, queryClient, selectedUserId }: UseProfileWorkflowOptions) {
  const [aiCheckResults, setAiCheckResults] = useState<Record<string, AiAnswerCheckResult>>({});
  const [aiCheckingKey, setAiCheckingKey] = useState<string | null>(null);
  const [aiCheckErrorKey, setAiCheckErrorKey] = useState<string | null>(null);
  const [aiAnswerSnapshots, setAiAnswerSnapshots] = useState<Record<string, string>>({});

  const { saveDraftMutation, submitProfileMutation, aiCheckMutation } = useProfileMutations({
    selectedUserId,
    onSaveSuccess: (updated) => {
      queryClient.setQueryData<EmployeeProfile[]>(
        queryKeys.myProfiles(selectedUserId),
        (existing) => existing?.map((profile) => (profile.id === updated.id ? updated : profile)) ?? [updated],
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(null) });
    },
    onSubmitSuccess: (updated) => {
      queryClient.setQueryData<EmployeeProfile[]>(
        queryKeys.myProfiles(selectedUserId),
        (existing) => existing?.map((profile) => (profile.id === updated.id ? updated : profile)) ?? [updated],
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(null) });
    },
    onAiCheckSuccess: (result, variables) => {
      setAiCheckResults((existing) => ({ ...existing, [result.question_key]: result }));
      setAiAnswerSnapshots((existing) => ({
        ...existing,
        [result.question_key]: variables.answers[result.question_key] ?? "",
      }));
      setAiCheckingKey(null);
      setAiCheckErrorKey(null);
    },
    onAiCheckError: (_error, variables) => {
      setAiCheckingKey(null);
      setAiCheckErrorKey(variables.questionKey);
    },
  });

  async function savePersonalDraft(
    profileId: number,
    answers: Record<string, string>,
    aiUsage: ProfileAiUsagePayload,
  ) {
    saveDraftMutation.reset();
    return saveDraftMutation.mutateAsync({ profileId, answers, aiUsage });
  }

  async function submitPersonalProfile(
    profileId: number,
    answers: Record<string, string>,
    aiUsage: ProfileAiUsagePayload,
  ) {
    submitProfileMutation.reset();
    return submitProfileMutation.mutateAsync({ profileId, answers, aiUsage });
  }

  async function checkPersonalAnswer(
    profileId: number,
    questionKey: string,
    answers: Record<string, string>,
  ) {
    aiCheckMutation.reset();
    setAiCheckingKey(questionKey);
    setAiCheckErrorKey(null);

    const previous = aiCheckResults[questionKey];

    return aiCheckMutation.mutateAsync({
      profileId,
      questionKey,
      answers,
      previousAnswer: previous ? aiAnswerSnapshots[questionKey] ?? null : null,
      previousFollowupQuestion: previous?.followup_question ?? null,
      previousClarityPercent: previous?.clarity_percent ?? null,
    });
  }

  return {
    aiAnswerSnapshots,
    aiCheckErrorKey,
    aiCheckMutation,
    aiCheckResults,
    aiCheckingKey,
    checkPersonalAnswer,
    saveDraftMutation,
    savePersonalDraft,
    submitPersonalProfile,
    submitProfileMutation,
  };
}
