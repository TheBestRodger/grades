import { providerOptions } from "./settingsOptions";
import type { AiConfiguration, AiConfigurationMode, AiProvider } from "./types";

export function ProviderModeControls({
  mode,
  provider,
  baseUrl,
  modelName,
  apiToken,
  clearToken,
  clarityThreshold,
  followupStrictness,
  configuration,
  needsEndpoint,
  needsToken,
  onProviderChange,
  onBaseUrlChange,
  onModelNameChange,
  onApiTokenChange,
  onClearTokenChange,
  onClarityThresholdChange,
  onFollowupStrictnessChange,
}: {
  mode: AiConfigurationMode;
  provider: AiProvider;
  baseUrl: string;
  modelName: string;
  apiToken: string;
  clearToken: boolean;
  clarityThreshold: number;
  followupStrictness: "soft" | "balanced" | "strict";
  configuration: AiConfiguration | null;
  needsEndpoint: boolean;
  needsToken: boolean;
  onProviderChange: (provider: AiProvider) => void;
  onBaseUrlChange: (value: string) => void;
  onModelNameChange: (value: string) => void;
  onApiTokenChange: (value: string) => void;
  onClearTokenChange: (value: boolean) => void;
  onClarityThresholdChange: (value: number) => void;
  onFollowupStrictnessChange: (value: "soft" | "balanced" | "strict") => void;
}) {
  return (
    <>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Провайдер
          <select
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700"
            onChange={(event) => onProviderChange(event.target.value as AiProvider)}
            value={provider}
          >
            {providerOptions[mode].map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Base URL
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsEndpoint}
            onChange={(event) => onBaseUrlChange(event.target.value)}
            placeholder={provider === "ollama" ? "http://localhost:11434" : "http://localhost:1234/v1"}
            value={baseUrl}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Модель
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsEndpoint}
            onChange={(event) => onModelNameChange(event.target.value)}
            placeholder={provider === "ollama" ? "llama3.1" : "local-model"}
            value={modelName}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          API token
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsToken}
            onChange={(event) => onApiTokenChange(event.target.value)}
            placeholder={configuration?.api_token_configured ? "Токен уже сохранён" : "Будет скрыт после сохранения"}
            type="password"
            value={apiToken}
          />
        </label>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Порог понятности ответа: {clarityThreshold}%
          <input
            className="mt-3 w-full"
            max={100}
            min={0}
            onChange={(event) => onClarityThresholdChange(Number(event.target.value))}
            type="range"
            value={clarityThreshold}
          />
          <span className="mt-1 block text-xs text-slate-500">
            Если ИИ-модель оценит ответ ниже порога, человеку будет показан уточняющий вопрос.
          </span>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Насколько ассистент будет докапываться
          <select
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700"
            onChange={(event) => onFollowupStrictnessChange(event.target.value as "soft" | "balanced" | "strict")}
            value={followupStrictness}
          >
            <option value="soft">Мягко</option>
            <option value="balanced">Сбалансированно</option>
            <option value="strict">Строго</option>
          </select>
          <span className="mt-1 block text-xs text-slate-500">
            Строгий режим чаще просит уточнить ответ, если он не раскрывает вопрос анкеты.
          </span>
        </label>
      </div>

      {configuration?.api_token_configured && needsToken && (
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-600">
          <input checked={clearToken} onChange={(event) => onClearTokenChange(event.target.checked)} type="checkbox" />
          Очистить сохранённый токен
        </label>
      )}
    </>
  );
}
