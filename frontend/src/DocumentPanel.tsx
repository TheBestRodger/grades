import { useEffect, useId, useMemo, useState, type FormEvent } from "react";

import type {
  DocumentCoverageItem,
  DocumentMatrixCell,
  DocumentPositionMatrixRow,
  DocumentRecord,
  DocumentRegistry,
  OrgNode,
  Position,
} from "./types";

type DocumentType = "job_instruction" | "unit_regulation" | "professional_standard";

interface DocumentPanelProps {
  registry: DocumentRegistry | null;
  tree: OrgNode[];
  isLoading: boolean;
  error: string | null;
  viewer?: "hr" | "manager";
  canEdit?: boolean;
  assigningKey?: string | null;
  onSetLink?: (staffingLineId: number, documentType: DocumentType, documentId: number | null) => void;
  isUploading?: boolean;
  reviewingDocumentId?: number | null;
  onUpload?: (
    file: File,
    documentCode: string,
    documentType: DocumentType,
    title: string,
    version: string,
  ) => void;
  onReviewQuality?: (documentId: number, status: "good" | "warning", text: string) => void;
  onDownloadSource?: (documentId: number) => void;
}

interface VisibleUnit {
  source: OrgNode;
  positions: Position[];
  children: VisibleUnit[];
}

function CoverageCard({ item }: { item: DocumentCoverageItem }) {
  return (
    <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700">{item.label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{item.covered} / {item.total}</p>
        </div>
        <span className="rounded-full bg-white px-3 py-1.5 text-sm font-semibold text-indigo-900">
          {Math.round(item.percent)}%
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-600">
        Без подтвержденной связи: <strong>{item.missing}</strong>
      </p>
    </div>
  );
}

function positionCount(node: OrgNode): number {
  return node.positions.length + node.children.reduce((total, child) => total + positionCount(child), 0);
}

function visibleTree(nodes: OrgNode[]): VisibleUnit[] {
  return nodes.map((node) => ({
    source: node,
    positions: node.positions,
    children: visibleTree(node.children),
  }));
}

function filterTree(nodes: OrgNode[], query: string): { nodes: VisibleUnit[]; expanded: Set<number> } {
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

function DocumentCell({
  label,
  documentType,
  cell,
  documents,
  lineId,
  positionTitle,
  canEdit,
  isAssigning,
  onSetLink,
}: {
  label: string;
  documentType: DocumentType;
  cell: DocumentMatrixCell;
  documents: DocumentRecord[];
  lineId: number;
  positionTitle: string;
  canEdit: boolean;
  isAssigning: boolean;
  onSetLink?: DocumentPanelProps["onSetLink"];
}) {
  const [isChoosing, setIsChoosing] = useState(false);
  const linked = cell.documents[0];
  const linkedStatus =
    linked?.link_status === "confirmed" ? "Подтверждено" : linked ? "Первичная связь" : "Нет связи";
  return (
    <div
      className={`min-w-0 rounded-lg border px-2.5 py-2 ${
        linked ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase text-slate-600">{label}</p>
      <p className={`mt-1 text-xs font-medium ${linked ? "text-emerald-800" : "text-amber-800"}`}>
        {linkedStatus}
      </p>
      {canEdit && !isChoosing && (
        <button
          aria-label={`${linked ? "Изменить" : "Добавить"} ${label} для ${positionTitle}`}
          className="mt-1.5 flex w-full items-center justify-between rounded-md border border-slate-200 bg-white px-2 py-1.5 text-left text-xs text-slate-700 hover:border-blue-300 hover:bg-blue-50"
          disabled={isAssigning}
          onClick={() => setIsChoosing(true)}
          type="button"
        >
          <span>{linked ? linked.document_code : "+ Выбрать документ"}</span>
          <span aria-hidden="true">v</span>
        </button>
      )}
      {canEdit && isChoosing && (
        <select
          aria-label={`${label}: документ для ${positionTitle}`}
          autoFocus
          className="mt-1.5 block w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 outline-none focus:border-blue-700 disabled:opacity-60"
          disabled={isAssigning}
          onBlur={() => setIsChoosing(false)}
          onChange={(event) => {
            setIsChoosing(false);
            onSetLink?.(lineId, documentType, event.target.value ? Number(event.target.value) : null);
          }}
          value={linked?.document_id ?? ""}
        >
          <option value="">+ Выбрать документ</option>
          {documents.map((document) => (
            <option
              disabled={document.has_stored_original && document.ocr_quality_status !== "good"}
              key={document.id}
              value={document.id}
            >
              {document.title} / {document.document_code}
              {document.has_stored_original && document.ocr_quality_status !== "good"
                ? " (нужна проверка текста)"
                : ""}
            </option>
          ))}
        </select>
      )}
      {!canEdit && (
        linked && (
          <>
            <p className="mt-1 text-xs text-slate-700">{linked.title}</p>
            <p className="mt-1 text-[11px] text-slate-500">{linked.document_code}</p>
          </>
        )
      )}
    </div>
  );
}

function PositionRow({
  position,
  row,
  registry,
  canEdit,
  assigningKey,
  onSetLink,
}: {
  position: Position;
  row: DocumentPositionMatrixRow | undefined;
  registry: DocumentRegistry;
  canEdit: boolean;
  assigningKey: string | null;
  onSetLink?: DocumentPanelProps["onSetLink"];
}) {
  if (!row) return null;
  const options = (type: DocumentType) => registry.documents.filter((document) => document.document_type === type);
  return (
    <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h4 className="truncate text-sm font-semibold text-slate-950">{position.title}</h4>
          <p className="mt-0.5 text-xs text-slate-500">
            Штатная позиция / покрытие {row.covered_count} из {row.required_count}
          </p>
        </div>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
          row.covered_count === row.required_count
            ? "bg-emerald-100 text-emerald-800"
            : "bg-amber-100 text-amber-800"
        }`}>
          {row.covered_count}/3
        </span>
      </div>
      <div className="mt-2.5 grid gap-2 lg:grid-cols-3">
        <DocumentCell
          canEdit={canEdit}
          cell={row.job_instruction}
          documentType="job_instruction"
          documents={options("job_instruction")}
          isAssigning={assigningKey === `${position.id}:job_instruction`}
          label="ДИ"
          lineId={position.id}
          onSetLink={onSetLink}
          positionTitle={position.title}
        />
        <DocumentCell
          canEdit={canEdit}
          cell={row.unit_regulation}
          documentType="unit_regulation"
          documents={options("unit_regulation")}
          isAssigning={assigningKey === `${position.id}:unit_regulation`}
          label="Положение"
          lineId={position.id}
          onSetLink={onSetLink}
          positionTitle={position.title}
        />
        <DocumentCell
          canEdit={canEdit}
          cell={row.professional_standard}
          documentType="professional_standard"
          documents={options("professional_standard")}
          isAssigning={assigningKey === `${position.id}:professional_standard`}
          label="Профстандарт"
          lineId={position.id}
          onSetLink={onSetLink}
          positionTitle={position.title}
        />
      </div>
    </article>
  );
}

function UnitNode({
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
  matrix: Map<number, DocumentPositionMatrixRow>;
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
            <PositionRow
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
            <UnitNode
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

function WorkDocumentControls({
  registry,
  isUploading,
  reviewingDocumentId,
  onUpload,
  onReviewQuality,
  onDownloadSource,
}: {
  registry: DocumentRegistry;
  isUploading: boolean;
  reviewingDocumentId: number | null;
  onUpload?: DocumentPanelProps["onUpload"];
  onReviewQuality?: DocumentPanelProps["onReviewQuality"];
  onDownloadSource?: DocumentPanelProps["onDownloadSource"];
}) {
  const [documentCode, setDocumentCode] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType>("job_instruction");
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("1.0");
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(registry.documents[0]?.id ?? null);
  const selected = registry.documents.find((document) => document.id === selectedId) ?? registry.documents[0] ?? null;
  const [qualityText, setQualityText] = useState(selected?.content_text ?? "");

  useEffect(() => {
    setQualityText(selected?.content_text ?? "");
  }, [selected?.id, selected?.content_text]);

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !documentCode.trim() || !title.trim() || !version.trim()) return;
    onUpload?.(file, documentCode.trim(), documentType, title.trim(), version.trim());
  }

  return (
    <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(300px,0.9fr)_minmax(420px,1.25fr)]">
      <form className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4" onSubmit={submitUpload}>
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-blue-700">Новый оригинал</p>
        <h3 className="mt-1 text-base font-bold text-slate-950">Загрузить документ</h3>
        <p className="mt-1 text-xs text-slate-600">
          TXT, MD и DOCX получают первоначальный текст локально. Для PDF внесите распознанный текст при проверке.
        </p>
        <div className="mt-4 grid gap-3">
          <input
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => setDocumentCode(event.target.value)}
            placeholder="Код документа"
            required
            value={documentCode}
          />
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => setDocumentType(event.target.value as DocumentType)}
            value={documentType}
          >
            <option value="job_instruction">Должностная инструкция</option>
            <option value="unit_regulation">Положение подразделения</option>
            <option value="professional_standard">Профстандарт</option>
          </select>
          <input
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Название"
            required
            value={title}
          />
          <input
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => setVersion(event.target.value)}
            placeholder="Версия"
            required
            value={version}
          />
          <input
            accept=".txt,.md,.docx,.pdf"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
            type="file"
          />
          <button
            className="rounded-lg bg-blue-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            disabled={isUploading}
            type="submit"
          >
            {isUploading ? "Загружаю..." : "Загрузить оригинал"}
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Контроль качества</p>
        <h3 className="mt-1 text-base font-bold text-slate-950">Проверка текста документа</h3>
        {selected ? (
          <>
            <select
              className="mt-4 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              onChange={(event) => setSelectedId(Number(event.target.value))}
              value={selected.id}
            >
              {registry.documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.document_code} / {document.title}
                </option>
              ))}
            </select>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full bg-white px-3 py-1.5 text-slate-700">
                {selected.ocr_quality_label}
              </span>
              {selected.has_stored_original && (
                <button
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 font-semibold text-blue-800"
                  onClick={() => onDownloadSource?.(selected.id)}
                  type="button"
                >
                  Скачать оригинал
                </button>
              )}
            </div>
            <textarea
              className="mt-3 min-h-[170px] w-full rounded-lg border border-slate-200 bg-white p-3 text-sm outline-none focus:border-blue-700"
              onChange={(event) => setQualityText(event.target.value)}
              placeholder="Извлечённый или распознанный текст для проверки HR"
              value={qualityText}
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                disabled={reviewingDocumentId === selected.id || !qualityText.trim()}
                onClick={() => onReviewQuality?.(selected.id, "good", qualityText)}
                type="button"
              >
                Подтвердить текст
              </button>
              <button
                className="rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-800 disabled:opacity-60"
                disabled={reviewingDocumentId === selected.id}
                onClick={() => onReviewQuality?.(selected.id, "warning", qualityText)}
                type="button"
              >
                Требует исправления
              </button>
            </div>
          </>
        ) : (
          <p className="mt-4 text-sm text-slate-500">В рабочем реестре пока нет документов.</p>
        )}
      </div>
    </div>
  );
}

export function DocumentPanel({
  registry,
  tree,
  isLoading,
  error,
  viewer = "hr",
  canEdit = false,
  assigningKey = null,
  onSetLink,
  isUploading = false,
  reviewingDocumentId = null,
  onUpload,
  onReviewQuality,
  onDownloadSource,
}: DocumentPanelProps) {
  const isManagerView = viewer === "manager";
  const searchId = useId();
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const query = search.trim().toLocaleLowerCase("ru-RU");
  const filtered = useMemo(() => filterTree(tree, query), [tree, query]);
  const visibleExpanded = query ? filtered.expanded : expanded;
  const matrix = useMemo(
    () => new Map(registry?.position_matrix.map((row) => [row.staffing_line_id, row]) ?? []),
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
    <section className="rounded-3xl border border-indigo-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-700">
            {isManagerView ? "Руководитель: документы своей зоны" : "HR: документы"}
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">
            {isManagerView ? "Документальное обеспечение моей ветки" : "Документы по структуре и штатным позициям"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {isManagerView
              ? "Только доступная зона: ДИ, положения и профстандарты можно просматривать без изменения связей."
              : "Структура без сотрудников: для каждой штатной позиции проверяются ДИ, положение и профстандарт."}
          </p>
        </div>
        {registry && (
          <span className="rounded-full bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
            Документов в реестре: {registry.documents_total}
          </span>
        )}
      </div>

      {isLoading && <p className="mt-5 text-sm text-slate-500">Загружаю реестр документов...</p>}
      {error && <p className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      {registry && (
        <>
          <p className="mt-5 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {registry.note}
          </p>
          <div className="mt-5 grid gap-4 xl:grid-cols-3">
            <CoverageCard item={registry.coverage.job_instruction} />
            <CoverageCard item={registry.coverage.unit_regulation} />
            <CoverageCard item={registry.coverage.professional_standard} />
          </div>
          {canEdit && registry.scope === "work" && (
            <WorkDocumentControls
              isUploading={isUploading}
              onDownloadSource={onDownloadSource}
              onReviewQuality={onReviewQuality}
              onUpload={onUpload}
              registry={registry}
              reviewingDocumentId={reviewingDocumentId}
            />
          )}
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
                <UnitNode
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
        </>
      )}
    </section>
  );
}
