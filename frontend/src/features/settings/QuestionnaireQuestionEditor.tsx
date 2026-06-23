import type { QuestionnaireQuestionSettingInput, QuestionnaireSettings } from "./types";

export function QuestionnaireQuestionEditor({
  activeQuestion,
  activeRow,
  onUpdateQuestionRow,
}: {
  activeQuestion: QuestionnaireSettings["questions"][number];
  activeRow: QuestionnaireQuestionSettingInput;
  onUpdateQuestionRow: (questionKey: string, patch: Partial<QuestionnaireQuestionSettingInput>) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{activeQuestion.section}</p>
      <h4 className="mt-2 text-lg font-bold text-slate-950">{activeQuestion.title}</h4>
      <p className="mt-2 text-sm text-slate-700">{activeQuestion.question}</p>
      <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
        Базовый пример: {activeQuestion.base_example}
      </p>

      <label className="mt-4 flex items-center gap-2 text-sm font-medium text-slate-700">
        <input
          checked={activeRow.ai_check_enabled}
          onChange={(event) => onUpdateQuestionRow(activeRow.question_key, { ai_check_enabled: event.target.checked })}
          type="checkbox"
        />
        Проверять этот ответ локальным AI-интервьюером
      </label>

      <label className="mt-4 block text-sm font-medium text-slate-700">
        Пример хорошего ответа
        <textarea
          className="mt-2 min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          onChange={(event) => onUpdateQuestionRow(activeRow.question_key, { good_example: event.target.value })}
          value={activeRow.good_example ?? ""}
        />
      </label>
      <label className="mt-4 block text-sm font-medium text-slate-700">
        Пример слабого ответа
        <textarea
          className="mt-2 min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
          onChange={(event) => onUpdateQuestionRow(activeRow.question_key, { bad_example: event.target.value })}
          placeholder="Например: слишком общий ответ без результата, масштаба или объекта ответственности."
          value={activeRow.bad_example ?? ""}
        />
      </label>
    </div>
  );
}
