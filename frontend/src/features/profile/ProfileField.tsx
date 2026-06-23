import type { AiAnswerCheckResult, ProfileQuestion } from "../../types";
import {
  answerBadge,
  fieldFrameClass,
  isAiCheckableQuestion,
  isQuestionFilled,
} from "./answerStatus";
import { ProfileAiCheckPanel } from "./ProfileAiCheckPanel";
import { TableAnswer } from "./TableAnswer";
import type { AnswerReviewState } from "./types";

interface ProfileFieldProps {
  question: ProfileQuestion;
  value: string | undefined;
  canEdit: boolean;
  aiEnabled: boolean;
  aiUnavailable: boolean;
  aiResult: AiAnswerCheckResult | undefined;
  aiResultCurrent: boolean;
  aiIgnored: boolean;
  aiChecking: boolean;
  aiCheckError: string | null;
  reviewState: AnswerReviewState;
  onChange: (value: string) => void;
  onAiCheck: () => void;
  onIgnoreAiResult: () => void;
}

export function ProfileField({
  question,
  value,
  canEdit,
  aiEnabled,
  aiUnavailable,
  aiResult,
  aiResultCurrent,
  aiIgnored,
  aiChecking,
  aiCheckError,
  reviewState,
  onChange,
  onAiCheck,
  onIgnoreAiResult,
}: ProfileFieldProps) {
  const filled = isQuestionFilled(question, value);
  const badge = answerBadge(reviewState);
  const aiCheckableQuestion = isAiCheckableQuestion(question);
  const canIgnoreAiRecommendation = Boolean(filled && aiResultCurrent && aiResult && !aiResult.accepted);

  return (
    <article className={`rounded-2xl border p-4 ${fieldFrameClass(reviewState)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            Поле шаблона
          </p>
          <h4 className="mt-1 text-lg font-bold text-slate-950">{question.title}</h4>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badge.className}`}>
          {badge.label}
        </span>
      </div>

      <p className="mt-3 text-sm font-medium text-slate-800">{question.question}</p>
      <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">{question.example}</p>
      {question.bad_example && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          <p>
            <span className="font-semibold text-slate-800">Слабый пример: </span>
            {question.bad_example}
          </p>
        </div>
      )}

      {question.quick_answers.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {question.quick_answers.map((answer) => (
            <button
              className="rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-900 disabled:opacity-50"
              disabled={!canEdit}
              key={answer}
              onClick={() => onChange(answer)}
              type="button"
            >
              {answer}
            </button>
          ))}
        </div>
      )}

      {question.input_type === "single_choice" ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {question.options?.map((option) => {
            const selected = value === option.label;
            return (
              <button
                className={`rounded-2xl border px-4 py-3 text-left ${
                  selected
                    ? "border-blue-400 bg-blue-50 text-blue-950"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                disabled={!canEdit}
                key={option.label}
                onClick={() => onChange(option.label)}
                type="button"
              >
                <span className="font-semibold">
                  {selected ? "✓ " : "☐ "}
                  {option.label}
                </span>
                {option.description && (
                  <span className="mt-1 block text-sm text-slate-500">{option.description}</span>
                )}
              </button>
            );
          })}
        </div>
      ) : question.input_type === "table" ? (
        <TableAnswer disabled={!canEdit} onChange={onChange} question={question} value={value} />
      ) : question.input_type === "text" ? (
        <input
          aria-label={`Ответ: ${question.title}`}
          className="mt-4 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          disabled={!canEdit}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Введите ответ..."
          value={value ?? ""}
        />
      ) : (
        <textarea
          aria-label={`Ответ: ${question.title}`}
          className="mt-4 min-h-32 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          disabled={!canEdit}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Введите ваш ответ..."
          value={value ?? ""}
        />
      )}

      {aiCheckableQuestion && (
        <ProfileAiCheckPanel
          aiCheckError={aiCheckError}
          aiChecking={aiChecking}
          aiEnabled={aiEnabled}
          aiIgnored={aiIgnored}
          aiResult={aiResult}
          aiResultCurrent={aiResultCurrent}
          aiUnavailable={aiUnavailable}
          canIgnoreAiRecommendation={canIgnoreAiRecommendation}
          filled={filled}
          onAiCheck={onAiCheck}
          onIgnoreAiResult={onIgnoreAiResult}
        />
      )}
    </article>
  );
}
