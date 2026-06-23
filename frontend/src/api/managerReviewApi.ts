import { request } from "./request";
import { API_URL } from "./urls";
import type { BulkReviewReturnResult, ManagerReviewProfile } from "./types";

export const getManagerReviews = (userId: number) =>
  request<ManagerReviewProfile[]>(API_URL.managerReview.list, { userId });

export const takeProfileForReview = (userId: number, profileId: number) =>
  request<ManagerReviewProfile>(API_URL.managerReview.take(profileId), {
    userId,
    method: "POST",
  });

export const returnProfileForRevision = (userId: number, profileId: number, reason: string) =>
  request<ManagerReviewProfile>(API_URL.managerReview.return(profileId), {
    userId,
    method: "POST",
    body: { reason },
  });

export const bulkReturnProfilesForRevision = (
  userId: number,
  selection: { profile_ids?: number[]; org_unit_id?: number },
  reason: string,
) =>
  request<BulkReviewReturnResult>(API_URL.managerReview.bulkReturn, {
    userId,
    method: "POST",
    body: { ...selection, reason },
  });

export const verifyProfileByManager = (userId: number, profileId: number, comment: string | null = null) =>
  request<ManagerReviewProfile>(API_URL.managerReview.verify(profileId), {
    userId,
    method: "POST",
    body: { comment },
  });
