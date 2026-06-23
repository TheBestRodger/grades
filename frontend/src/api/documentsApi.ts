import { authHeaders, readResponseError, request } from "./request";
import { API_URL } from "./urls";
import type { DocumentRegistry } from "./types";

export const getHrDocuments = (userId: number, scope: "demo" | "work" = "demo") =>
  request<DocumentRegistry>(API_URL.documents.hr(scope), { userId });

export const getManagerDocuments = (userId: number) =>
  request<DocumentRegistry>(API_URL.documents.manager, { userId });

export const setWorkDocumentLink = (
  userId: number,
  staffingLineId: number,
  documentType: "job_instruction" | "unit_regulation" | "professional_standard",
  documentId: number | null,
) =>
  request<DocumentRegistry>(API_URL.documents.workLink, {
    userId,
    method: "PUT",
    body: {
      staffing_line_id: staffingLineId,
      document_type: documentType,
      document_id: documentId,
    },
  });

export const uploadWorkDocument = async (
  _userId: number,
  file: File,
  metadata: {
    documentCode: string;
    documentType: "job_instruction" | "unit_regulation" | "professional_standard";
    title: string;
    version: string;
  },
) => {
  const query = new URLSearchParams({
    filename: file.name,
    document_code: metadata.documentCode,
    document_type: metadata.documentType,
    title: metadata.title,
    version: metadata.version,
  });
  const response = await fetch(API_URL.documents.workUpload(query), {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  return (await response.json()) as DocumentRegistry;
};

export const reviewWorkDocumentQuality = (
  userId: number,
  documentId: number,
  ocrQualityStatus: "good" | "warning",
  extractedText: string,
) =>
  request<DocumentRegistry>(API_URL.documents.workQuality(documentId), {
    userId,
    method: "PUT",
    body: { ocr_quality_status: ocrQualityStatus, extracted_text: extractedText },
  });

export const downloadWorkDocumentSource = async (_userId: number, documentId: number) => {
  const response = await fetch(API_URL.documents.workSource(documentId), {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const matchedFilename = disposition.match(/filename="([^"]+)"/)?.[1];
  link.download = matchedFilename ?? `document_${documentId}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
