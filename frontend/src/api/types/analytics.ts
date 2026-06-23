import type { Summary } from "./organization";
import type { ProfileQuestion, ProfileRevision } from "./profile";

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
  route_path: string[];
  route_current: string;
  route_reason: string;
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
