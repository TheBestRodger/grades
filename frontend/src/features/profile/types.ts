import type { AiAnswerCheckResult, AiStatus, EmployeeProfile, ProfileAnswerStatus, ProfileQuestion } from "../../types";

export interface ProfileWorkspaceProps {
  profile: EmployeeProfile;
  ai: AiStatus | undefined;
  error: string | null;
  isSaving: boolean;
  isSubmitting: boolean;
  aiCheckResults: Record<string, AiAnswerCheckResult>;
  aiAnswerSnapshots: Record<string, string>;
  aiCheckingKey: string | null;
  aiCheckError: string | null;
  onSave: (profileId: number, answers: Record<string, string>, aiUsage: AiUsage) => Promise<EmployeeProfile>;
  onSubmit: (profileId: number, answers: Record<string, string>, aiUsage: AiUsage) => Promise<EmployeeProfile>;
  onExport: (profileId: number) => Promise<void>;
  onAiCheck: (
    profileId: number,
    questionKey: string,
    answers: Record<string, string>,
  ) => Promise<AiAnswerCheckResult>;
}

export interface AiUsage {
  ai_checked_questions: string[];
  ai_ignored_questions: string[];
  ai_without_ai_questions: string[];
  ai_answer_statuses: Record<string, ProfileAnswerStatus>;
}

export interface LocalDraftPayload {
  answers?: Record<string, string>;
  ai_usage?: Partial<AiUsage>;
  updated_at?: string;
}

export interface ProfileSection {
  title: string;
  questions: ProfileQuestion[];
}

export interface SectionProgress {
  filled: number;
  total: number;
  complete: boolean;
  hasIgnoredAi: boolean;
  hasWithoutAi: boolean;
  hasRejectedAi: boolean;
  hasDraft: boolean;
}

export type AnswerReviewState = "empty" | "draft" | "accepted" | "rejected" | "ignored" | "without_ai";

export type SaveAction =
  | { type: "next" }
  | { type: "exit" }
  | { type: "navigate"; index: number };
