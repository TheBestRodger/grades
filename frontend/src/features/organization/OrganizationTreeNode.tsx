import { CampaignSelectionIndicator } from "./CampaignSelectionIndicator";
import { positionCount, selectionState } from "./organizationTreeUtils";
import { StaffingLineRow } from "./StaffingLineRow";
import { TreeNodeActions } from "./TreeNodeActions";
import type { OrganizationTreePanelProps, VisibleOrgNode } from "./types";

export function OrganizationTreeNode({
  node: visibleNode,
  canManage,
  canAddEmployees = canManage,
  canEditStructure = false,
  activeCampaign,
  includingUnitId,
  excludingUnitId,
  onAdd,
  onCreatePosition,
  onEditAssignment,
  onDeleteAssignment,
  onDeletePosition,
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
            <CampaignSelectionIndicator activeCampaign={activeCampaign} node={node} />
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
          <TreeNodeActions
            activeCampaign={activeCampaign}
            canEditStructure={canEditStructure}
            canManage={canManage}
            excludingUnitId={excludingUnitId}
            includingUnitId={includingUnitId}
            node={node}
            onCreatePosition={onCreatePosition}
            onExclude={onExclude}
            onInclude={onInclude}
          />
        </div>
      </div>
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {visibleNode.positions.map((position) => (
            <StaffingLineRow
              activeCampaign={activeCampaign}
              canAddEmployees={canAddEmployees}
              canEditStructure={canEditStructure}
              canManage={canManage}
              changingAssignmentId={changingAssignmentId}
              key={position.id}
              onAdd={onAdd}
              onDeleteAssignment={onDeleteAssignment}
              onDeletePosition={onDeletePosition}
              onEditAssignment={onEditAssignment}
              onSetAssignment={onSetAssignment}
              position={position}
            />
          ))}
          {visibleNode.children.map((child) => (
            <OrganizationTreeNode
              activeCampaign={activeCampaign}
              canAddEmployees={canAddEmployees}
              canEditStructure={canEditStructure}
              canManage={canManage}
              changingAssignmentId={changingAssignmentId}
              depth={depth + 1}
              excludingUnitId={excludingUnitId}
              expandedUnitIds={expandedUnitIds}
              includingUnitId={includingUnitId}
              key={child.source.id}
              node={child}
              nodes={[]}
              onAdd={onAdd}
              onCreatePosition={onCreatePosition}
              onDeleteAssignment={onDeleteAssignment}
              onDeletePosition={onDeletePosition}
              onEditAssignment={onEditAssignment}
              onExclude={onExclude}
              onInclude={onInclude}
              onSetAssignment={onSetAssignment}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}
