import { DocumentPanel } from "../features/documents";
import type { AppControllerContext } from "../app/types";

interface DocumentsPageProps
  extends Pick<
    AppControllerContext,
    | "activeSection"
    | "assigningDocumentKey"
    | "dataScope"
    | "documentDownloadError"
    | "documents"
    | "isHr"
    | "isManager"
    | "managerDocuments"
    | "reviewingDocumentId"
    | "tree"
    | "workTree"
  > {
  documentLinkError: string | null;
  documentQualityError: string | null;
  documentUploadError: string | null;
  isUploading: boolean;
  onDownloadSource: (documentId: number) => void;
  onReviewQuality: AppControllerContext["reviewWorkDocument"];
  onSetLink: AppControllerContext["assignWorkDocument"];
  onUpload: AppControllerContext["addWorkDocument"];
}

export function DocumentsPage({
  activeSection,
  assigningDocumentKey,
  dataScope,
  documentDownloadError,
  documentLinkError,
  documentQualityError,
  documents,
  documentUploadError,
  isHr,
  isManager,
  isUploading,
  managerDocuments,
  onDownloadSource,
  onReviewQuality,
  onSetLink,
  onUpload,
  reviewingDocumentId,
  tree,
  workTree,
}: DocumentsPageProps) {
  if (activeSection !== "documents") return null;

  if (dataScope === "work" && isHr) {
    return (
      <DocumentPanel
        assigningKey={assigningDocumentKey}
        canEdit
        error={
          documents.error?.message ??
          documentLinkError ??
          documentUploadError ??
          documentQualityError ??
          documentDownloadError ??
          null
        }
        isLoading={documents.isLoading}
        isUploading={isUploading}
        onDownloadSource={onDownloadSource}
        onReviewQuality={onReviewQuality}
        onSetLink={onSetLink}
        onUpload={onUpload}
        registry={documents.data ?? null}
        reviewingDocumentId={reviewingDocumentId}
        tree={workTree.data?.nodes ?? []}
      />
    );
  }

  if (dataScope === "demo" && isHr) {
    return (
      <DocumentPanel
        error={documents.error?.message ?? null}
        isLoading={documents.isLoading}
        registry={documents.data ?? null}
        tree={tree.data?.nodes ?? []}
      />
    );
  }

  if (isManager) {
    return (
      <DocumentPanel
        error={managerDocuments.error?.message ?? null}
        isLoading={managerDocuments.isLoading}
        registry={managerDocuments.data ?? null}
        tree={tree.data?.nodes ?? []}
        viewer="manager"
      />
    );
  }

  return null;
}
