import { request } from "./request";
import { API_URL } from "./urls";
import type { Campaign } from "./types";

export const getCampaigns = (userId: number, scope: "demo" | "work" = "demo") =>
  request<Campaign[]>(API_URL.campaigns.list(scope), { userId });

export const createCampaign = (userId: number, name: string, dueAt: string | null, scope: "demo" | "work" = "demo") =>
  request<Campaign>(API_URL.campaigns.list(scope), {
    userId,
    method: "POST",
    body: { name, due_at: dueAt || null },
  });

export const createCampaignWave = (
  userId: number,
  campaignId: number,
  name: string,
  dueAt: string | null,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.waves(scope, campaignId), {
    userId,
    method: "POST",
    body: { name, due_at: dueAt || null },
  });

export const launchCampaignWave = (
  userId: number,
  campaignId: number,
  waveId: number,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.launchWave(scope, campaignId, waveId), {
    userId,
    method: "POST",
  });

export const editCampaignWave = (
  userId: number,
  campaignId: number,
  waveId: number,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.editWave(scope, campaignId, waveId), {
    userId,
    method: "POST",
  });

export const includeBranch = (
  userId: number,
  campaignId: number,
  orgUnitId: number,
  waveId?: number | null,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.includeBranch(scope, campaignId, orgUnitId, waveId), {
    userId,
    method: "POST",
  });

export const excludeBranch = (
  userId: number,
  campaignId: number,
  orgUnitId: number,
  waveId?: number | null,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.excludeBranch(scope, campaignId, orgUnitId, waveId), {
    userId,
    method: "POST",
  });

export const setCampaignAssignments = (
  userId: number,
  campaignId: number,
  waveId: number,
  assignmentIds: number[],
  action: "include" | "exclude",
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(API_URL.campaigns.assignments(scope, campaignId, waveId), {
    userId,
    method: "PUT",
    body: { assignment_ids: assignmentIds, action },
  });
