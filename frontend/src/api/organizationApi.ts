import { request } from "./request";
import { API_URL } from "./urls";
import type { ManagerOption, Summary, Tree } from "./types";

export const getTree = (userId: number) => request<Tree>(API_URL.organization.tree, { userId });

export const getSummary = (userId: number) => request<Summary>(API_URL.organization.summary, { userId });

export const getWorkTree = (userId: number) => request<Tree>(API_URL.organization.workTree, { userId });

export const getWorkSummary = (userId: number) => request<Summary>(API_URL.organization.workSummary, { userId });

export const getManagerOptions = (userId: number, scope: "demo" | "work" = "demo") =>
  request<ManagerOption[]>(API_URL.organization.managerOptions(scope), { userId });
