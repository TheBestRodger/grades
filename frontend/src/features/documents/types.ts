import type {
  DocumentPositionMatrixRow,
  DocumentRegistry,
  OrgNode,
  Position,
} from "../../types";

export type DocumentType = "job_instruction" | "unit_regulation" | "professional_standard";

export interface DocumentPanelProps {
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

export interface VisibleUnit {
  source: OrgNode;
  positions: Position[];
  children: VisibleUnit[];
}

export type DocumentMatrixByLine = Map<number, DocumentPositionMatrixRow>;
