import { request } from "./request";
import { API_URL } from "./urls";
import type {
  AiConfiguration,
  AiConfigurationInput,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
} from "./types";

export const getAiSettings = (userId: number) =>
  request<AiConfiguration>(API_URL.settings.ai, { userId });

export const updateAiSettings = (userId: number, payload: AiConfigurationInput) =>
  request<AiConfiguration>(API_URL.settings.ai, {
    userId,
    method: "PUT",
    body: payload,
  });

export const getQuestionnaireSettings = (userId: number) =>
  request<QuestionnaireSettings>(API_URL.settings.questionnaire, { userId });

export const updateQuestionnaireSettings = (userId: number, payload: QuestionnaireSettingsInput) =>
  request<QuestionnaireSettings>(API_URL.settings.questionnaire, {
    userId,
    method: "PUT",
    body: payload,
  });
