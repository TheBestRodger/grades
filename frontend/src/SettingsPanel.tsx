import { useEffect, useState } from "react";

import type {
  AiConfiguration,
  AiConfigurationInput,
  AiConfigurationMode,
  AiProvider,
  QuestionnaireQuestionSettingInput,
  QuestionnaireSettings,
  QuestionnaireSettingsInput,
} from "./types";

const modeOptions: Array<{ value: AiConfigurationMode; label: string; note: string }> = [
  { value: "default", label: "По умолчанию", note: "Берётся из переменных окружения сервера." },
  { value: "off", label: "Без ИИ", note: "Анкета, документы и аналитика работают полностью локально." },
  { value: "local", label: "Локальная ИИ", note: "Заготовка под Ollama или LM Studio на локальной машине." },
  { value: "token", label: "По токену", note: "Заготовка под OpenAI-compatible endpoint с API-токеном." },
];

const providerOptions: Record<AiConfigurationMode, Array<{ value: AiProvider; label: string }>> = {
  default: [{ value: "off", label: "Без провайдера" }],
  off: [{ value: "off", label: "Без провайдера" }],
  local: [
    { value: "ollama", label: "Ollama" },
    { value: "lm_studio", label: "LM Studio" },
  ],
  token: [{ value: "openai_compatible", label: "OpenAI-compatible API" }],
};

function defaultProvider(mode: AiConfigurationMode): AiProvider {
  return providerOptions[mode][0].value;
}

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
}: {
  configuration: AiConfiguration | null;
  questionnaire: QuestionnaireSettings | null;
  error: string | null;
  questionnaireError: string | null;
  isLoading: boolean;
  isQuestionnaireLoading: boolean;
  isSaving: boolean;
  isQuestionnaireSaving: boolean;
  onSave: (payload: AiConfigurationInput) => void;
  onSaveQuestionnaire: (payload: QuestionnaireSettingsInput) => void;
}) {
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
      current && rows.some((question) => question.question_key === current)
        ? current
        : rows[0]?.question_key ?? null,
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

  const activeQuestion =
    questionnaire?.questions.find((question) => question.question_key === activeQuestionKey) ??
    questionnaire?.questions[0] ??
    null;
  const activeRow =
    questionRows.find((question) => question.question_key === activeQuestion?.question_key) ?? null;

  function updateQuestionRow(
    questionKey: string,
    patch: Partial<QuestionnaireQuestionSettingInput>,
  ) {
    setQuestionRows((existing) =>
      existing.map((question) =>
        question.question_key === questionKey ? { ...question, ...patch } : question,
      ),
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
            Настройки платформы
          </p>
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

      <div className="mt-6 grid gap-4 xl:grid-cols-4">
        {modeOptions.map((option) => (
          <button
            className={`rounded-2xl border p-4 text-left ${
              mode === option.value
                ? "border-blue-800 bg-blue-50 text-blue-950"
                : "border-slate-200 bg-slate-50 text-slate-700 hover:border-blue-200"
            }`}
            key={option.value}
            onClick={() => changeMode(option.value)}
            type="button"
          >
            <p className="font-semibold">{option.label}</p>
            <p className="mt-2 text-sm">{option.note}</p>
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Провайдер
          <select
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700"
            onChange={(event) => setProvider(event.target.value as AiProvider)}
            value={provider}
          >
            {providerOptions[mode].map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Base URL
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsEndpoint}
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder={provider === "ollama" ? "http://localhost:11434" : "http://localhost:1234/v1"}
            value={baseUrl}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Модель
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsEndpoint}
            onChange={(event) => setModelName(event.target.value)}
            placeholder={provider === "ollama" ? "llama3.1" : "local-model"}
            value={modelName}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          API token
          <input
            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-2 outline-none focus:border-blue-700 disabled:bg-slate-100"
            disabled={!needsToken}
            onChange={(event) => setApiToken(event.target.value)}
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
            onChange={(event) => setClarityThreshold(Number(event.target.value))}
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
            onChange={(event) => setFollowupStrictness(event.target.value as "soft" | "balanced" | "strict")}
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
          <input
            checked={clearToken}
            onChange={(event) => setClearToken(event.target.checked)}
            type="checkbox"
          />
          Очистить сохранённый токен
        </label>
      )}

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
          onClick={submit}
          type="button"
        >
          {isSaving ? "Сохраняю..." : "Сохранить настройки"}
        </button>
        {configuration?.updated_at && (
          <p className="text-sm text-slate-500">Последнее изменение: {configuration.updated_at}</p>
        )}
      </div>

      <div className="mt-8 border-t border-slate-100 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              Анкета
            </p>
            <h3 className="mt-2 text-xl font-bold text-slate-950">Настройка открытых ответов</h3>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Пока это глобальная настройка текущей анкеты: какие открытые поля проверяет ИИ-интервьюер
              и какие примеры он видит. Версии анкеты для кампаний появятся отдельным слоем.
            </p>
          </div>
          <button
            className="rounded-xl bg-blue-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
            disabled={isQuestionnaireSaving || !questionRows.length}
            onClick={submitQuestionnaire}
            type="button"
          >
            {isQuestionnaireSaving ? "Сохраняю..." : "Сохранить анкету"}
          </button>
        </div>

        {isQuestionnaireLoading && <p className="mt-5 text-sm text-slate-500">Загружаю анкету...</p>}
        {questionnaireError && (
          <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {questionnaireError}
          </p>
        )}

        {questionnaire && activeQuestion && activeRow && (
          <div className="mt-5 grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
            <div className="max-h-[620px] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
              {questionnaire.questions.map((question) => {
                const row = questionRows.find((item) => item.question_key === question.question_key);
                const active = question.question_key === activeQuestion.question_key;
                return (
                  <button
                    className={`mb-2 w-full rounded-xl border px-3 py-3 text-left text-sm last:mb-0 ${
                      active
                        ? "border-blue-400 bg-blue-50 text-blue-950"
                        : "border-slate-200 bg-white text-slate-700 hover:border-blue-200"
                    }`}
                    key={question.question_key}
                    onClick={() => setActiveQuestionKey(question.question_key)}
                    type="button"
                  >
                    <span className="block text-xs font-semibold text-slate-400">{question.section}</span>
                    <span className="mt-1 block font-semibold">{question.title}</span>
                    <span className={`mt-2 inline-block rounded-full px-2 py-1 text-xs font-semibold ${
                      row?.ai_check_enabled
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-slate-200 text-slate-600"
                    }`}>
                      {row?.ai_check_enabled ? "AI-проверка включена" : "AI-проверка выключена"}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                {activeQuestion.section}
              </p>
              <h4 className="mt-2 text-lg font-bold text-slate-950">{activeQuestion.title}</h4>
              <p className="mt-2 text-sm text-slate-700">{activeQuestion.question}</p>
              <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Базовый пример: {activeQuestion.base_example}
              </p>

              <label className="mt-4 flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  checked={activeRow.ai_check_enabled}
                  onChange={(event) =>
                    updateQuestionRow(activeRow.question_key, { ai_check_enabled: event.target.checked })
                  }
                  type="checkbox"
                />
                Проверять этот ответ локальным AI-интервьюером
              </label>

              <label className="mt-4 block text-sm font-medium text-slate-700">
                Пример хорошего ответа
                <textarea
                  className="mt-2 min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) =>
                    updateQuestionRow(activeRow.question_key, { good_example: event.target.value })
                  }
                  value={activeRow.good_example ?? ""}
                />
              </label>
              <label className="mt-4 block text-sm font-medium text-slate-700">
                Пример слабого ответа
                <textarea
                  className="mt-2 min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) =>
                    updateQuestionRow(activeRow.question_key, { bad_example: event.target.value })
                  }
                  placeholder="Например: слишком общий ответ без результата, масштаба или объекта ответственности."
                  value={activeRow.bad_example ?? ""}
                />
              </label>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
