import type { DataScope } from "../app/navigation";

export const queryKeys = {
  health: () => ["health"] as const,
  authMe: (authToken: string | null) => ["me", authToken] as const,
  summary: (userId: number | null) => ["summary", userId] as const,
  tree: (userId: number | null) => ["tree", userId] as const,
  workTree: (userId: number | null) => ["work-tree", userId] as const,
  workSummary: (userId: number | null) => ["work-summary", userId] as const,
  managers: (userId: number | null) => ["managers", userId] as const,
  workManagers: (userId: number | null) => ["work-managers", userId] as const,
  campaigns: (userId: number | null, scope?: DataScope) =>
    scope ? (["campaigns", userId, scope] as const) : (["campaigns", userId] as const),
  audit: (userId: number | null, scope?: DataScope) =>
    scope ? (["audit", userId, scope] as const) : (["audit", userId] as const),
  hrAnalytics: (userId: number | null, scope?: DataScope) =>
    scope ? (["hr-analytics", userId, scope] as const) : (["hr-analytics", userId] as const),
  aiSettings: (userId: number | null) => ["ai-settings", userId] as const,
  questionnaireSettings: (userId: number | null) => ["questionnaire-settings", userId] as const,
  hrReviews: (userId: number | null, scope?: DataScope) =>
    scope ? (["hr-profile-reviews", userId, scope] as const) : (["hr-profile-reviews", userId] as const),
  hrDocuments: (userId: number | null, scope?: DataScope) =>
    scope ? (["hr-documents", userId, scope] as const) : (["hr-documents", userId] as const),
  myProfiles: (userId: number | null) => ["my-profiles", userId] as const,
  managerReviews: (userId: number | null) => ["manager-reviews", userId] as const,
  managerOverview: (userId: number | null) => ["manager-overview", userId] as const,
  managerDocuments: (userId: number | null) => ["manager-documents", userId] as const,
  demoUsers: () => ["demo-users"] as const,
  notifications: (userId: number | null) => ["notifications", userId] as const,
  notificationUnreadCount: (userId: number | null) =>
    ["notification-unread-count", userId] as const,
};
