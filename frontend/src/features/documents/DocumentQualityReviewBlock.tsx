import { useEffect, useState } from "react";

import type { DocumentRegistry } from "../../types";
import { DocumentSourceDownloadButton } from "./DocumentSourceDownloadButton";
import type { DocumentPanelProps } from "./types";

export function DocumentQualityReviewBlock({
  registry,
  reviewingDocumentId,
  onReviewQuality,
  onDownloadSource,
}: {
  registry: DocumentRegistry;
  reviewingDocumentId: number | null;
  onReviewQuality?: DocumentPanelProps["onReviewQuality"];
  onDownloadSource?: DocumentPanelProps["onDownloadSource"];
}) {
  const [selectedId, setSelectedId] = useState<number | null>(registry.documents[0]?.id ?? null);
  const selected = registry.documents.find((document) => document.id === selectedId) ?? registry.documents[0] ?? null;
  const [qualityText, setQualityText] = useState(selected?.content_text ?? "");

  useEffect(() => {
    setQualityText(selected?.content_text ?? "");
  }, [selected?.id, selected?.content_text]);

  return (
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
              <DocumentSourceDownloadButton documentId={selected.id} onDownloadSource={onDownloadSource} />
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
  );
}
