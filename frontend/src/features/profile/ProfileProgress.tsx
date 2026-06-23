import type { EmployeeProfile } from "../../types";
import { statusLabels } from "./answerStatus";
import type { ProfileSection, SectionProgress } from "./types";

interface ProfileProgressProps {
  completed: number;
  profile: EmployeeProfile;
  progress: number;
  visibleQuestionCount: number;
}

interface ProfileSectionNavigationProps {
  activeSectionIndex: number;
  sections: ProfileSection[];
  onNavigate: (index: number) => void;
  sectionProgress: (section: ProfileSection) => SectionProgress;
}

export function ProfileProgress({
  completed,
  profile,
  progress,
  visibleQuestionCount,
}: ProfileProgressProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
          Личный профиль должности
        </p>
        <h2 className="mt-2 text-2xl font-bold text-slate-950">{profile.position_title}</h2>
        <p className="mt-1 text-sm text-slate-500">
          {profile.unit_name} / кампания «{profile.campaign_name}»
        </p>
      </div>
      <div className="min-w-52 rounded-2xl bg-blue-50 px-4 py-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600">{statusLabels[profile.workflow_status] ?? profile.workflow_status}</span>
          <strong className="text-blue-950">{progress}%</strong>
        </div>
        <p className="mt-2 text-xs font-medium text-slate-600">
          Маршрут: {profile.route_path.join(" → ")}
        </p>
        <p className="mt-1 text-xs text-slate-500">Сейчас: {profile.route_current}</p>
        <p className="mt-1 text-xs text-slate-500">{profile.route_reason}</p>
        <div className="mt-3 h-2 rounded-full bg-blue-100">
          <div className="h-2 rounded-full bg-blue-800 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Заполнено {completed} из {visibleQuestionCount} полей шаблона
        </p>
      </div>
    </div>
  );
}

export function ProfileSectionNavigation({
  activeSectionIndex,
  sections,
  onNavigate,
  sectionProgress,
}: ProfileSectionNavigationProps) {
  return (
    <nav className="space-y-2" aria-label="Разделы профиля">
      {sections.map((section, index) => {
        const status = sectionProgress(section);
        const active = index === activeSectionIndex;
        return (
          <button
            className={`flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left text-sm ${
              status.complete
                ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                : active
                  ? "border-blue-300 bg-blue-50 text-blue-950"
                  : "border-slate-100 bg-slate-50 text-slate-700"
            }`}
            key={section.title}
            onClick={() => onNavigate(index)}
            type="button"
          >
            <span
              className={`mt-0.5 h-6 w-6 shrink-0 rounded-full text-center text-xs font-semibold leading-6 ${
                status.complete ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"
              }`}
            >
              {status.complete ? "✓" : index + 1}
            </span>
            <span className="min-w-0">
              <span className="flex items-center gap-2 font-semibold">
                <span>{section.title}</span>
                {status.hasIgnoredAi && (
                  <span
                    className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800"
                    title="В разделе есть ответы, где пользователь проигнорировал рекомендации ИИ."
                  >
                    !
                  </span>
                )}
                {status.hasWithoutAi && (
                  <span
                    className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-orange-100 text-xs font-bold text-orange-800"
                    title="В разделе есть ответы, заполненные без ИИ-проверки."
                  >
                    i
                  </span>
                )}
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                {status.filled} из {status.total} полей
              </span>
            </span>
          </button>
        );
      })}
    </nav>
  );
}
