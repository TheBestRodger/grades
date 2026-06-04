import { useEffect, useId, useMemo, useState } from "react";

import type { Campaign, OrgNode, Position } from "./types";

interface OrganizationTreePanelProps {
  nodes: OrgNode[];
  canManage: boolean;
  canAddEmployees?: boolean;
  activeCampaign: Campaign | null;
  includingUnitId: number | null;
  excludingUnitId: number | null;
  changingAssignmentId?: number | null;
  onAdd: (position: Position) => void;
  onInclude: (unit: OrgNode) => void;
  onExclude: (unit: OrgNode) => void;
  onSetAssignment?: (assignmentId: number, included: boolean) => void;
}

function displayFte(value: number | null): string {
  return value === null ? "-" : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function assignmentIds(node: OrgNode): number[] {
  return [
    ...node.positions.flatMap((position) => position.assignments.map((assignment) => assignment.id)),
    ...node.children.flatMap((child) => assignmentIds(child)),
  ];
}

function positionCount(node: OrgNode): number {
  return node.positions.length + node.children.reduce((total, child) => total + positionCount(child), 0);
}

interface FilteredTree {
  nodes: VisibleOrgNode[];
  expandedUnitIds: Set<number>;
  matchCount: number;
}

interface VisibleOrgNode {
  source: OrgNode;
  positions: Position[];
  children: VisibleOrgNode[];
}

function matchesQuery(value: string, query: string): boolean {
  return value.toLocaleLowerCase("ru-RU").includes(query);
}

function visibleTree(nodes: OrgNode[]): VisibleOrgNode[] {
  return nodes.map((node) => ({
    source: node,
    positions: node.positions,
    children: visibleTree(node.children),
  }));
}

function filterTree(nodes: OrgNode[], query: string): FilteredTree {
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

function selectionState(node: OrgNode, activeCampaign: Campaign | null) {
  if (!activeCampaign) {
    return { label: "•", tone: "border-slate-200 bg-white text-slate-500", selected: 0, total: 0 };
  }
  const ids =
    activeCampaign.scope === "work"
      ? unitIds(node)
      : assignmentIds(node);
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

function unitIds(node: OrgNode): number[] {
  return [node.id, ...node.children.flatMap((child) => unitIds(child))];
}

function PositionLine({
  position,
  canAddEmployees,
  canManage,
  activeCampaign,
  changingAssignmentId,
  onAdd,
  onSetAssignment,
}: {
  position: Position;
  canAddEmployees: boolean;
  canManage: boolean;
  activeCampaign: Campaign | null;
  changingAssignmentId?: number | null;
  onAdd: (position: Position) => void;
  onSetAssignment?: (assignmentId: number, included: boolean) => void;
}) {
  const included = new Set(activeCampaign?.participant_assignment_ids ?? []);
  const canFillReportedOccupiedLine =
    position.assignments.length === 0 &&
    (position.approved_fte ?? 0) > 0 &&
    (position.assigned_fte ?? 0) > 0;
  const canOpenEmployeeModal =
    canAddEmployees && ((position.vacancy_fte ?? 0) > 0 || canFillReportedOccupiedLine);
  return (
    <div className="ml-8 border-l border-slate-100 pl-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{position.title}</p>
          {position.approved_fte !== null && (
            <p className="text-xs text-slate-500">
              ШР {displayFte(position.approved_fte)} / занято {displayFte(position.assigned_fte)} / свободно{" "}
              {displayFte(position.vacancy_fte)}
            </p>
          )}
        </div>
        {canOpenEmployeeModal && (
          <button
            className="rounded-full bg-blue-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
            onClick={() => onAdd(position)}
            type="button"
          >
            Добавить людей
          </button>
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {position.assignments.map((assignment) => {
          const isIncluded = included.has(assignment.id);
          const className = `rounded-full border px-2.5 py-1 text-xs ${
            isIncluded
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-slate-200 bg-white text-slate-600"
          }`;
          const label = (
            <>
              {isIncluded ? "✓ " : canManage && activeCampaign ? "+ " : ""}
              {assignment.employee_name}
              {position.assigned_fte !== null && ` / ${displayFte(assignment.fte)}`}
            </>
          );
          return canManage && activeCampaign ? (
            <button
              aria-label={`${isIncluded ? "Исключить" : "Включить"} назначение ${assignment.employee_name}`}
              className={`${className} hover:border-blue-300 disabled:opacity-50`}
              disabled={changingAssignmentId === assignment.id}
              key={assignment.id}
              onClick={() => onSetAssignment?.(assignment.id, !isIncluded)}
              type="button"
            >
              {label}
            </button>
          ) : (
            <span
              className={`rounded-full border px-2.5 py-1 text-xs ${
                isIncluded
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : "border-slate-200 bg-white text-slate-600"
              }`}
              key={assignment.id}
            >
              {label}
            </span>
          );
        })}
        {position.assignments.length === 0 && (
          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-400">
            {(position.assigned_fte ?? 0) > 0
              ? `Сотрудники не загружены / занято ${displayFte(position.assigned_fte)}`
              : "Вакантно"}
          </span>
        )}
      </div>
    </div>
  );
}

function TreeNode({
  node: visibleNode,
  canManage,
  canAddEmployees = canManage,
  activeCampaign,
  includingUnitId,
  excludingUnitId,
  onAdd,
  onInclude,
  onExclude,
  changingAssignmentId,
  onSetAssignment,
  depth,
  expandedUnitIds,
  onToggle,
}: OrganizationTreePanelProps & {
  node: VisibleOrgNode;
  depth: number;
  expandedUnitIds: Set<number>;
  onToggle: (unitId: number) => void;
}) {
  const node = visibleNode.source;
  const state = selectionState(node, activeCampaign);
  const isBusy = includingUnitId === node.id || excludingUnitId === node.id;
  const positionsTotal = positionCount(node);
  const hasContents = visibleNode.positions.length > 0 || visibleNode.children.length > 0;
  const isExpanded = hasContents && expandedUnitIds.has(node.id);
  return (
    <div className={depth === 0 ? "" : "ml-5 border-l border-slate-200 pl-4"}>
      <div className={`rounded-2xl border px-4 py-3 ${state.tone}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {hasContents ? (
              <button
                aria-expanded={isExpanded}
                aria-label={`${isExpanded ? "Свернуть" : "Развернуть"} подразделение ${node.name}`}
                className="grid h-8 w-8 place-items-center rounded-lg border border-slate-300 bg-white text-lg font-medium text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-900"
                onClick={() => onToggle(node.id)}
                type="button"
              >
                {isExpanded ? "-" : "+"}
              </button>
            ) : (
              <span className="h-8 w-8" />
            )}
            <span className="grid h-8 w-8 place-items-center rounded-lg border border-current bg-white/70 text-sm font-bold">
              {state.label}
            </span>
            <div>
              <p className="font-semibold text-slate-950">{node.name}</p>
              <p className="text-xs text-slate-500">
                {activeCampaign
                  ? activeCampaign.scope === "work"
                    ? `В волне: ${state.selected} / ${state.total} подразделений`
                    : `В кампании: ${state.selected} / ${state.total} назначений`
                  : `Штатных строк: ${positionsTotal}`}
              </p>
            </div>
          </div>
          {canManage && activeCampaign && (
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold text-blue-900 hover:bg-blue-50 disabled:opacity-50"
                disabled={isBusy}
                onClick={() => onInclude(node)}
                type="button"
              >
                {includingUnitId === node.id ? "Включаю..." : "Включить ветку"}
              </button>
              <button
                className="rounded-full border border-amber-200 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-50 disabled:opacity-50"
                disabled={isBusy || state.selected === 0}
                onClick={() => onExclude(node)}
                type="button"
              >
                {excludingUnitId === node.id ? "Выключаю..." : "Выключить"}
              </button>
            </div>
          )}
        </div>
      </div>
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {visibleNode.positions.map((position) => (
            <PositionLine
              activeCampaign={activeCampaign}
              canAddEmployees={canAddEmployees}
              canManage={canManage}
              changingAssignmentId={changingAssignmentId}
              key={position.id}
              onAdd={onAdd}
              onSetAssignment={onSetAssignment}
              position={position}
            />
          ))}
          {visibleNode.children.map((child) => (
            <TreeNode
              activeCampaign={activeCampaign}
              canManage={canManage}
              canAddEmployees={canAddEmployees}
              excludingUnitId={excludingUnitId}
              changingAssignmentId={changingAssignmentId}
              expandedUnitIds={expandedUnitIds}
              includingUnitId={includingUnitId}
              key={child.source.id}
              node={child}
              nodes={[]}
              onAdd={onAdd}
              onExclude={onExclude}
              onInclude={onInclude}
              onSetAssignment={onSetAssignment}
              onToggle={onToggle}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function OrganizationTreePanel(props: OrganizationTreePanelProps) {
  const searchId = useId();
  const [searchValue, setSearchValue] = useState("");
  const [expandedUnitIds, setExpandedUnitIds] = useState<Set<number>>(new Set());
  const [searchExpandedUnitIds, setSearchExpandedUnitIds] = useState<Set<number>>(new Set());
  const query = searchValue.trim().toLocaleLowerCase("ru-RU");
  const filteredTree = useMemo(() => filterTree(props.nodes, query), [props.nodes, query]);
  const isSearching = query.length > 0;
  const visibleExpandedUnitIds = isSearching ? searchExpandedUnitIds : expandedUnitIds;

  useEffect(() => {
    if (isSearching) {
      setSearchExpandedUnitIds(new Set(filteredTree.expandedUnitIds));
    }
  }, [filteredTree.expandedUnitIds, isSearching]);

  function toggleUnit(unitId: number) {
    const update = (current: Set<number>) => {
      const next = new Set(current);
      if (next.has(unitId)) {
        next.delete(unitId);
      } else {
        next.add(unitId);
      }
      return next;
    };
    if (isSearching) {
      setSearchExpandedUnitIds(update);
      return;
    }
    setExpandedUnitIds(update);
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
            Структура
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">
            Дерево подразделений и назначений
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            ✓ вся ветка в кампании, – выбрана частично, ○ не выбрана.
          </p>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-end gap-3 border-y border-slate-100 py-4">
        <div className="min-w-[260px] flex-1">
          <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500" htmlFor={searchId}>
            Поиск по структуре
          </label>
          <input
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-700"
            id={searchId}
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="Подразделение, должность или сотрудник"
            type="search"
            value={searchValue}
          />
        </div>
        {isSearching && (
          <>
            <p className="rounded-lg bg-blue-50 px-3 py-2.5 text-sm font-medium text-blue-900">
              Найдено: {filteredTree.matchCount}
            </p>
            <button
              className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => setSearchValue("")}
              type="button"
            >
              Очистить
            </button>
          </>
        )}
      </div>
      <div className="mt-5 space-y-4">
        {filteredTree.nodes.map((node) => (
          <TreeNode
            {...props}
            depth={0}
            expandedUnitIds={visibleExpandedUnitIds}
            key={node.source.id}
            node={node}
            onToggle={toggleUnit}
          />
        ))}
        {isSearching && filteredTree.nodes.length === 0 && (
          <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
            По вашему запросу в доступной структуре ничего не найдено.
          </p>
        )}
      </div>
    </section>
  );
}
