import type { QuestionnaireQuestionSettingInput, QuestionnaireSettings } from "./types";
import { QuestionnaireQuestionEditor } from "./QuestionnaireQuestionEditor";
import { QuestionnaireQuestionList } from "./QuestionnaireQuestionList";

export function QuestionnaireSettingsPanel({
  questionnaire,
  questionnaireError,
  isQuestionnaireLoading,
  isQuestionnaireSaving,
  questionRows,
  activeQuestionKey,
  onActiveQuestionChange,
  onUpdateQuestionRow,
  onSubmitQuestionnaire,
}: {
  questionnaire: QuestionnaireSettings | null;
  questionnaireError: string | null;
  isQuestionnaireLoading: boolean;
  isQuestionnaireSaving: boolean;
  questionRows: QuestionnaireQuestionSettingInput[];
  activeQuestionKey: string | null;
  onActiveQuestionChange: (questionKey: string) => void;
  onUpdateQuestionRow: (questionKey: string, patch: Partial<QuestionnaireQuestionSettingInput>) => void;
  onSubmitQuestionnaire: () => void;
}) {
  const activeQuestion =
    questionnaire?.questions.find((question) => question.question_key === activeQuestionKey) ??
    questionnaire?.questions[0] ??
    null;
  const activeRow = questionRows.find((question) => question.question_key === activeQuestion?.question_key) ?? null;

  return (
    <div className="mt-8 border-t border-slate-100 pt-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Анкета</p>
          <h3 className="mt-2 text-xl font-bold text-slate-950">Настройка открытых ответов</h3>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Пока это глобальная настройка текущей анкеты: какие открытые поля проверяет ИИ-интервьюер
            и какие примеры он видит. Версии анкеты для кампаний появятся отдельным слоем.
          </p>
        </div>
        <button
          className="rounded-xl bg-blue-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
          disabled={isQuestionnaireSaving || !questionRows.length}
          onClick={onSubmitQuestionnaire}
          type="button"
        >
          {isQuestionnaireSaving ? "Сохраняю..." : "Сохранить анкету"}
        </button>
      </div>

      {isQuestionnaireLoading && <p className="mt-5 text-sm text-slate-500">Загружаю анкету...</p>}
      {questionnaireError && <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{questionnaireError}</p>}

      {questionnaire && activeQuestion && activeRow && (
        <div className="mt-5 grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <QuestionnaireQuestionList
            activeQuestionKey={activeQuestion.question_key}
            onActiveQuestionChange={onActiveQuestionChange}
            questionnaire={questionnaire}
            questionRows={questionRows}
          />
          <QuestionnaireQuestionEditor
            activeQuestion={activeQuestion}
            activeRow={activeRow}
            onUpdateQuestionRow={onUpdateQuestionRow}
          />
        </div>
      )}
    </div>
  );
}
