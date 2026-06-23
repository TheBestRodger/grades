import type { Campaign, OrgNode } from "../../types";
import type { FilteredTree, VisibleOrgNode } from "./types";

export function displayFte(value: number | null): string {
  return value === null ? "-" : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

export function assignmentIds(node: OrgNode): number[] {
  return [
    ...node.positions.flatMap((position) => position.assignments.map((assignment) => assignment.id)),
    ...node.children.flatMap((child) => assignmentIds(child)),
  ];
}

export function positionCount(node: OrgNode): number {
  return node.positions.length + node.children.reduce((total, child) => total + positionCount(child), 0);
}

export function selectionState(node: OrgNode, activeCampaign: Campaign | null) {
  if (!activeCampaign) {
    return { label: "•", tone: "border-slate-200 bg-white text-slate-500", selected: 0, total: 0 };
  }
  const ids = activeCampaign.scope === "work" ? unitIds(node) : assignmentIds(node);
  const included = new Set(
    activeCampaign.scope === "work"
      ? activeCampaign.selected_org_unit_ids
      : activeCampaign.participant_assignment_ids,
  );
  const selected = ids.filter((id) => included.has(id)).length;
  if (ids.length === 0 || selected === 0) {
    return { label: "○", tone: "border-slate-200 bg-white text-slate-400", selected, total: ids.length };
  }
  if (selected === ids.length) {
    return { label: "✓", tone: "border-emerald-200 bg-emerald-50 text-emerald-700", selected, total: ids.length };
  }
  return { label: "–", tone: "border-amber-200 bg-amber-50 text-amber-700", selected, total: ids.length };
}

export function unitIds(node: OrgNode): number[] {
  return [node.id, ...node.children.flatMap((child) => unitIds(child))];
}

function matchesQuery(value: string, query: string): boolean {
  return value.toLocaleLowerCase("ru-RU").includes(query);
}

export function visibleTree(nodes: OrgNode[]): VisibleOrgNode[] {
  return nodes.map((node) => ({
    source: node,
    positions: node.positions,
    children: visibleTree(node.children),
  }));
}

export function filterTree(nodes: OrgNode[], query: string): FilteredTree {
  if (!query) {
    return { nodes: visibleTree(nodes), expandedUnitIds: new Set<number>(), matchCount: 0 };
  }

  const expandedUnitIds = new Set<number>();
  let matchCount = 0;

  function filterNode(node: OrgNode): VisibleOrgNode | null {
    const nodeMatches = matchesQuery(node.name, query);
    if (nodeMatches) {
      matchCount += 1;
    }

    const positions = node.positions.filter((position) => {
      const positionMatches =
        matchesQuery(position.title, query) ||
        position.assignments.some((assignment) => matchesQuery(assignment.employee_name, query));
      if (positionMatches) {
        matchCount += 1;
      }
      return positionMatches;
    });
    const children = node.children
      .map((child) => filterNode(child))
      .filter((child): child is VisibleOrgNode => child !== null);

    if (!nodeMatches && positions.length === 0 && children.length === 0) {
      return null;
    }
    if (positions.length > 0 || children.length > 0) {
      expandedUnitIds.add(node.id);
    }
    return { source: node, positions, children };
  }

  return {
    nodes: nodes.map((node) => filterNode(node)).filter((node): node is VisibleOrgNode => node !== null),
    expandedUnitIds,
    matchCount,
  };
}
