import { AiModeControls } from "./AiModeControls";
import { ProviderModeControls } from "./ProviderModeControls";
import type { AiConfiguration, AiConfigurationMode, AiProvider } from "./types";

export function AiSettingsPanel({
  configuration,
  isLoading,
  error,
  isSaving,
  mode,
  provider,
  baseUrl,
  modelName,
  apiToken,
  clearToken,
  clarityThreshold,
  followupStrictness,
  needsEndpoint,
  needsToken,
  onChangeMode,
  onProviderChange,
  onBaseUrlChange,
  onModelNameChange,
  onApiTokenChange,
  onClearTokenChange,
  onClarityThresholdChange,
  onFollowupStrictnessChange,
  onSubmit,
}: {
  configuration: AiConfiguration | null;
  isLoading: boolean;
  error: string | null;
  isSaving: boolean;
  mode: AiConfigurationMode;
  provider: AiProvider;
  baseUrl: string;
  modelName: string;
  apiToken: string;
  clearToken: boolean;
  clarityThreshold: number;
  followupStrictness: "soft" | "balanced" | "strict";
  needsEndpoint: boolean;
  needsToken: boolean;
  onChangeMode: (mode: AiConfigurationMode) => void;
  onProviderChange: (provider: AiProvider) => void;
  onBaseUrlChange: (value: string) => void;
  onModelNameChange: (value: string) => void;
  onApiTokenChange: (value: string) => void;
  onClearTokenChange: (value: boolean) => void;
  onClarityThresholdChange: (value: number) => void;
  onFollowupStrictnessChange: (value: "soft" | "balanced" | "strict") => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Настройки платформы</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">Режим ИИ</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Это управляемая HR-заготовка под будущий AI Gateway. Сейчас реальные вызовы LLM не выполняются,
            а персональные данные не передаются в модель.
          </p>
        </div>
        {configuration && (
          <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <p className="font-semibold text-slate-950">Текущий режим: {configuration.mode_label}</p>
            <p className="mt-1">Провайдер: {configuration.provider_label}</p>
            <p className="mt-1">Статус: {configuration.available ? "доступен" : "не подключён"}</p>
          </div>
        )}
      </div>

      {isLoading && <p className="mt-5 text-sm text-slate-500">Загружаю настройки...</p>}
      {error && <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <AiModeControls mode={mode} onChangeMode={onChangeMode} />
      <ProviderModeControls
        apiToken={apiToken}
        baseUrl={baseUrl}
        clarityThreshold={clarityThreshold}
        clearToken={clearToken}
        configuration={configuration}
        followupStrictness={followupStrictness}
        mode={mode}
        modelName={modelName}
        needsEndpoint={needsEndpoint}
        needsToken={needsToken}
        onApiTokenChange={onApiTokenChange}
        onBaseUrlChange={onBaseUrlChange}
        onClarityThresholdChange={onClarityThresholdChange}
        onClearTokenChange={onClearTokenChange}
        onFollowupStrictnessChange={onFollowupStrictnessChange}
        onModelNameChange={onModelNameChange}
        onProviderChange={onProviderChange}
        provider={provider}
      />

      <div className="mt-6 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <p className="font-semibold">Важно</p>
        <p className="mt-1">
          ИИ-модель используется только как интервьюер по одному открытому вопросу.
          В модель не отправляются ФИО, email, кадровые ID и история действий; статус профиля всё равно меняет только backend-сценарий.
        </p>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          className="rounded-xl bg-blue-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
          disabled={isSaving}
          onClick={onSubmit}
          type="button"
        >
          {isSaving ? "Сохраняю..." : "Сохранить настройки"}
        </button>
        {configuration?.updated_at && <p className="text-sm text-slate-500">Последнее изменение: {configuration.updated_at}</p>}
      </div>
    </>
  );
}
