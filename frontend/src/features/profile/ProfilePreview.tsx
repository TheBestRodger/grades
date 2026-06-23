import type { ProfileQuestion } from "../../types";
import { formatAnswer } from "./answerStatus";

interface ProfilePreviewProps {
  answers: Record<string, string>;
  questions: ProfileQuestion[] | undefined;
}

export function ProfilePreview({ answers, questions }: ProfilePreviewProps) {
  return (
    <aside className="h-fit rounded-2xl bg-slate-50 p-4">
      <h3 className="font-bold text-slate-900">Краткий просмотр текущего раздела</h3>
      <div className="mt-3 space-y-3">
        {questions?.map((item) => (
          <div key={item.key}>
            <p className="text-xs font-semibold text-slate-500">{item.title}</p>
            <p className="mt-1 line-clamp-3 text-sm text-slate-700">
              {formatAnswer(item, answers[item.key])}
            </p>
          </div>
        ))}
      </div>
    </aside>
  );
}
