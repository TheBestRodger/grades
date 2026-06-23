import { useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

import type { DataScope } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";
import { useReviewMutations } from "./useReviewMutations";

interface UseReviewWorkflowOptions {
  dataScope: DataScope;
  queryClient: QueryClient;
  selectedUserId: number | null;
}

export function useReviewWorkflow({ dataScope, queryClient, selectedUserId }: UseReviewWorkflowOptions) {
  const [reviewActionProfileId, setReviewActionProfileId] = useState<number | null>(null);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [hrDecisionProfileId, setHrDecisionProfileId] = useState<number | null>(null);
  const [hrDecisionMessage, setHrDecisionMessage] = useState<string | null>(null);

  async function refreshReviewViews() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.managerReviews(selectedUserId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.managerOverview(selectedUserId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.myProfiles(null) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.audit(null) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(null) }),
    ]);
  }

  async function refreshHrDecisionViews() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.hrReviews(selectedUserId, dataScope) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.campaigns(selectedUserId, dataScope) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.audit(selectedUserId, dataScope) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(selectedUserId, dataScope) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.managerReviews(null) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.managerOverview(null) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.myProfiles(null) }),
    ]);
  }

  const {
    takeReviewMutation,
    verifyReviewMutation,
    returnReviewMutation,
    bulkReturnReviewMutation,
    acceptHrMutation,
    returnHrMutation,
    bulkReturnHrMutation,
  } = useReviewMutations({
    selectedUserId,
    dataScope,
    onTakeSuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» взят на проверку.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onTakeError: () => setReviewActionProfileId(null),
    onReturnSuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» возвращен на доработку.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onReturnError: () => setReviewActionProfileId(null),
    onBulkReturnSuccess: async (result) => {
      setReviewMessage(`На доработку возвращено профилей: ${result.returned_count}.`);
      await refreshReviewViews();
    },
    onVerifySuccess: async (review) => {
      setReviewMessage(`Профиль сотрудника «${review.employee_name}» подтвержден.`);
      setReviewActionProfileId(null);
      await refreshReviewViews();
    },
    onVerifyError: () => setReviewActionProfileId(null),
    onAcceptHrSuccess: async (profile) => {
      setHrDecisionMessage(`Профиль сотрудника «${profile.employee_name}» принят HR.`);
      setHrDecisionProfileId(null);
      await refreshHrDecisionViews();
    },
    onAcceptHrError: () => setHrDecisionProfileId(null),
    onReturnHrSuccess: async (profile) => {
      setHrDecisionMessage(`Профиль сотрудника «${profile.employee_name}» возвращен на доработку.`);
      setHrDecisionProfileId(null);
      await refreshHrDecisionViews();
    },
    onReturnHrError: () => setHrDecisionProfileId(null),
    onBulkReturnHrSuccess: async (result) => {
      setHrDecisionMessage(`На доработку возвращено профилей: ${result.returned_count}.`);
      await refreshHrDecisionViews();
    },
  });

  function takeReview(profileId: number) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    takeReviewMutation.reset();
    takeReviewMutation.mutate(profileId);
  }

  function returnReview(profileId: number, reason: string) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    returnReviewMutation.reset();
    returnReviewMutation.mutate({ profileId, reason });
  }

  function bulkReturnReviewSelected(profileIds: number[], reason: string) {
    setReviewMessage(null);
    bulkReturnReviewMutation.reset();
    bulkReturnReviewMutation.mutate({ selection: { profile_ids: profileIds }, reason });
  }

  function bulkReturnReviewUnit(orgUnitId: number, reason: string) {
    setReviewMessage(null);
    bulkReturnReviewMutation.reset();
    bulkReturnReviewMutation.mutate({ selection: { org_unit_id: orgUnitId }, reason });
  }

  function verifyReview(profileId: number) {
    setReviewActionProfileId(profileId);
    setReviewMessage(null);
    verifyReviewMutation.reset();
    verifyReviewMutation.mutate(profileId);
  }

  function acceptByHr(profileId: number) {
    setHrDecisionProfileId(profileId);
    setHrDecisionMessage(null);
    acceptHrMutation.reset();
    acceptHrMutation.mutate(profileId);
  }

  function returnByHr(profileId: number, reason: string) {
    setHrDecisionProfileId(profileId);
    setHrDecisionMessage(null);
    returnHrMutation.reset();
    returnHrMutation.mutate({ profileId, reason });
  }

  function bulkReturnByHrSelected(profileIds: number[], reason: string) {
    setHrDecisionMessage(null);
    bulkReturnHrMutation.reset();
    bulkReturnHrMutation.mutate({ selection: { profile_ids: profileIds }, reason });
  }

  function bulkReturnByHrUnit(orgUnitId: number, reason: string) {
    setHrDecisionMessage(null);
    bulkReturnHrMutation.reset();
    bulkReturnHrMutation.mutate({ selection: { org_unit_id: orgUnitId }, reason });
  }

  return {
    acceptByHr,
    acceptHrMutation,
    bulkReturnByHrSelected,
    bulkReturnByHrUnit,
    bulkReturnHrMutation,
    bulkReturnReviewMutation,
    bulkReturnReviewSelected,
    bulkReturnReviewUnit,
    hrDecisionMessage,
    hrDecisionProfileId,
    returnByHr,
    returnHrMutation,
    returnReview,
    returnReviewMutation,
    reviewActionProfileId,
    reviewMessage,
    takeReview,
    takeReviewMutation,
    verifyReview,
    verifyReviewMutation,
  };
}
