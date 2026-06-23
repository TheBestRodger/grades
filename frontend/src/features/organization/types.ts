import type { Assignment, Campaign, OrgNode, Position } from "../../types";

export interface OrganizationTreePanelProps {
  nodes: OrgNode[];
  canManage: boolean;
  canAddEmployees?: boolean;
  canEditStructure?: boolean;
  activeCampaign: Campaign | null;
  includingUnitId: number | null;
  excludingUnitId: number | null;
  changingAssignmentId?: number | null;
  onAdd: (position: Position) => void;
  onCreatePosition?: (unit: OrgNode) => void;
  onEditAssignment?: (assignment: Assignment, position: Position) => void;
  onDeleteAssignment?: (assignment: Assignment, position: Position) => void;
  onDeletePosition?: (position: Position) => void;
  onInclude: (unit: OrgNode) => void;
  onExclude: (unit: OrgNode) => void;
  onSetAssignment?: (assignmentId: number, included: boolean) => void;
}

export interface FilteredTree {
  nodes: VisibleOrgNode[];
  expandedUnitIds: Set<number>;
  matchCount: number;
}

export interface VisibleOrgNode {
  source: OrgNode;
  positions: Position[];
  children: VisibleOrgNode[];
}
