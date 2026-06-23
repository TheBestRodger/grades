import type { AiConfigurationMode, AiProvider } from "./types";

export const modeOptions: Array<{ value: AiConfigurationMode; label: string; note: string }> = [
  { value: "default", label: "По умолчанию", note: "Берётся из переменных окружения сервера." },
  { value: "off", label: "Без ИИ", note: "Анкета, документы и аналитика работают полностью локально." },
  { value: "local", label: "Локальная ИИ", note: "Заготовка под Ollama или LM Studio на локальной машине." },
  { value: "token", label: "По токену", note: "Заготовка под OpenAI-compatible endpoint с API-токеном." },
];

export const providerOptions: Record<AiConfigurationMode, Array<{ value: AiProvider; label: string }>> = {
  default: [{ value: "off", label: "Без провайдера" }],
  off: [{ value: "off", label: "Без провайдера" }],
  local: [
    { value: "ollama", label: "Ollama" },
    { value: "lm_studio", label: "LM Studio" },
  ],
  token: [{ value: "openai_compatible", label: "OpenAI-compatible API" }],
};

export function defaultProvider(mode: AiConfigurationMode): AiProvider {
  return providerOptions[mode][0].value;
}
