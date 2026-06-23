import type { DocumentRecord } from "../../types";

export function normalizeDocumentSearch(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase();
}

export function isDocumentLinkDisabled(document: DocumentRecord) {
  return document.has_stored_original && document.ocr_quality_status !== "good";
}

export function getDocumentQualityStatusText(document: DocumentRecord) {
  return document.ocr_quality_label || document.ocr_quality_status || "Статус текста не указан";
}

export function matchesDocumentSearch(document: DocumentRecord, query: string) {
  const normalizedQuery = normalizeDocumentSearch(query);
  if (!normalizedQuery) return true;

  return [document.title, document.document_code, document.version]
    .map(normalizeDocumentSearch)
    .some((value) => value.includes(normalizedQuery));
}

export function filterDocumentsForSearch(documents: DocumentRecord[], query: string) {
  return documents.filter((document) => matchesDocumentSearch(document, query));
}
