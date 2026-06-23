import { request } from "./request";
import { API_URL } from "./urls";
import type { DemoResetResult, DemoUser } from "./types";

export const getDemoUsers = () => request<DemoUser[]>(API_URL.demo.users);

export const resetDemoData = (userId: number) =>
  request<DemoResetResult>(API_URL.demo.reset, { userId, method: "POST" });
