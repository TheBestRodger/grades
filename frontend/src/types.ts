export interface AiStatus {
  mode: string;
  provider: string;
  available: boolean;
  label: string;
  fallback_message: string;
  configuration?: AiConfiguration;
}

export interface Health {
  status: string;
  environment: string;
  ai: AiStatus;
}

export interface DemoUser {
  id: number;
  full_name: string;
  email: string;
  username: string | null;
  role: "hr" | "manager" | "employee";
  is_demo: boolean;
}

export interface AuthUser extends DemoUser {}

export interface MagicLinkResponse {
  email: string;
  delivery_mode: "local_link" | "email";
  expires_at: string;
  login_token: string | null;
  login_url: string | null;
  message: string;
}

export interface AuthSession {
  token: string;
  expires_at: string;
  user: AuthUser;
}

export interface AiAnswerCheckResult {
  profile_id: number;
  question_key: string;
  question_title: string;
  payload_policy: string;
  available: boolean;
  provider: string;
  model: string;
  clarity_threshold: number;
  clarity_percent: number;
  status: "accepted" | "needs_clarification";
  accepted: boolean;
  explanation: string;
  followup_question: string;
  raw_text: string;
}

export type AiConfigurationMode = "default" | "off" | "local" | "token";
export type AiProvider = "off" | "ollama" | "lm_studio" | "openai_compatible";

export interface AiConfiguration {
  mode: AiConfigurationMode;
  mode_label: string;
  provider: AiProvider;
  provider_label: string;
  base_url: string | null;
  model_name: string | null;
  api_token_configured: boolean;
  clarity_threshold: number;
  followup_strictness: "soft" | "balanced" | "strict";
  effective_mode: string;
  effective_provider: string;
  available: boolean;
  connection_status: string;
  note: string;
  updated_at: string | null;
  updated_by_id: number | null;
}

export interface AiConfigurationInput {
  mode: AiConfigurationMode;
  provider: AiProvider;
  base_url: string | null;
  model_name: string | null;
  api_token?: string | null;
  clear_api_token?: boolean;
  clarity_threshold: number;
  followup_strictness: "soft" | "balanced" | "strict";
}

export interface QuestionnaireQuestionSetting {
  question_key: string;
  section: string;
  title: string;
  input_type: "text" | "textarea" | "table";
  question: string;
  base_example: string;
  ai_check_enabled: boolean;
  good_example: string;
  bad_example: string | null;
  requirements: string | null;
  updated_at: string | null;
  updated_by_id: number | null;
}

export interface QuestionnaireSettings {
  scope: "global_current_questionnaire";
  versioning_status: "not_versioned_yet";
  questions: QuestionnaireQuestionSetting[];
}

export interface QuestionnaireQuestionSettingInput {
  question_key: string;
  ai_check_enabled: boolean;
  good_example: string | null;
  bad_example: string | null;
  requirements: string | null;
}

export interface QuestionnaireSettingsInput {
  questions: QuestionnaireQuestionSettingInput[];
}

export interface Assignment {
  id: number;
  employee_id: number;
  employee_name: string;
  fte: number;
  role: string;
}

export interface Position {
  id: number;
  title: string;
  position_code: string | null;
  approved_fte: number | null;
  assigned_fte: number | null;
  vacancy_fte: number | null;
  assignments: Assignment[];
}

export interface OrgNode {
  id: number;
  name: string;
  department_code: string | null;
  is_demo: boolean;
  positions: Position[];
  children: OrgNode[];
}

export interface Tree {
  scope: DemoUser["role"] | "work";
  nodes: OrgNode[];
}

export interface Summary {
  scope: string;
  employees: number;
  staffing_lines: number | null;
  approved_fte: number | null;
  assigned_fte: number | null;
  vacancy_fte: number | null;
}

export interface DemoResetResult {
  scope: "demo";
  before: Record<"demo" | "work", Record<string, number>>;
  after: Record<"demo" | "work", Record<string, number>>;
  work_unchanged: boolean;
}

export interface ManagerOption {
  assignment_id: number;
  employee_name: string;
  position_title: string;
  unit_name: string;
  is_demo?: boolean;
}

export interface NewEmployee {
  full_name: string;
  email: string;
  fte: number;
  system_role: "employee" | "manager";
  manager_assignment_id: number | null;
}

export interface BulkEmployeeResult {
  staffing_line_id: number;
  staffing_title: string;
  added: Array<{
    employee_id: number;
    assignment_id: number;
    full_name: string;
    email: string;
    username: string;
    password?: string;
    system_role?: "employee" | "manager";
    fte: number;
  }>;
  remaining_fte: number;
}

export interface WorkEmployeeImportResult {
  scope: "work";
  filename: string;
  sha256: string;
  rows: number;
  created_employees: number;
  updated_employees: number;
  created_assignments: number;
  updated_assignments: number;
}

export interface WorkStaffingEmployeeInput {
  full_name: string;
  email: string;
  fte: number;
  system_role: "employee" | "manager";
  manager_assignment_id?: number | null;
}

export interface WorkStaffingLineInput {
  title: string;
  approved_fte: number;
  employees: WorkStaffingEmployeeInput[];
}

export interface WorkStaffingLineResult {
  scope: "work";
  org_unit_id: number;
  org_unit_name: string;
  staffing_line_id: number;
  staffing_title: string;
  approved_fte: number;
  added: Array<{
    employee_id: number;
    assignment_id: number;
    full_name: string;
    email: string;
    fte: number;
    system_role: "employee" | "manager";
    manager_assignment_id: number | null;
  }>;
  remaining_fte: number;
}

export interface Campaign {
  id: number;
  scope: "demo" | "work";
  is_demo: boolean;
  name: string;
  status: string;
  due_at: string | null;
  participants_expected: number;
  total_participants_expected: number;
  active_wave_id: number | null;
  active_wave_name: string | null;
  waves: CampaignWave[];
  participant_assignment_ids: number[];
  selected_org_unit_ids: number[];
  selected_units_count: number;
  selected_staffing_lines: number;
  selected_approved_fte: number;
  status_counts: Record<string, number>;
  created_at: string | null;
  included_unit_name?: string;
  included_wave_id?: number;
  included_wave_name?: string;
  new_participants?: number;
  excluded_unit_name?: string;
  excluded_wave_id?: number;
  excluded_wave_name?: string;
  excluded_participants?: number;
  new_wave_id?: number;
  new_wave_name?: string;
  launched_wave_id?: number;
  launched_wave_name?: string;
  editing_wave_id?: number;
  editing_wave_name?: string;
  changed_participants?: number;
  participant_action?: "include" | "exclude";
}

export interface CampaignWave {
  id: number;
  campaign_id: number;
  name: string;
  status: string;
  status_label: string;
  can_edit: boolean;
  can_launch: boolean;
  due_at: string | null;
  participants_expected: number;
  participant_assignment_ids: number[];
  selected_org_unit_ids: number[];
  selected_units_count: number;
  selected_staffing_lines: number;
  selected_approved_fte: number;
  status_counts: Record<string, number>;
  created_at: string | null;
}

export interface AuditEvent {
  id: number;
  action: string;
  entity_type: string;
  details: Record<string, unknown>;
  created_at: string | null;
}

export interface DocumentGap {
  target_type: "staffing_line" | "org_unit";
  target_id: number;
  label: string;
  title?: string;
  unit_name?: string;
  name?: string;
  path?: string;
}

export interface DocumentCoverageItem {
  document_type: "job_instruction" | "unit_regulation" | "professional_standard";
  label: string;
  total: number;
  covered: number;
  missing: number;
  percent: number;
  gaps: DocumentGap[];
}

export interface DocumentLink {
  target_type: "staffing_line" | "org_unit";
  target_id: number;
  target_label: string;
  link_status: string;
  confirmed_at: string | null;
}

export interface DocumentRecord {
  id: number;
  document_code: string;
  document_type: "job_instruction" | "unit_regulation" | "professional_standard";
  document_type_label: string;
  title: string;
  version: string;
  document_status: string;
  ocr_quality_status: string;
  ocr_quality_label: string;
  has_stored_original: boolean;
  has_extracted_text: boolean;
  content_text: string | null;
  is_demo: boolean;
  created_at: string | null;
  links: DocumentLink[];
}

export interface DocumentMatrixCell {
  covered: boolean;
  documents: Array<{
    document_id: number;
    document_code: string;
    title: string;
    link_status: string;
  }>;
}

export interface DocumentPositionMatrixRow {
  staffing_line_id: number;
  position_title: string;
  unit_name: string;
  covered_count: number;
  required_count: number;
  coverage_percent: number;
  job_instruction: DocumentMatrixCell;
  unit_regulation: DocumentMatrixCell;
  professional_standard: DocumentMatrixCell;
}

export interface DocumentRegistry {
  scope: "demo" | "work";
  note: string;
  documents_total: number;
  confirmed_documents: number;
  ocr_quality_counts: Record<string, number>;
  coverage: {
    job_instruction: DocumentCoverageItem;
    unit_regulation: DocumentCoverageItem;
    professional_standard: DocumentCoverageItem;
  };
  position_matrix: DocumentPositionMatrixRow[];
  documents: DocumentRecord[];
}

export interface HrAnalytics {
  scope: "demo" | "work";
  note: string;
  structure: Summary;
  campaigns_total: number;
  active_campaigns: number;
  profiles_expected: number;
  average_progress_percent: number;
  profiles_with_revisions: number;
  revision_count: number;
  resubmitted_profiles: number;
  returned_profiles: number;
  return_events: number;
  accepted_profiles: number;
  funnel: Array<{
    status: string;
    label: string;
    count: number;
    percent: number;
  }>;
  units: Array<{
    unit_id: number;
    unit_name: string;
    profiles_expected: number;
    average_progress_percent: number;
    accepted: number;
    returned: number;
  }>;
  campaigns: Array<{
    id: number;
    name: string;
    status: string;
    participants_expected: number;
    active_wave_name: string | null;
    status_counts: Record<string, number>;
  }>;
  documents: {
    documents_total: number;
    confirmed_documents: number;
    ocr_quality_counts: Record<string, number>;
    coverage: Record<
      "job_instruction" | "unit_regulation" | "professional_standard",
      {
        label: string;
        total: number;
        covered: number;
        missing: number;
        percent: number;
      }
    >;
  };
}

export interface ProfileQuestion {
  key: string;
  section: string;
  title: string;
  question: string;
  example: string;
  input_type: "text" | "textarea" | "single_choice" | "table";
  quick_answers: string[];
  ai_check_enabled?: boolean;
  good_example?: string;
  bad_example?: string | null;
  requirements?: string | null;
  options?: Array<{
    label: string;
    description: string;
  }>;
  columns?: string[];
  rows?: number;
  row_labels?: string[];
}

export interface ProfileAssistedSections {
  checked_questions: string[];
  ignored_questions: string[];
  without_ai_questions?: string[];
  answer_statuses?: Record<string, "accepted" | "ignored" | "rejected" | "without_ai">;
}

export interface ProfileRevision {
  id: number;
  revision_no: number;
  submitted_at: string;
  assistant_mode: string;
  assistance_level: string;
  assisted_sections?: ProfileAssistedSections;
  answers: Record<string, string>;
}

export interface ProfileReviewEvent {
  id: number;
  revision_no: number;
  action: "taken" | "returned" | "verified" | "hr_returned" | "hr_accepted";
  comment: string | null;
  actor_name: string;
  created_at: string | null;
}

export interface EmployeeProfile {
  id: number;
  campaign_id: number;
  campaign_name: string;
  assignment_id: number;
  position_title: string;
  unit_name: string;
  workflow_status: string;
  progress_percent: number;
  answers: Record<string, string>;
  draft_assisted_sections?: ProfileAssistedSections;
  can_edit: boolean;
  questions: ProfileQuestion[];
  review_events: ProfileReviewEvent[];
  revisions: ProfileRevision[];
}

export interface ManagerReviewProfile {
  id: number;
  employee_name: string;
  position_title: string;
  org_unit_id: number;
  unit_name: string;
  campaign_name: string;
  workflow_status: string;
  progress_percent: number;
  questions: ProfileQuestion[];
  revision_count: number;
  latest_revision: ProfileRevision | null;
  review_events: ProfileReviewEvent[];
  can_take: boolean;
  can_decide: boolean;
  returned_by_hr: boolean;
}

export interface HrReviewProfile {
  id: number;
  employee_name: string;
  position_title: string;
  org_unit_id: number;
  unit_name: string;
  campaign_name: string;
  workflow_status: string;
  progress_percent: number;
  questions: ProfileQuestion[];
  latest_revision: ProfileRevision | null;
  review_events: ProfileReviewEvent[];
  can_decide: boolean;
}

export interface BulkReviewReturnResult {
  selection: "profiles" | "org_unit";
  org_unit_id: number | null;
  profile_ids: number[];
  returned_count: number;
  reason: string;
}

export interface DocumentAnomalyCheck {
  document_type: "job_instruction" | "unit_regulation" | "professional_standard";
  label: string;
  risk_level: "normal" | "attention" | "critical";
  score: number;
  documents: Array<{
    document_id: number;
    document_code: string;
    title: string;
    ocr_quality_status: string;
    text_excerpt?: string;
  }>;
  matched_terms: string[];
  reason: string;
}

export interface ProfileDocumentSignal {
  risk_level: "normal" | "attention" | "critical";
  risk_label: string;
  risk_reason: string;
  checks: DocumentAnomalyCheck[];
}

export interface ManagerProfileSignal {
  profile_id: number;
  employee_name: string;
  position_title: string;
  unit_name: string;
  campaign_name: string;
  workflow_status: string;
  workflow_status_label: string;
  progress_percent: number;
  return_count: number;
  risk_level: "normal" | "attention" | "critical";
  risk_label: string;
  risk_reason: string;
  workflow_risk_level: "normal" | "attention" | "critical";
  workflow_risk_reason: string;
  document_signal: ProfileDocumentSignal;
  questions: ProfileQuestion[];
  latest_revision: ProfileRevision | null;
}

export interface ManagerOverviewUnit {
  unit_id: number;
  unit_name: string;
  total: number;
  quality_score: number;
  quality_percent: number;
  heat_level: "green" | "yellow" | "red";
  heat_label: string;
  risk_counts: Record<string, number>;
  status_counts: Record<string, number>;
  profiles: ManagerProfileSignal[];
}

export interface ManagerOverview {
  scope: "manager_subtree";
  campaign_id: number | null;
  campaign_name: string | null;
  total_profiles: number;
  risk_counts: Record<string, number>;
  status_counts: Record<string, number>;
  status_labels: Record<string, string>;
  units: ManagerOverviewUnit[];
}
