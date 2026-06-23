import { useEffect, useState } from "react";

import { AiSettingsPanel } from "./AiSettingsPanel";
import { defaultProvider } from "./settingsOptions";
import { QuestionnaireSettingsPanel } from "./QuestionnaireSettingsPanel";
import type {
  AiConfigurationMode,
  AiProvider,
  QuestionnaireQuestionSettingInput,
  SettingsPanelProps,
} from "./types";

export function SettingsPanel({
  configuration,
  questionnaire,
  error,
  questionnaireError,
  isLoading,
  isQuestionnaireLoading,
  isSaving,
  isQuestionnaireSaving,
  onSave,
  onSaveQuestionnaire,
}: SettingsPanelProps) {
  const [mode, setMode] = useState<AiConfigurationMode>("default");
  const [provider, setProvider] = useState<AiProvider>("off");
  const [baseUrl, setBaseUrl] = useState("");
  const [modelName, setModelName] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [clearToken, setClearToken] = useState(false);
  const [clarityThreshold, setClarityThreshold] = useState(70);
  const [followupStrictness, setFollowupStrictness] = useState<"soft" | "balanced" | "strict">("balanced");
  const [questionRows, setQuestionRows] = useState<QuestionnaireQuestionSettingInput[]>([]);
  const [activeQuestionKey, setActiveQuestionKey] = useState<string | null>(null);

  useEffect(() => {
    if (!configuration) return;
    setMode(configuration.mode);
    setProvider(configuration.provider);
    setBaseUrl(configuration.base_url ?? "");
    setModelName(configuration.model_name ?? "");
    setApiToken("");
    setClearToken(false);
    setClarityThreshold(configuration.clarity_threshold);
    setFollowupStrictness(configuration.followup_strictness);
  }, [configuration]);

  useEffect(() => {
    if (!questionnaire) return;
    const rows = questionnaire.questions.map((question) => ({
      question_key: question.question_key,
      ai_check_enabled: question.ai_check_enabled,
      good_example: question.good_example,
      bad_example: question.bad_example,
      requirements: question.requirements,
    }));
    setQuestionRows(rows);
    setActiveQuestionKey((current) =>
      current && rows.some((question) => question.question_key === current) ? current : rows[0]?.question_key ?? null,
    );
  }, [questionnaire]);

  const needsEndpoint = mode === "local" || mode === "token";
  const needsToken = mode === "token";

  function changeMode(nextMode: AiConfigurationMode) {
    setMode(nextMode);
    setProvider(defaultProvider(nextMode));
    if (nextMode === "default" || nextMode === "off") {
      setBaseUrl("");
      setModelName("");
      setApiToken("");
      setClearToken(true);
    }
  }

  function submit() {
    onSave({
      mode,
      provider,
      base_url: needsEndpoint ? baseUrl || null : null,
      model_name: needsEndpoint ? modelName || null : null,
      api_token: needsToken && apiToken ? apiToken : null,
      clear_api_token: clearToken || (!needsToken && configuration?.api_token_configured),
      clarity_threshold: clarityThreshold,
      followup_strictness: followupStrictness,
    });
  }

  function updateQuestionRow(questionKey: string, patch: Partial<QuestionnaireQuestionSettingInput>) {
    setQuestionRows((existing) =>
      existing.map((question) => (question.question_key === questionKey ? { ...question, ...patch } : question)),
    );
  }

  function submitQuestionnaire() {
    onSaveQuestionnaire({
      questions: questionRows.map((question) => ({
        ...question,
        good_example: question.good_example || null,
        bad_example: question.bad_example || null,
        requirements: question.requirements || null,
      })),
    });
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <AiSettingsPanel
        apiToken={apiToken}
        baseUrl={baseUrl}
        clarityThreshold={clarityThreshold}
        clearToken={clearToken}
        configuration={configuration}
        error={error}
        followupStrictness={followupStrictness}
        isLoading={isLoading}
        isSaving={isSaving}
        mode={mode}
        modelName={modelName}
        needsEndpoint={needsEndpoint}
        needsToken={needsToken}
        onApiTokenChange={setApiToken}
        onBaseUrlChange={setBaseUrl}
        onChangeMode={changeMode}
        onClarityThresholdChange={setClarityThreshold}
        onClearTokenChange={setClearToken}
        onFollowupStrictnessChange={setFollowupStrictness}
        onModelNameChange={setModelName}
        onProviderChange={setProvider}
        onSubmit={submit}
        provider={provider}
      />
      <QuestionnaireSettingsPanel
        activeQuestionKey={activeQuestionKey}
        isQuestionnaireLoading={isQuestionnaireLoading}
        isQuestionnaireSaving={isQuestionnaireSaving}
        onActiveQuestionChange={setActiveQuestionKey}
        onSubmitQuestionnaire={submitQuestionnaire}
        onUpdateQuestionRow={updateQuestionRow}
        questionnaire={questionnaire}
        questionnaireError={questionnaireError}
        questionRows={questionRows}
      />
    </section>
  );
}
