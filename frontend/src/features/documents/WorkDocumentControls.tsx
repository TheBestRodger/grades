import type { DocumentRegistry } from "../../types";
import { DocumentQualityReviewBlock } from "./DocumentQualityReviewBlock";
import { DocumentUploadBlock } from "./DocumentUploadBlock";
import type { DocumentPanelProps } from "./types";

export function WorkDocumentControls({
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
  return (
    <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(300px,0.9fr)_minmax(420px,1.25fr)]">
      <DocumentUploadBlock isUploading={isUploading} onUpload={onUpload} />
      <DocumentQualityReviewBlock
        onDownloadSource={onDownloadSource}
        onReviewQuality={onReviewQuality}
        registry={registry}
        reviewingDocumentId={reviewingDocumentId}
      />
    </div>
  );
}
