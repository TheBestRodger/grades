export interface DocumentGap {
  target_type: "staffing_line" | "org_unit";
  target_id: number;
  label: string;
  title?: string;
  unit_name?: string;
  name?: string;
  path?: string;
}

export interface DocumentCoverageItem {
  document_type: "job_instruction" | "unit_regulation" | "professional_standard";
  label: string;
  total: number;
  covered: number;
  missing: number;
  percent: number;
  gaps: DocumentGap[];
}

export interface DocumentLink {
  target_type: "staffing_line" | "org_unit";
  target_id: number;
  target_label: string;
  link_status: string;
  confirmed_at: string | null;
}

export interface DocumentRecord {
  id: number;
  document_code: string;
  document_type: "job_instruction" | "unit_regulation" | "professional_standard";
  document_type_label: string;
  title: string;
  version: string;
  document_status: string;
  ocr_quality_status: string;
  ocr_quality_label: string;
  has_stored_original: boolean;
  has_extracted_text: boolean;
  content_text: string | null;
  is_demo: boolean;
  created_at: string | null;
  links: DocumentLink[];
}

export interface DocumentMatrixCell {
  covered: boolean;
  documents: Array<{
    document_id: number;
    document_code: string;
    title: string;
    link_status: string;
  }>;
}

export interface DocumentPositionMatrixRow {
  staffing_line_id: number;
  position_title: string;
  unit_name: string;
  covered_count: number;
  required_count: number;
  coverage_percent: number;
  job_instruction: DocumentMatrixCell;
  unit_regulation: DocumentMatrixCell;
  professional_standard: DocumentMatrixCell;
}

export interface DocumentRegistry {
  scope: "demo" | "work";
  note: string;
  documents_total: number;
  confirmed_documents: number;
  ocr_quality_counts: Record<string, number>;
  coverage: {
    job_instruction: DocumentCoverageItem;
    unit_regulation: DocumentCoverageItem;
    professional_standard: DocumentCoverageItem;
  };
  position_matrix: DocumentPositionMatrixRow[];
  documents: DocumentRecord[];
}
