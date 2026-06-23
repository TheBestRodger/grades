export interface NewEmployee {
  full_name: string;
  email: string;
  fte: number;
  system_role: "employee" | "manager";
  is_hr: boolean;
  manager_assignment_id: number | null;
}

export interface EmployeeAssignmentUpdate {
  full_name: string;
  email: string;
  system_role: "employee" | "manager";
  is_hr: boolean;
}

export interface EmployeeAssignmentUpdateResult {
  assignment_id: number;
  employee_id: number;
  full_name: string;
  email: string;
  system_role: "employee" | "manager";
  is_hr: boolean;
  manager_assignment_id: number | null;
  staffing_line_id: number;
  staffing_title: string;
  unit_name: string;
}

export interface EmployeePasswordResetResult {
  assignment_id: number;
  employee_id: number;
  full_name: string;
  email: string;
  username: string | null;
  password: string;
  staffing_line_id: number;
  staffing_title: string;
  unit_name: string;
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
    is_hr?: boolean;
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
  is_hr?: boolean;
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
    is_hr: boolean;
    manager_assignment_id: number | null;
  }>;
  remaining_fte: number;
}

export interface StructureDeleteResult {
  scope: "work";
  assignment_id?: number;
  staffing_line_id?: number;
  deleted_assignments: number;
  deleted_participants: number;
  deleted_profiles: number;
  deactivated_employees: number;
  document_links_deleted?: number;
}
