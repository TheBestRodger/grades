import { useMutation } from "@tanstack/react-query";

import { checkProfileAnswer, saveProfileDraft, submitProfile } from "../../api";
import type { ProfileAiUsagePayload } from "../../app/types";
import type { AiAnswerCheckResult, EmployeeProfile } from "../../types";

interface AiCheckPayload {
  profileId: number;
  questionKey: string;
  answers: Record<string, string>;
  previousAnswer?: string | null;
  previousFollowupQuestion?: string | null;
  previousClarityPercent?: number | null;
}

interface ProfileMutationOptions {
  selectedUserId: number | null;
  onSaveSuccess?: (updated: EmployeeProfile) => void | Promise<void>;
  onSubmitSuccess?: (updated: EmployeeProfile) => void | Promise<void>;
  onAiCheckSuccess?: (result: AiAnswerCheckResult, variables: AiCheckPayload) => void;
  onAiCheckError?: (error: unknown, variables: AiCheckPayload) => void;
}

export function useProfileMutations(options: ProfileMutationOptions) {
  const saveDraftMutation = useMutation({
    mutationFn: ({ profileId, answers, aiUsage }: { profileId: number; answers: Record<string, string>; aiUsage?: ProfileAiUsagePayload }) =>
      saveProfileDraft(options.selectedUserId!, profileId, answers, aiUsage),
    onSuccess: options.onSaveSuccess,
  });
  const submitProfileMutation = useMutation({
    mutationFn: ({ profileId, answers, aiUsage }: { profileId: number; answers: Record<string, string>; aiUsage?: ProfileAiUsagePayload }) =>
      submitProfile(options.selectedUserId!, profileId, answers, aiUsage),
    onSuccess: options.onSubmitSuccess,
  });
  const aiCheckMutation = useMutation({
    mutationFn: ({ profileId, questionKey, answers, previousAnswer, previousFollowupQuestion, previousClarityPercent }: AiCheckPayload) =>
      checkProfileAnswer(options.selectedUserId!, profileId, questionKey, answers, {
        previous_answer: previousAnswer ?? null,
        previous_followup_question: previousFollowupQuestion ?? null,
        previous_clarity_percent: previousClarityPercent ?? null,
      }),
    onSuccess: options.onAiCheckSuccess,
    onError: options.onAiCheckError,
  });

  return { saveDraftMutation, submitProfileMutation, aiCheckMutation };
}
