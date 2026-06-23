import type { DemoUser } from "./auth";

export interface Assignment {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_email: string;
  fte: number;
  role: string;
  is_hr: boolean;
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

export interface ManagerOption {
  assignment_id: number;
  employee_name: string;
  position_title: string;
  unit_name: string;
  is_demo?: boolean;
}
