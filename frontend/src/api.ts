import type {
  AuditEvent,
  AiConfiguration,
  AiConfigurationInput,
  AiAnswerCheckResult,
  AuthSession,
  AuthUser,
  BulkEmployeeResult,
  Campaign,
  DemoUser,
  DemoResetResult,
  DocumentRegistry,
  EmployeeProfile,
  BulkReviewReturnResult,
  Health,
  HrAnalytics,
  HrReviewProfile,
  MagicLinkResponse,
  ManagerOverview,
  ManagerReviewProfile,
  ManagerOption,
  NewEmployee,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
  Summary,
  Tree,
  WorkEmployeeImportResult,
  WorkStaffingLineInput,
  WorkStaffingLineResult,
  StructureDeleteResult,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function storedAuthToken(): string | null {
  return window.localStorage.getItem("auth_token");
}

function authHeaders(): Record<string, string> {
  const token = storedAuthToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(
  url: string,
  options: { userId?: number; method?: "DELETE" | "GET" | "POST" | "PUT"; body?: unknown } = {},
): Promise<T> {
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers: {
      ...authHeaders(),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(payload?.detail ?? `Request failed: ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export const getHealth = () => request<Health>("/api/health");
export const getDemoUsers = () => request<DemoUser[]>("/api/demo/users");
export const getMe = () => request<AuthUser>("/api/me");
export const loginWithPassword = (username: string, password: string) =>
  request<AuthSession>("/api/auth/login", {
    method: "POST",
    body: { username, password },
  });
export const requestMagicLink = (email: string) =>
  request<MagicLinkResponse>("/api/auth/magic-link/request", {
    method: "POST",
    body: { email },
  });
export const consumeMagicLink = (token: string) =>
  request<AuthSession>("/api/auth/magic-link/consume", {
    method: "POST",
    body: { token },
  });
export const logoutAuth = () =>
  request<{ revoked: boolean }>("/api/auth/logout", {
    method: "POST",
  });
export const getAiSettings = (userId: number) =>
  request<AiConfiguration>("/api/hr/settings/ai", { userId });
export const updateAiSettings = (userId: number, payload: AiConfigurationInput) =>
  request<AiConfiguration>("/api/hr/settings/ai", {
    userId,
    method: "PUT",
    body: payload,
  });
export const getQuestionnaireSettings = (userId: number) =>
  request<QuestionnaireSettings>("/api/hr/settings/questionnaire", { userId });
export const updateQuestionnaireSettings = (userId: number, payload: QuestionnaireSettingsInput) =>
  request<QuestionnaireSettings>("/api/hr/settings/questionnaire", {
    userId,
    method: "PUT",
    body: payload,
  });
export const getTree = (userId: number) =>
  request<Tree>("/api/organization/tree", { userId });
export const getSummary = (userId: number) =>
  request<Summary>("/api/organization/summary", { userId });
export const getWorkTree = (userId: number) =>
  request<Tree>("/api/work/organization/tree", { userId });
export const getWorkSummary = (userId: number) =>
  request<Summary>("/api/work/organization/summary", { userId });
export const getManagerOptions = (userId: number, scope: "demo" | "work" = "demo") =>
  request<ManagerOption[]>(scope === "work" ? "/api/work/hr/managers" : "/api/hr/managers", { userId });
export const resetDemoData = (userId: number) =>
  request<DemoResetResult>("/api/hr/demo-reset", { userId, method: "POST" });
export const bulkAddEmployees = (
  userId: number,
  staffingLineId: number,
  employees: NewEmployee[],
  scope: "demo" | "work" = "demo",
) =>
  request<BulkEmployeeResult>(
    `${scope === "work" ? "/api/work/hr" : "/api/hr"}/staffing-lines/${staffingLineId}/employees/bulk`,
    {
    userId,
    method: "POST",
    body: { employees },
    },
  );
export const importWorkEmployees = async (_userId: number, file: File) => {
  const response = await fetch(`/api/work/hr/employees/import?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as WorkEmployeeImportResult;
};
export const createWorkStaffingLine = (
  userId: number,
  orgUnitId: number,
  payload: WorkStaffingLineInput,
) =>
  request<WorkStaffingLineResult>(`/api/work/hr/org-units/${orgUnitId}/staffing-lines`, {
    userId,
    method: "POST",
    body: payload,
  });
export const deleteWorkAssignment = (userId: number, assignmentId: number, force = false) =>
  request<StructureDeleteResult>(`/api/work/hr/assignments/${assignmentId}${force ? "?force=true" : ""}`, {
    userId,
    method: "DELETE",
  });
export const deleteWorkStaffingLine = (userId: number, staffingLineId: number, force = false) =>
  request<StructureDeleteResult>(`/api/work/hr/staffing-lines/${staffingLineId}${force ? "?force=true" : ""}`, {
    userId,
    method: "DELETE",
  });
export const getCampaigns = (userId: number, scope: "demo" | "work" = "demo") =>
  request<Campaign[]>(scope === "work" ? "/api/work/hr/campaigns" : "/api/hr/campaigns", { userId });
export const createCampaign = (userId: number, name: string, dueAt: string | null, scope: "demo" | "work" = "demo") =>
  request<Campaign>(scope === "work" ? "/api/work/hr/campaigns" : "/api/hr/campaigns", {
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
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/waves`, {
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
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/waves/${waveId}/launch`, {
    userId,
    method: "POST",
  });
export const editCampaignWave = (
  userId: number,
  campaignId: number,
  waveId: number,
  scope: "demo" | "work" = "demo",
) =>
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/waves/${waveId}/edit`, {
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
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/include-unit/${orgUnitId}${waveId ? `?wave_id=${waveId}` : ""}`, {
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
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/exclude-unit/${orgUnitId}${waveId ? `?wave_id=${waveId}` : ""}`, {
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
  request<Campaign>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/campaigns/${campaignId}/waves/${waveId}/assignments`, {
    userId,
    method: "PUT",
    body: { assignment_ids: assignmentIds, action },
  });
export const getRecentAudit = (userId: number, scope: "demo" | "work" = "demo") =>
  request<AuditEvent[]>(scope === "work" ? "/api/work/hr/audit/recent" : "/api/hr/audit/recent", { userId });
export const getHrAnalytics = (userId: number, scope: "demo" | "work" = "demo") =>
  request<HrAnalytics>(scope === "work" ? "/api/work/hr/analytics" : "/api/hr/analytics", { userId });
export const getHrDocuments = (userId: number, scope: "demo" | "work" = "demo") =>
  request<DocumentRegistry>(scope === "work" ? "/api/work/hr/documents" : "/api/hr/documents", { userId });
export const getManagerDocuments = (userId: number) =>
  request<DocumentRegistry>("/api/manager/documents", { userId });
export const setWorkDocumentLink = (
  userId: number,
  staffingLineId: number,
  documentType: "job_instruction" | "unit_regulation" | "professional_standard",
  documentId: number | null,
) =>
  request<DocumentRegistry>("/api/work/hr/documents/link", {
    userId,
    method: "PUT",
    body: {
      staffing_line_id: staffingLineId,
      document_type: documentType,
      document_id: documentId,
    },
  });
export const uploadWorkDocument = async (
  _userId: number,
  file: File,
  metadata: {
    documentCode: string;
    documentType: "job_instruction" | "unit_regulation" | "professional_standard";
    title: string;
    version: string;
  },
) => {
  const query = new URLSearchParams({
    filename: file.name,
    document_code: metadata.documentCode,
    document_type: metadata.documentType,
    title: metadata.title,
    version: metadata.version,
  });
  const response = await fetch(`/api/work/hr/documents/upload?${query.toString()}`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as DocumentRegistry;
};
export const reviewWorkDocumentQuality = (
  userId: number,
  documentId: number,
  ocrQualityStatus: "good" | "warning",
  extractedText: string,
) =>
  request<DocumentRegistry>(`/api/work/hr/documents/${documentId}/quality`, {
    userId,
    method: "PUT",
    body: { ocr_quality_status: ocrQualityStatus, extracted_text: extractedText },
  });
export const downloadWorkDocumentSource = async (_userId: number, documentId: number) => {
  const response = await fetch(`/api/work/hr/documents/${documentId}/source`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const matchedFilename = disposition.match(/filename="([^"]+)"/)?.[1];
  link.download = matchedFilename ?? `document_${documentId}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
export const downloadHrExport = async (
  _userId: number,
  kind: "profiles" | "campaigns",
  format: "csv" | "json",
) => {
  const response = await fetch(`/api/hr/exports/${kind}.${format}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${kind}_export.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
export const downloadCredentialsExport = async (
  rows: Array<{
    full_name: string;
    email: string;
    username: string;
    password: string;
    role?: string;
    position?: string;
  }>,
) => {
  const response = await fetch("/api/hr/exports/credentials.xlsx", {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ rows }),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "credentials.xlsx";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const issueWaveCredentialsExport = async (
  _userId: number,
  scope: "demo" | "work",
  campaignId: number,
  waveId: number,
): Promise<Blob> => {
  const prefix = scope === "work" ? "/api/work/hr" : "/api/hr";
  const response = await fetch(`${prefix}/campaigns/${campaignId}/waves/${waveId}/credentials.xlsx`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  return response.blob();
};
export const getMyProfiles = (userId: number) =>
  request<EmployeeProfile[]>("/api/my/profiles", { userId });
export const saveProfileDraft = (
  userId: number,
  profileId: number,
  answers: Record<string, string>,
  aiUsage?: {
    ai_checked_questions?: string[];
    ai_ignored_questions?: string[];
    ai_without_ai_questions?: string[];
    ai_answer_statuses?: Record<string, "accepted" | "ignored" | "rejected" | "without_ai">;
  },
) =>
  request<EmployeeProfile>(`/api/my/profiles/${profileId}/draft`, {
    userId,
    method: "PUT",
    body: { answers, ...(aiUsage ?? {}) },
  });
export const submitProfile = (
  userId: number,
  profileId: number,
  answers: Record<string, string>,
  aiUsage?: {
    ai_checked_questions?: string[];
    ai_ignored_questions?: string[];
    ai_without_ai_questions?: string[];
    ai_answer_statuses?: Record<string, "accepted" | "ignored" | "rejected" | "without_ai">;
  },
) =>
  request<EmployeeProfile>(`/api/my/profiles/${profileId}/submit`, {
    userId,
    method: "POST",
    body: { answers, ...(aiUsage ?? {}) },
  });
export const downloadProfileTemplateExport = async (_userId: number, profileId: number) => {
  const response = await fetch(`/api/my/profiles/${profileId}/export.xlsx`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `profile_${profileId}_template.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
export const checkProfileAnswer = (
  userId: number,
  profileId: number,
  questionKey: string,
  answers: Record<string, string>,
  previous?: {
    previous_answer?: string | null;
    previous_followup_question?: string | null;
    previous_clarity_percent?: number | null;
  },
) =>
  request<AiAnswerCheckResult>(`/api/my/profiles/${profileId}/ai-check`, {
    userId,
    method: "POST",
    body: { question_key: questionKey, answers, ...(previous ?? {}) },
  });
export const getManagerReviews = (userId: number) =>
  request<ManagerReviewProfile[]>("/api/manager/reviews", { userId });
export const getManagerOverview = (userId: number) =>
  request<ManagerOverview>("/api/manager/overview", { userId });
export const takeProfileForReview = (userId: number, profileId: number) =>
  request<ManagerReviewProfile>(`/api/manager/reviews/${profileId}/take`, {
    userId,
    method: "POST",
  });
export const returnProfileForRevision = (userId: number, profileId: number, reason: string) =>
  request<ManagerReviewProfile>(`/api/manager/reviews/${profileId}/return`, {
    userId,
    method: "POST",
    body: { reason },
  });
export const bulkReturnProfilesForRevision = (
  userId: number,
  selection: { profile_ids?: number[]; org_unit_id?: number },
  reason: string,
) =>
  request<BulkReviewReturnResult>("/api/manager/reviews/bulk-return", {
    userId,
    method: "POST",
    body: { ...selection, reason },
  });
export const verifyProfileByManager = (
  userId: number,
  profileId: number,
  comment: string | null = null,
) =>
  request<ManagerReviewProfile>(`/api/manager/reviews/${profileId}/verify`, {
    userId,
    method: "POST",
    body: { comment },
  });
export const getHrProfileReviews = (userId: number, scope: "demo" | "work" = "demo") =>
  request<HrReviewProfile[]>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/profile-reviews`, { userId });
export const acceptProfileByHr = (userId: number, profileId: number, scope: "demo" | "work" = "demo") =>
  request<HrReviewProfile>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/profile-reviews/${profileId}/accept`, {
    userId,
    method: "POST",
    body: { comment: null },
  });
export const returnProfileByHr = (userId: number, profileId: number, reason: string, scope: "demo" | "work" = "demo") =>
  request<HrReviewProfile>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/profile-reviews/${profileId}/return`, {
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
  request<BulkReviewReturnResult>(`${scope === "work" ? "/api/work/hr" : "/api/hr"}/profile-reviews/bulk-return`, {
    userId,
    method: "POST",
    body: { ...selection, reason },
  });
