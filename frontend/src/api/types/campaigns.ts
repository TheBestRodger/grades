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
