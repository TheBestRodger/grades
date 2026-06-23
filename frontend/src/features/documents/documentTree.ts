import type { OrgNode } from "../../types";
import type { VisibleUnit } from "./types";

export function positionCount(node: OrgNode): number {
  return node.positions.length + node.children.reduce((total, child) => total + positionCount(child), 0);
}

export function visibleTree(nodes: OrgNode[]): VisibleUnit[] {
  return nodes.map((node) => ({
    source: node,
    positions: node.positions,
    children: visibleTree(node.children),
  }));
}

export function filterTree(nodes: OrgNode[], query: string): { nodes: VisibleUnit[]; expanded: Set<number> } {
  if (!query) {
    return { nodes: visibleTree(nodes), expanded: new Set<number>() };
  }
  const expanded = new Set<number>();

  function visit(node: OrgNode): VisibleUnit | null {
    const unitMatches = node.name.toLocaleLowerCase("ru-RU").includes(query);
    const positions = unitMatches
      ? node.positions
      : node.positions.filter((position) => position.title.toLocaleLowerCase("ru-RU").includes(query));
    const children = node.children.map(visit).filter((child): child is VisibleUnit => child !== null);
    if (!unitMatches && positions.length === 0 && children.length === 0) {
      return null;
    }
    expanded.add(node.id);
    return { source: node, positions, children };
  }

  return {
    nodes: nodes.map(visit).filter((node): node is VisibleUnit => node !== null),
    expanded,
  };
}
