export type ApiScope = "demo" | "work";

export const hrPrefix = (scope: ApiScope = "demo") => (scope === "work" ? "/api/work/hr" : "/api/hr");

export const API_URL = {
  system: {
    health: "/api/health",
  },
  demo: {
    users: "/api/demo/users",
    reset: "/api/hr/demo-reset",
  },
  auth: {
    me: "/api/me",
    login: "/api/auth/login",
    logout: "/api/auth/logout",
    requestMagicLink: "/api/auth/magic-link/request",
    consumeMagicLink: "/api/auth/magic-link/consume",
  },
  notifications: {
    list: (limit = 50) => `/api/notifications?limit=${limit}`,
    unreadCount: "/api/notifications/unread-count",
    read: (notificationId: number) => `/api/notifications/${notificationId}/read`,
    readAll: "/api/notifications/read-all",
  },
  settings: {
    ai: "/api/hr/settings/ai",
    questionnaire: "/api/hr/settings/questionnaire",
  },
  organization: {
    tree: "/api/organization/tree",
    summary: "/api/organization/summary",
    workTree: "/api/work/organization/tree",
    workSummary: "/api/work/organization/summary",
    managerOptions: (scope: ApiScope = "demo") => (scope === "work" ? "/api/work/hr/managers" : "/api/hr/managers"),
  },
  structure: {
    staffingLineEmployeesBulk: (scope: ApiScope, staffingLineId: number) =>
      `${hrPrefix(scope)}/staffing-lines/${staffingLineId}/employees/bulk`,
    assignmentEmployee: (scope: ApiScope, assignmentId: number) => `${hrPrefix(scope)}/assignments/${assignmentId}/employee`,
    assignmentPasswordReset: (scope: ApiScope, assignmentId: number) =>
      `${hrPrefix(scope)}/assignments/${assignmentId}/password/reset`,
    importWorkEmployees: (filename: string) => `/api/work/hr/employees/import?filename=${encodeURIComponent(filename)}`,
    createWorkStaffingLine: (orgUnitId: number) => `/api/work/hr/org-units/${orgUnitId}/staffing-lines`,
    deleteWorkAssignment: (assignmentId: number, force = false) =>
      `/api/work/hr/assignments/${assignmentId}${force ? "?force=true" : ""}`,
    deleteWorkStaffingLine: (staffingLineId: number, force = false) =>
      `/api/work/hr/staffing-lines/${staffingLineId}${force ? "?force=true" : ""}`,
  },
  campaigns: {
    list: (scope: ApiScope = "demo") => `${hrPrefix(scope)}/campaigns`,
    waves: (scope: ApiScope, campaignId: number) => `${hrPrefix(scope)}/campaigns/${campaignId}/waves`,
    launchWave: (scope: ApiScope, campaignId: number, waveId: number) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/waves/${waveId}/launch`,
    editWave: (scope: ApiScope, campaignId: number, waveId: number) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/waves/${waveId}/edit`,
    includeBranch: (scope: ApiScope, campaignId: number, orgUnitId: number, waveId?: number | null) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/include-unit/${orgUnitId}${waveId ? `?wave_id=${waveId}` : ""}`,
    excludeBranch: (scope: ApiScope, campaignId: number, orgUnitId: number, waveId?: number | null) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/exclude-unit/${orgUnitId}${waveId ? `?wave_id=${waveId}` : ""}`,
    assignments: (scope: ApiScope, campaignId: number, waveId: number) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/waves/${waveId}/assignments`,
    waveCredentials: (scope: ApiScope, campaignId: number, waveId: number) =>
      `${hrPrefix(scope)}/campaigns/${campaignId}/waves/${waveId}/credentials.xlsx`,
  },
  audit: {
    recent: (scope: ApiScope = "demo") => `${hrPrefix(scope)}/audit/recent`,
  },
  analytics: {
    hr: (scope: ApiScope = "demo") => `${hrPrefix(scope)}/analytics`,
    managerOverview: "/api/manager/overview",
  },
  documents: {
    hr: (scope: ApiScope = "demo") => `${hrPrefix(scope)}/documents`,
    manager: "/api/manager/documents",
    workLink: "/api/work/hr/documents/link",
    workUpload: (query: URLSearchParams) => `/api/work/hr/documents/upload?${query.toString()}`,
    workQuality: (documentId: number) => `/api/work/hr/documents/${documentId}/quality`,
    workSource: (documentId: number) => `/api/work/hr/documents/${documentId}/source`,
  },
  exports: {
    hr: (kind: "profiles" | "campaigns", format: "csv" | "json") => `/api/hr/exports/${kind}.${format}`,
    credentials: "/api/hr/exports/credentials.xlsx",
    profileTemplate: (profileId: number) => `/api/my/profiles/${profileId}/export.xlsx`,
  },
  profile: {
    myProfiles: "/api/my/profiles",
    draft: (profileId: number) => `/api/my/profiles/${profileId}/draft`,
    submit: (profileId: number) => `/api/my/profiles/${profileId}/submit`,
    aiCheck: (profileId: number) => `/api/my/profiles/${profileId}/ai-check`,
  },
  managerReview: {
    list: "/api/manager/reviews",
    take: (profileId: number) => `/api/manager/reviews/${profileId}/take`,
    return: (profileId: number) => `/api/manager/reviews/${profileId}/return`,
    bulkReturn: "/api/manager/reviews/bulk-return",
    verify: (profileId: number) => `/api/manager/reviews/${profileId}/verify`,
  },
  hrReview: {
    list: (scope: ApiScope = "demo") => `${hrPrefix(scope)}/profile-reviews`,
    accept: (scope: ApiScope, profileId: number) => `${hrPrefix(scope)}/profile-reviews/${profileId}/accept`,
    return: (scope: ApiScope, profileId: number) => `${hrPrefix(scope)}/profile-reviews/${profileId}/return`,
    bulkReturn: (scope: ApiScope) => `${hrPrefix(scope)}/profile-reviews/bulk-return`,
  },
};
