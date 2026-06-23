import type { Campaign, OrgNode } from "../../types";
import { selectionState } from "./organizationTreeUtils";

export function TreeNodeActions({
  node,
  activeCampaign,
  canManage,
  canEditStructure,
  includingUnitId,
  excludingUnitId,
  onInclude,
  onExclude,
  onCreatePosition,
}: {
  node: OrgNode;
  activeCampaign: Campaign | null;
  canManage: boolean;
  canEditStructure: boolean;
  includingUnitId: number | null;
  excludingUnitId: number | null;
  onInclude: (unit: OrgNode) => void;
  onExclude: (unit: OrgNode) => void;
  onCreatePosition?: (unit: OrgNode) => void;
}) {
  const state = selectionState(node, activeCampaign);
  const isBusy = includingUnitId === node.id || excludingUnitId === node.id;

  return (
    <>
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
      {canEditStructure && (
        <button
          className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold text-blue-900 hover:bg-blue-50"
          onClick={() => onCreatePosition?.(node)}
          type="button"
        >
          Добавить штатную единицу
        </button>
      )}
    </>
  );
}
