import { request } from "./request";
import { API_URL } from "./urls";
import type { BulkReviewReturnResult, HrReviewProfile } from "./types";

export const getHrProfileReviews = (userId: number, scope: "demo" | "work" = "demo") =>
  request<HrReviewProfile[]>(API_URL.hrReview.list(scope), { userId });

export const acceptProfileByHr = (userId: number, profileId: number, scope: "demo" | "work" = "demo") =>
  request<HrReviewProfile>(API_URL.hrReview.accept(scope, profileId), {
    userId,
    method: "POST",
    body: { comment: null },
  });

export const returnProfileByHr = (
  userId: number,
  profileId: number,
  reason: string,
  scope: "demo" | "work" = "demo",
) =>
  request<HrReviewProfile>(API_URL.hrReview.return(scope, profileId), {
    userId,
    method: "POST",
    body: { reason },
  });

export const bulkReturnProfilesByHr = (
  userId: number,
  selection: { profile_ids?: number[]; org_unit_id?: number },
  reason: string,
  scope: "demo" | "work" = "demo",
) =>
  request<BulkReviewReturnResult>(API_URL.hrReview.bulkReturn(scope), {
    userId,
    method: "POST",
    body: { ...selection, reason },
  });
