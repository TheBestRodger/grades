import { request } from "./request";
import { API_URL } from "./urls";
import type { AuditEvent } from "./types";

export const getRecentAudit = (userId: number, scope: "demo" | "work" = "demo") =>
  request<AuditEvent[]>(API_URL.audit.recent(scope), { userId });
