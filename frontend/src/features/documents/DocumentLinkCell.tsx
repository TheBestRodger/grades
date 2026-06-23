import { useEffect, useRef, useState } from "react";

import type { DocumentMatrixCell, DocumentRecord } from "../../types";
import { DocumentSearchCombobox } from "./DocumentSearchCombobox";
import type { DocumentPanelProps, DocumentType } from "./types";

export function DocumentLinkCell({
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
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const shouldRestoreFocus = useRef(false);
  const linked = cell.documents[0];
  const linkedStatus =
    linked?.link_status === "confirmed" ? "Подтверждено" : linked ? "Первичная связь" : "Нет связи";

  useEffect(() => {
    if (!isChoosing && shouldRestoreFocus.current) {
      shouldRestoreFocus.current = false;
      triggerRef.current?.focus();
    }
  }, [isChoosing]);

  function closeChooser(restoreFocus: boolean) {
    shouldRestoreFocus.current = restoreFocus;
    setIsChoosing(false);
  }

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
          ref={triggerRef}
          type="button"
        >
          <span>{linked ? linked.document_code : "+ Выбрать документ"}</span>
          <span aria-hidden="true">V</span>
        </button>
      )}
      {canEdit && isChoosing && (
        <DocumentSearchCombobox
          ariaLabel={`${label}: документ для ${positionTitle}`}
          documents={documents}
          isAssigning={isAssigning}
          linkedDocumentId={linked?.document_id}
          onClose={closeChooser}
          onSelect={(documentId) => onSetLink?.(lineId, documentType, documentId)}
        />
      )}
      {!canEdit && linked && (
        <>
          <p className="mt-1 text-xs text-slate-700">{linked.title}</p>
          <p className="mt-1 text-[11px] text-slate-500">{linked.document_code}</p>
        </>
      )}
    </div>
  );
}
