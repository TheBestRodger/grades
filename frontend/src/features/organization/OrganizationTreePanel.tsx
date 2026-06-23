import { useEffect, useId, useMemo, useState } from "react";

import { OrganizationTreeNode } from "./OrganizationTreeNode";
import { filterTree } from "./organizationTreeUtils";
import type { OrganizationTreePanelProps } from "./types";

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
      if (next.has(unitId)) next.delete(unitId);
      else next.add(unitId);
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
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Структура</p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">Дерево подразделений и назначений</h2>
          <p className="mt-1 text-sm text-slate-500">✓ вся ветка в кампании, – выбрана частично, ○ не выбрана.</p>
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
          <OrganizationTreeNode
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
