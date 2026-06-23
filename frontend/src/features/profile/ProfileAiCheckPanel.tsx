import { useState } from "react";

import type { AiAnswerCheckResult } from "../../types";

interface ProfileAiCheckPanelProps {
  aiCheckError: string | null;
  aiChecking: boolean;
  aiEnabled: boolean;
  aiIgnored: boolean;
  aiResult: AiAnswerCheckResult | undefined;
  aiResultCurrent: boolean;
  aiUnavailable: boolean;
  canIgnoreAiRecommendation: boolean;
  filled: boolean;
  onAiCheck: () => void;
  onIgnoreAiResult: () => void;
}

export function ProfileAiCheckPanel({
  aiCheckError,
  aiChecking,
  aiEnabled,
  aiIgnored,
  aiResult,
  aiResultCurrent,
  aiUnavailable,
  canIgnoreAiRecommendation,
  filled,
  onAiCheck,
  onIgnoreAiResult,
}: ProfileAiCheckPanelProps) {
  const [offlineAiNotice, setOfflineAiNotice] = useState(false);
  const clarityStyle =
    aiResult && !aiResultCurrent
      ? "border-slate-200 bg-slate-50 text-slate-700"
      : aiResult?.accepted
        ? "border-emerald-200 bg-emerald-50 text-emerald-900"
        : "border-amber-200 bg-amber-50 text-amber-900";
  const clarityLabel = aiResult && `${aiResult.clarity_percent}% / порог ${aiResult.clarity_threshold}%`;

  return (
    <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-blue-950">AI-проверка ответа</p>
          {!aiEnabled && (
            <p className="mt-1 text-amber-900">
              ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            className="rounded-xl bg-blue-950 px-4 py-2 text-xs font-semibold text-white disabled:bg-slate-300"
            disabled={!filled || aiChecking}
            onClick={() => {
              if (!aiEnabled) {
                setOfflineAiNotice(true);
                return;
              }
              setOfflineAiNotice(false);
              onAiCheck();
            }}
            type="button"
          >
            {aiChecking ? "Отправляю..." : "Ответить"}
          </button>
          {canIgnoreAiRecommendation && (
            <button
              className={`rounded-xl border px-4 py-2 text-xs font-bold shadow-sm transition ${
                aiIgnored
                  ? "border-amber-700 bg-amber-700 text-white hover:bg-amber-800"
                  : "border-orange-600 bg-orange-500 text-white hover:bg-orange-600"
              }`}
              onClick={onIgnoreAiResult}
              type="button"
            >
              {aiIgnored ? "Рекомендация ИИ проигнорирована" : "Игнорировать рекомендацию ИИ"}
            </button>
          )}
        </div>
      </div>
      {offlineAiNotice && !aiEnabled && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
          ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос.
        </p>
      )}
      {aiCheckError && (
        <p
          className={`mt-3 rounded-xl px-3 py-2 ${
            aiUnavailable ? "border border-amber-200 bg-amber-50 text-amber-900" : "bg-red-50 text-red-700"
          }`}
        >
          {aiUnavailable
            ? "ИИ недоступен. Постарайтесь ответить максимально четко и полно на вопрос."
            : aiCheckError}
        </p>
      )}
      {filled && aiResult && (
        <div className={`mt-3 rounded-xl border px-3 py-2 ${clarityStyle}`}>
          <p className="font-semibold">
            {!aiResultCurrent
              ? `Понятность: ${clarityLabel} · ответ изменён после проверки`
              : aiResult.accepted
                ? "Ответ принят"
                : `Понятность: ${clarityLabel} · нужно уточнить`}
          </p>
          {!aiResultCurrent ? (
            <p className="mt-1">Проверьте ответ заново, чтобы ИИ оценил текущий текст.</p>
          ) : !aiResult.accepted ? (
            <p className="mt-1">{aiResult.explanation}</p>
          ) : null}
          {aiResultCurrent && aiResult.accepted && <p className="mt-1">Ответ принят.</p>}
          {aiResultCurrent && !aiResult.accepted && aiResult.followup_question && (
            <p className="mt-2 font-medium">Уточняющий вопрос: {aiResult.followup_question}</p>
          )}
          {aiResultCurrent && !aiResult.accepted && aiIgnored && (
            <p className="mt-3 text-xs text-amber-800">Ответ будет сохранён как решение пользователя.</p>
          )}
        </div>
      )}
    </div>
  );
}
