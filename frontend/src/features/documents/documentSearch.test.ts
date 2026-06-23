import { describe, expect, it } from "vitest";

import type { DocumentRecord } from "../../types";
import {
  filterDocumentsForSearch,
  getDocumentQualityStatusText,
  isDocumentLinkDisabled,
  matchesDocumentSearch,
} from "./documentSearch";

function makeDocument(overrides: Partial<DocumentRecord> = {}): DocumentRecord {
  return {
    id: 1,
    document_code: "DI-001",
    document_type: "job_instruction",
    document_type_label: "ДИ",
    title: "Должностная инструкция инженера",
    version: "v2",
    document_status: "active",
    ocr_quality_status: "good",
    ocr_quality_label: "Текст проверен",
    has_stored_original: true,
    has_extracted_text: true,
    content_text: "text",
    is_demo: false,
    created_at: null,
    links: [],
    ...overrides,
  };
}

describe("documentSearch", () => {
  it("matches documents by title, code and version", () => {
    const document = makeDocument();

    expect(matchesDocumentSearch(document, "инженера")).toBe(true);
    expect(matchesDocumentSearch(document, "di-001")).toBe(true);
    expect(matchesDocumentSearch(document, "V2")).toBe(true);
  });

  it("returns all documents for empty search", () => {
    const documents = [makeDocument({ id: 1 }), makeDocument({ id: 2, document_code: "PS-002" })];

    expect(filterDocumentsForSearch(documents, "  ")).toHaveLength(2);
  });

  it("returns no documents when nothing matches", () => {
    const documents = [makeDocument()];

    expect(filterDocumentsForSearch(documents, "несуществующий документ")).toEqual([]);
  });

  it("keeps previous unavailable document rule", () => {
    expect(isDocumentLinkDisabled(makeDocument({ ocr_quality_status: "warning" }))).toBe(true);
    expect(isDocumentLinkDisabled(makeDocument({ has_stored_original: false, ocr_quality_status: "warning" }))).toBe(false);
  });

  it("returns quality label fallback", () => {
    expect(getDocumentQualityStatusText(makeDocument({ ocr_quality_label: "" }))).toBe("good");
  });
});
