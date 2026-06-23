import type { ProfileQuestion, ProfileRevision, ProfileReviewEvent } from "./profile";

export interface ManagerReviewProfile {
  id: number;
  employee_name: string;
  position_title: string;
  org_unit_id: number;
  unit_name: string;
  campaign_name: string;
  workflow_status: string;
  progress_percent: number;
  route_path: string[];
  route_current: string;
  route_reason: string;
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
  route_path: string[];
  route_current: string;
  route_reason: string;
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
