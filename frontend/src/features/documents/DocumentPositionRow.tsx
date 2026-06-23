import type { DocumentPositionMatrixRow, DocumentRegistry, Position } from "../../types";
import { DocumentLinkCell } from "./DocumentLinkCell";
import type { DocumentPanelProps, DocumentType } from "./types";

export function DocumentPositionRow({
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
        <DocumentLinkCell
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
        <DocumentLinkCell
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
        <DocumentLinkCell
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
