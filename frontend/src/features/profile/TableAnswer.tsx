import type { ProfileQuestion } from "../../types";
import { parseTableAnswer } from "./answerStatus";

interface TableAnswerProps {
  question: ProfileQuestion;
  value: string | undefined;
  disabled: boolean;
  onChange: (value: string) => void;
}

export function TableAnswer({ question, value, disabled, onChange }: TableAnswerProps) {
  const table = parseTableAnswer(question, value);

  function updateCell(rowIndex: number, columnIndex: number, next: string) {
    const nextTable = table.map((row, currentRow) =>
      row.map((cell, currentColumn) =>
        currentRow === rowIndex && currentColumn === columnIndex ? next : cell,
      ),
    );
    onChange(JSON.stringify(nextTable));
  }

  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200">
      <div
        className="grid bg-slate-100 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
        style={{ gridTemplateColumns: `repeat(${question.columns?.length ?? 1}, minmax(0, 1fr))` }}
      >
        {question.columns?.map((column) => (
          <div className="border-r border-slate-200 px-3 py-2 last:border-r-0" key={column}>
            {column}
          </div>
        ))}
      </div>
      {table.map((row, rowIndex) => (
        <div
          className="grid border-t border-slate-200"
          key={rowIndex}
          style={{ gridTemplateColumns: `repeat(${question.columns?.length ?? 1}, minmax(0, 1fr))` }}
        >
          {row.map((cell, columnIndex) => {
            const locked = columnIndex === 0 && Boolean(question.row_labels?.[rowIndex]);
            return (
              <textarea
                aria-label={`${question.title}: строка ${rowIndex + 1}, колонка ${columnIndex + 1}`}
                className={`min-h-20 resize-y border-r border-slate-100 px-3 py-2 text-sm outline-none last:border-r-0 focus:bg-blue-50 ${
                  locked ? "bg-slate-50 font-medium text-slate-500" : "bg-white"
                }`}
                disabled={disabled || locked}
                key={`${rowIndex}-${columnIndex}`}
                onChange={(event) => updateCell(rowIndex, columnIndex, event.target.value)}
                value={cell}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}
