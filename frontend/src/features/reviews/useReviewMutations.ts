import { useMutation } from "@tanstack/react-query";

import {
  acceptProfileByHr,
  bulkReturnProfilesByHr,
  bulkReturnProfilesForRevision,
  returnProfileByHr,
  returnProfileForRevision,
  takeProfileForReview,
  verifyProfileByManager,
} from "../../api";
import type { DataScope } from "../../app/navigation";
import type { BulkReviewReturnResult, HrReviewProfile, ManagerReviewProfile } from "../../types";

interface ReviewMutationOptions {
  selectedUserId: number | null;
  dataScope: DataScope;
  onTakeSuccess?: (review: ManagerReviewProfile) => void | Promise<void>;
  onTakeError?: () => void;
  onVerifySuccess?: (review: ManagerReviewProfile) => void | Promise<void>;
  onVerifyError?: () => void;
  onReturnSuccess?: (review: ManagerReviewProfile) => void | Promise<void>;
  onReturnError?: () => void;
  onBulkReturnSuccess?: (result: BulkReviewReturnResult) => void | Promise<void>;
  onAcceptHrSuccess?: (profile: HrReviewProfile) => void | Promise<void>;
  onAcceptHrError?: () => void;
  onReturnHrSuccess?: (profile: HrReviewProfile) => void | Promise<void>;
  onReturnHrError?: () => void;
  onBulkReturnHrSuccess?: (result: BulkReviewReturnResult) => void | Promise<void>;
}

export function useReviewMutations(options: ReviewMutationOptions) {
  const takeReviewMutation = useMutation({
    mutationFn: (profileId: number) => takeProfileForReview(options.selectedUserId!, profileId),
    onSuccess: options.onTakeSuccess,
    onError: options.onTakeError,
  });
  const verifyReviewMutation = useMutation({
    mutationFn: (profileId: number) => verifyProfileByManager(options.selectedUserId!, profileId),
    onSuccess: options.onVerifySuccess,
    onError: options.onVerifyError,
  });
  const returnReviewMutation = useMutation({
    mutationFn: ({ profileId, reason }: { profileId: number; reason: string }) =>
      returnProfileForRevision(options.selectedUserId!, profileId, reason),
    onSuccess: options.onReturnSuccess,
    onError: options.onReturnError,
  });
  const bulkReturnReviewMutation = useMutation({
    mutationFn: ({ selection, reason }: { selection: { profile_ids?: number[]; org_unit_id?: number }; reason: string }) =>
      bulkReturnProfilesForRevision(options.selectedUserId!, selection, reason),
    onSuccess: options.onBulkReturnSuccess,
  });
  const acceptHrMutation = useMutation({
    mutationFn: (profileId: number) => acceptProfileByHr(options.selectedUserId!, profileId, options.dataScope),
    onSuccess: options.onAcceptHrSuccess,
    onError: options.onAcceptHrError,
  });
  const returnHrMutation = useMutation({
    mutationFn: ({ profileId, reason }: { profileId: number; reason: string }) =>
      returnProfileByHr(options.selectedUserId!, profileId, reason, options.dataScope),
    onSuccess: options.onReturnHrSuccess,
    onError: options.onReturnHrError,
  });
  const bulkReturnHrMutation = useMutation({
    mutationFn: ({ selection, reason }: { selection: { profile_ids?: number[]; org_unit_id?: number }; reason: string }) =>
      bulkReturnProfilesByHr(options.selectedUserId!, selection, reason, options.dataScope),
    onSuccess: options.onBulkReturnHrSuccess,
  });

  return {
    takeReviewMutation,
    verifyReviewMutation,
    returnReviewMutation,
    bulkReturnReviewMutation,
    acceptHrMutation,
    returnHrMutation,
    bulkReturnHrMutation,
  };
}
