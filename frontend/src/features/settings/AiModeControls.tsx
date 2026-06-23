import { modeOptions } from "./settingsOptions";
import type { AiConfigurationMode } from "./types";

export function AiModeControls({ mode, onChangeMode }: { mode: AiConfigurationMode; onChangeMode: (mode: AiConfigurationMode) => void }) {
  return (
    <div className="mt-6 grid gap-4 xl:grid-cols-4">
      {modeOptions.map((option) => (
        <button
          className={`rounded-2xl border p-4 text-left ${
            mode === option.value
              ? "border-blue-800 bg-blue-50 text-blue-950"
              : "border-slate-200 bg-slate-50 text-slate-700 hover:border-blue-200"
          }`}
          key={option.value}
          onClick={() => onChangeMode(option.value)}
          type="button"
        >
          <p className="font-semibold">{option.label}</p>
          <p className="mt-2 text-sm">{option.note}</p>
        </button>
      ))}
    </div>
  );
}
