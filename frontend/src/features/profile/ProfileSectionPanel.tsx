import type { AiAnswerCheckResult, ProfileQuestion } from "../../types";
import { isLockedPrefilledQuestion } from "./answerStatus";
import { ProfileDraftActions } from "./ProfileDraftActions";
import { ProfileField } from "./ProfileField";
import type { AnswerReviewState, ProfileSection, SectionProgress } from "./types";

interface ProfileSectionPanelProps {
  activeSection: ProfileSection | undefined;
  activeSectionIndex: number;
  activeSectionStatus: SectionProgress;
  aiAnswerSnapshots: Record<string, string>;
  aiCheckError: string | null;
  aiCheckResults: Record<string, AiAnswerCheckResult>;
  aiCheckingKey: string | null;
  aiEnabled: boolean;
  aiFallbackMessage: string | undefined;
  answers: Record<string, string>;
  canEdit: boolean;
  confirming: boolean;
  dirty: boolean;
  error: string | null;
  exporting: boolean;
  hasRevisions: boolean;
  ignoredAiQuestions: Set<string>;
  isSaving: boolean;
  isSubmitting: boolean;
  localError: string | null;
  notice: string | null;
  sectionCount: number;
  unavailableAiQuestions: Set<string>;
  onCancelSubmit: () => void;
  onCheckAnswer: (questionKey: string) => void;
  onConfirmSubmit: () => void;
  onExportTemplate: () => void;
  onGoNext: () => void;
  onNavigatePrevious: () => void;
  onSaveAndExit: () => void;
  onStartSubmit: () => void;
  onToggleIgnoreAi: (questionKey: string) => void;
  onUpdateAnswer: (questionKey: string, value: string) => void;
  questionState: (question: ProfileQuestion) => AnswerReviewState;
}

export function ProfileSectionPanel({
  activeSection,
  activeSectionIndex,
  activeSectionStatus,
  aiAnswerSnapshots,
  aiCheckError,
  aiCheckResults,
  aiCheckingKey,
  aiEnabled,
  aiFallbackMessage,
  answers,
  canEdit,
  confirming,
  dirty,
  error,
  exporting,
  hasRevisions,
  ignoredAiQuestions,
  isSaving,
  isSubmitting,
  localError,
  notice,
  sectionCount,
  unavailableAiQuestions,
  onCancelSubmit,
  onCheckAnswer,
  onConfirmSubmit,
  onExportTemplate,
  onGoNext,
  onNavigatePrevious,
  onSaveAndExit,
  onStartSubmit,
  onToggleIgnoreAi,
  onUpdateAnswer,
  questionState,
}: ProfileSectionPanelProps) {
  return (
    <div className="rounded-2xl border border-slate-100 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
            Раздел {activeSectionIndex + 1} из {sectionCount}
          </p>
          <h3 className="mt-2 text-xl font-bold text-slate-950">
            {activeSection?.title ?? "Раздел профиля"}
          </h3>
        </div>
        <span
          className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
            activeSectionStatus.hasIgnoredAi
              ? "bg-amber-100 text-amber-900"
              : activeSectionStatus.hasWithoutAi
                ? "bg-orange-100 text-orange-900"
                : activeSectionStatus.complete
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-slate-100 text-slate-600"
          }`}
          title={
            activeSectionStatus.hasIgnoredAi
              ? "В разделе есть ответы, где пользователь проигнорировал рекомендации ИИ."
              : activeSectionStatus.hasWithoutAi
                ? "В разделе есть ответы, заполненные без ИИ-проверки."
                : undefined
          }
        >
          {activeSectionStatus.hasIgnoredAi
            ? "! Есть игнор рекомендаций ИИ"
            : activeSectionStatus.hasWithoutAi
              ? "Заполнено без ИИ"
              : activeSectionStatus.complete
                ? "✓ Раздел заполнен"
                : `${activeSectionStatus.filled} из ${activeSectionStatus.total} заполнено`}
        </span>
      </div>

      {!aiEnabled && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-semibold">ИИ-ассистент недоступен</p>
          <p className="mt-1">{aiFallbackMessage}</p>
        </div>
      )}

      <div className="mt-5 space-y-4">
        {activeSection?.questions.map((item) => (
          <ProfileField
            aiCheckError={
              aiCheckingKey === item.key || unavailableAiQuestions.has(item.key) ? aiCheckError : null
            }
            aiChecking={aiCheckingKey === item.key}
            aiEnabled={aiEnabled}
            aiIgnored={ignoredAiQuestions.has(item.key)}
            aiResult={aiCheckResults[item.key]}
            aiResultCurrent={aiAnswerSnapshots[item.key] === answers[item.key]}
            aiUnavailable={unavailableAiQuestions.has(item.key)}
            canEdit={canEdit && !isLockedPrefilledQuestion(item)}
            key={item.key}
            onAiCheck={() => onCheckAnswer(item.key)}
            onChange={(value) => onUpdateAnswer(item.key, value)}
            onIgnoreAiResult={() => onToggleIgnoreAi(item.key)}
            question={item}
            reviewState={questionState(item)}
            value={answers[item.key]}
          />
        ))}
      </div>

      <p className="mt-3 text-xs text-slate-500">
        При переходе далее раздел сохраняется как черновик. Ответы можно исправить до проверки руководителем.
      </p>

      {(notice || error || localError) && (
        <p
          className={`mt-4 rounded-xl px-4 py-3 text-sm ${
            error || localError ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800"
          }`}
        >
          {error ?? localError ?? notice}
        </p>
      )}

      <ProfileDraftActions
        activeSectionIndex={activeSectionIndex}
        canEdit={canEdit}
        confirming={confirming}
        exporting={exporting}
        hasAiCheckInProgress={Boolean(aiCheckingKey)}
        hasRevisions={hasRevisions}
        isDirty={dirty}
        isSaving={isSaving}
        isSubmitting={isSubmitting}
        onCancelSubmit={onCancelSubmit}
        onConfirmSubmit={onConfirmSubmit}
        onExportTemplate={onExportTemplate}
        onGoNext={onGoNext}
        onNavigatePrevious={onNavigatePrevious}
        onSaveAndExit={onSaveAndExit}
        onStartSubmit={onStartSubmit}
        sectionCount={sectionCount}
      />
    </div>
  );
}
