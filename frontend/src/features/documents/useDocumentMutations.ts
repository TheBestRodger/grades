import { useMutation } from "@tanstack/react-query";

import { reviewWorkDocumentQuality, setWorkDocumentLink, uploadWorkDocument } from "../../api";
import type { DocumentRegistry } from "../../types";

interface DocumentMutationOptions {
  selectedUserId: number | null;
  onLinkSuccess?: (registry: DocumentRegistry) => void | Promise<void>;
  onLinkError?: () => void;
  onUploadSuccess?: (registry: DocumentRegistry) => void | Promise<void>;
  onQualitySuccess?: (registry: DocumentRegistry) => void | Promise<void>;
  onQualityError?: () => void;
}

export function useDocumentMutations(options: DocumentMutationOptions) {
  const documentLinkMutation = useMutation({
    mutationFn: ({
      staffingLineId,
      documentType,
      documentId,
    }: {
      staffingLineId: number;
      documentType: "job_instruction" | "unit_regulation" | "professional_standard";
      documentId: number | null;
    }) => setWorkDocumentLink(options.selectedUserId!, staffingLineId, documentType, documentId),
    onSuccess: options.onLinkSuccess,
    onError: options.onLinkError,
  });
  const documentUploadMutation = useMutation({
    mutationFn: ({
      file,
      documentCode,
      documentType,
      title,
      version,
    }: {
      file: File;
      documentCode: string;
      documentType: "job_instruction" | "unit_regulation" | "professional_standard";
      title: string;
      version: string;
    }) =>
      uploadWorkDocument(options.selectedUserId!, file, {
        documentCode,
        documentType,
        title,
        version,
      }),
    onSuccess: options.onUploadSuccess,
  });
  const documentQualityMutation = useMutation({
    mutationFn: ({ documentId, status, text }: { documentId: number; status: "good" | "warning"; text: string }) =>
      reviewWorkDocumentQuality(options.selectedUserId!, documentId, status, text),
    onSuccess: options.onQualitySuccess,
    onError: options.onQualityError,
  });

  return { documentLinkMutation, documentUploadMutation, documentQualityMutation };
}
