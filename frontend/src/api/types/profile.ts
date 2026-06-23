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

export type ProfileAnswerStatus =
  | "accepted"
  | "rejected"
  | "ignored"
  | "without_ai"
  | "ignored_ai"
  | "filled_without_ai";

export interface ProfileAssistedSections {
  checked_questions: string[];
  ignored_questions: string[];
  without_ai_questions?: string[];
  answer_statuses?: Record<string, ProfileAnswerStatus>;
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
  route_path: string[];
  route_current: string;
  route_reason: string;
  answers: Record<string, string>;
  draft_assisted_sections?: ProfileAssistedSections;
  can_edit: boolean;
  questions: ProfileQuestion[];
  review_events: ProfileReviewEvent[];
  revisions: ProfileRevision[];
}
