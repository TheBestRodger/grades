import type { DocumentRegistry } from "../../types";
import { DocumentPositionRow } from "./DocumentPositionRow";
import { positionCount } from "./documentTree";
import type { DocumentMatrixByLine, DocumentPanelProps, VisibleUnit } from "./types";

export function DocumentUnitNode({
  node,
  depth,
  registry,
  matrix,
  expanded,
  onToggle,
  canEdit,
  assigningKey,
  onSetLink,
}: {
  node: VisibleUnit;
  depth: number;
  registry: DocumentRegistry;
  matrix: DocumentMatrixByLine;
  expanded: Set<number>;
  onToggle: (id: number) => void;
  canEdit: boolean;
  assigningKey: string | null;
  onSetLink?: DocumentPanelProps["onSetLink"];
}) {
  const isExpanded = expanded.has(node.source.id);
  const hasContents = node.positions.length > 0 || node.children.length > 0;
  return (
    <div className={depth === 0 ? "" : "ml-4 border-l border-slate-200 pl-3"}>
      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
        {hasContents ? (
          <button
            aria-expanded={isExpanded}
            aria-label={`${isExpanded ? "Свернуть" : "Развернуть"} документацию подразделения ${node.source.name}`}
            className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-slate-300 text-sm text-slate-700 hover:bg-blue-50"
            onClick={() => onToggle(node.source.id)}
            type="button"
          >
            {isExpanded ? "-" : "+"}
          </button>
        ) : (
          <span className="h-7 w-7 shrink-0" />
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-950">{node.source.name}</p>
          <p className="text-xs text-slate-500">Штатных позиций: {positionCount(node.source)}</p>
        </div>
      </div>
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {node.positions.map((position) => (
            <DocumentPositionRow
              assigningKey={assigningKey}
              canEdit={canEdit}
              key={position.id}
              onSetLink={onSetLink}
              position={position}
              registry={registry}
              row={matrix.get(position.id)}
            />
          ))}
          {node.children.map((child) => (
            <DocumentUnitNode
              assigningKey={assigningKey}
              canEdit={canEdit}
              depth={depth + 1}
              expanded={expanded}
              key={child.source.id}
              matrix={matrix}
              node={child}
              onSetLink={onSetLink}
              onToggle={onToggle}
              registry={registry}
            />
          ))}
        </div>
      )}
    </div>
  );
}
