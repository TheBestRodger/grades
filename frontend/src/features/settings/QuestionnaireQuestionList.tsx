import type { QuestionnaireQuestionSettingInput, QuestionnaireSettings } from "./types";

export function QuestionnaireQuestionList({
  questionnaire,
  questionRows,
  activeQuestionKey,
  onActiveQuestionChange,
}: {
  questionnaire: QuestionnaireSettings;
  questionRows: QuestionnaireQuestionSettingInput[];
  activeQuestionKey: string | null;
  onActiveQuestionChange: (questionKey: string) => void;
}) {
  return (
    <div className="max-h-[620px] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
      {questionnaire.questions.map((question) => {
        const row = questionRows.find((item) => item.question_key === question.question_key);
        const active = question.question_key === activeQuestionKey;
        return (
          <button
            className={`mb-2 w-full rounded-xl border px-3 py-3 text-left text-sm last:mb-0 ${
              active
                ? "border-blue-400 bg-blue-50 text-blue-950"
                : "border-slate-200 bg-white text-slate-700 hover:border-blue-200"
            }`}
            key={question.question_key}
            onClick={() => onActiveQuestionChange(question.question_key)}
            type="button"
          >
            <span className="block text-xs font-semibold text-slate-400">{question.section}</span>
            <span className="mt-1 block font-semibold">{question.title}</span>
            <span className={`mt-2 inline-block rounded-full px-2 py-1 text-xs font-semibold ${
              row?.ai_check_enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"
            }`}>
              {row?.ai_check_enabled ? "AI-проверка включена" : "AI-проверка выключена"}
            </span>
          </button>
        );
      })}
    </div>
  );
}
