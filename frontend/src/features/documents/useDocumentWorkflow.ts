import { useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

import { downloadWorkDocumentSource } from "../../api";
import { queryKeys } from "../../shared/queryKeys";
import { useDocumentMutations } from "./useDocumentMutations";

interface UseDocumentWorkflowOptions {
  queryClient: QueryClient;
  selectedUserId: number | null;
  setOperationMessage: (message: string | null) => void;
}

export function useDocumentWorkflow({ queryClient, selectedUserId, setOperationMessage }: UseDocumentWorkflowOptions) {
  const [assigningDocumentKey, setAssigningDocumentKey] = useState<string | null>(null);
  const [reviewingDocumentId, setReviewingDocumentId] = useState<number | null>(null);
  const [documentDownloadError, setDocumentDownloadError] = useState<string | null>(null);

  const { documentLinkMutation, documentUploadMutation, documentQualityMutation } = useDocumentMutations({
    selectedUserId,
    onLinkSuccess: async (registry) => {
      queryClient.setQueryData(queryKeys.hrDocuments(selectedUserId, "work"), registry);
      setAssigningDocumentKey(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(selectedUserId, "work") }),
        queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(selectedUserId, "work") }),
      ]);
    },
    onLinkError: () => setAssigningDocumentKey(null),
    onUploadSuccess: async (registry) => {
      queryClient.setQueryData(queryKeys.hrDocuments(selectedUserId, "work"), registry);
      setOperationMessage("Оригинал документа загружен. Проверьте текст перед подтверждением связи.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(selectedUserId, "work") }),
        queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(selectedUserId, "work") }),
      ]);
    },
    onQualitySuccess: async (registry) => {
      queryClient.setQueryData(queryKeys.hrDocuments(selectedUserId, "work"), registry);
      setReviewingDocumentId(null);
      setOperationMessage("Результат проверки текста сохранён в аудите.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(selectedUserId, "work") }),
        queryClient.invalidateQueries({ queryKey: queryKeys.hrAnalytics(selectedUserId, "work") }),
      ]);
    },
    onQualityError: () => setReviewingDocumentId(null),
  });

  function assignWorkDocument(
    staffingLineId: number,
    documentType: "job_instruction" | "unit_regulation" | "professional_standard",
    documentId: number | null,
  ) {
    setAssigningDocumentKey(`${staffingLineId}:${documentType}`);
    documentLinkMutation.mutate({ staffingLineId, documentType, documentId });
  }

  function addWorkDocument(
    file: File,
    documentCode: string,
    documentType: "job_instruction" | "unit_regulation" | "professional_standard",
    title: string,
    version: string,
  ) {
    setDocumentDownloadError(null);
    documentUploadMutation.mutate({ file, documentCode, documentType, title, version });
  }

  function reviewWorkDocument(documentId: number, status: "good" | "warning", text: string) {
    setReviewingDocumentId(documentId);
    documentQualityMutation.mutate({ documentId, status, text });
  }

  async function downloadWorkDocument(documentId: number) {
    if (!selectedUserId) return;
    setDocumentDownloadError(null);
    try {
      await downloadWorkDocumentSource(selectedUserId, documentId);
    } catch (error) {
      setDocumentDownloadError(
        error instanceof Error ? error.message : "Не удалось скачать оригинал документа.",
      );
    }
  }

  return {
    addWorkDocument,
    assignWorkDocument,
    assigningDocumentKey,
    documentDownloadError,
    documentLinkMutation,
    documentQualityMutation,
    documentUploadMutation,
    downloadWorkDocument,
    reviewingDocumentId,
    reviewWorkDocument,
  };
}
