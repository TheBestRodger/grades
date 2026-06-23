import { request } from "./request";
import { API_URL } from "./urls";
import type { AiAnswerCheckResult, EmployeeProfile, ProfileAnswerStatus } from "./types";

type AiUsagePayload = {
  ai_checked_questions?: string[];
  ai_ignored_questions?: string[];
  ai_without_ai_questions?: string[];
  ai_answer_statuses?: Record<string, ProfileAnswerStatus>;
};

export const getMyProfiles = (userId: number) =>
  request<EmployeeProfile[]>(API_URL.profile.myProfiles, { userId });

export const saveProfileDraft = (
  userId: number,
  profileId: number,
  answers: Record<string, string>,
  aiUsage?: AiUsagePayload,
) =>
  request<EmployeeProfile>(API_URL.profile.draft(profileId), {
    userId,
    method: "PUT",
    body: { answers, ...(aiUsage ?? {}) },
  });

export const submitProfile = (
  userId: number,
  profileId: number,
  answers: Record<string, string>,
  aiUsage?: AiUsagePayload,
) =>
  request<EmployeeProfile>(API_URL.profile.submit(profileId), {
    userId,
    method: "POST",
    body: { answers, ...(aiUsage ?? {}) },
  });

export const checkProfileAnswer = (
  userId: number,
  profileId: number,
  questionKey: string,
  answers: Record<string, string>,
  previous?: {
    previous_answer?: string | null;
    previous_followup_question?: string | null;
    previous_clarity_percent?: number | null;
  },
) =>
  request<AiAnswerCheckResult>(API_URL.profile.aiCheck(profileId), {
    userId,
    method: "POST",
    body: { question_key: questionKey, answers, ...(previous ?? {}) },
  });
