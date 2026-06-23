import { useEffect, useId, useMemo, useState } from "react";

import type { DocumentRegistry, OrgNode } from "../../types";
import { DocumentUnitNode } from "./DocumentUnitNode";
import { filterTree } from "./documentTree";
import type { DocumentPanelProps } from "./types";

export function DocumentRegistryTree({
  registry,
  tree,
  canEdit,
  assigningKey,
  onSetLink,
}: {
  registry: DocumentRegistry;
  tree: OrgNode[];
  canEdit: boolean;
  assigningKey: string | null;
  onSetLink?: DocumentPanelProps["onSetLink"];
}) {
  const searchId = useId();
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const query = search.trim().toLocaleLowerCase("ru-RU");
  const filtered = useMemo(() => filterTree(tree, query), [tree, query]);
  const visibleExpanded = query ? filtered.expanded : expanded;
  const matrix = useMemo(
    () => new Map(registry.position_matrix.map((row) => [row.staffing_line_id, row])),
    [registry],
  );

  useEffect(() => {
    if (query) {
      setExpanded(new Set(filtered.expanded));
    }
  }, [filtered.expanded, query]);

  function toggle(id: number) {
    setExpanded((current) => {
      const next = new Set(query ? visibleExpanded : current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[260px] flex-1">
          <label className="mb-2 block text-xs font-semibold uppercase text-slate-500" htmlFor={searchId}>
            Поиск по структуре или должности
          </label>
          <input
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-blue-700"
            id={searchId}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Подразделение или штатная позиция"
            type="search"
            value={search}
          />
        </div>
        {query && (
          <button
            className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700"
            onClick={() => setSearch("")}
            type="button"
          >
            Очистить
          </button>
        )}
      </div>
      <div className="mt-4 space-y-2">
        {filtered.nodes.map((node) => (
          <DocumentUnitNode
            assigningKey={assigningKey}
            canEdit={canEdit}
            depth={0}
            expanded={visibleExpanded}
            key={node.source.id}
            matrix={matrix}
            node={node}
            onSetLink={onSetLink}
            onToggle={toggle}
            registry={registry}
          />
        ))}
        {filtered.nodes.length === 0 && (
          <p className="rounded-xl bg-white px-4 py-5 text-sm text-slate-500">Ничего не найдено.</p>
        )}
      </div>
    </div>
  );
}
