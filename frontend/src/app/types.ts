import type { Assignment, Position, ProfileAnswerStatus } from "../types";
import type { useAppControllerContext } from "./useAppControllerContext";

export type AppControllerContext = ReturnType<typeof useAppControllerContext>["controllerContext"];

export type ProfileAiUsagePayload = {
  ai_checked_questions: string[];
  ai_ignored_questions: string[];
  ai_without_ai_questions?: string[];
  ai_answer_statuses?: Record<string, ProfileAnswerStatus>;
};

export type StructureDeleteTarget = {
  kind: "assignment" | "position";
  id: number;
  label: string;
  force: boolean;
  warning: string | null;
};

export type EmployeeEditTarget = {
  assignment: Assignment;
  position: Position;
};
