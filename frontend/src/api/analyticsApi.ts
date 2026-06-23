import { request } from "./request";
import { API_URL } from "./urls";
import type { HrAnalytics, ManagerOverview } from "./types";

export const getHrAnalytics = (userId: number, scope: "demo" | "work" = "demo") =>
  request<HrAnalytics>(API_URL.analytics.hr(scope), { userId });

export const getManagerOverview = (userId: number) =>
  request<ManagerOverview>(API_URL.analytics.managerOverview, { userId });
