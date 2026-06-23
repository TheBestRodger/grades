import { useEffect, useMemo, useState } from "react";

import type { ProfileQuestion, ProfileAnswerStatus } from "../../../types";
import {
  answerReviewState,
  currentDateValue,
  isAcceptedAnswer,
  isHiddenQuestion,
  isQuestionFilled,
  persistedAnswerState,
  removeAiUsageQuestion,
} from "../answerStatus";
import { loadLocalDraft, removeLocalDraft, saveLocalDraft } from "../localDraftStorage";
import { ProfileHistory } from "../ProfileHistory";
import { ProfilePreview } from "../ProfilePreview";
import { ProfileProgress, ProfileSectionNavigation } from "../ProfileProgress";
import { ProfileSectionPanel } from "../ProfileSectionPanel";
import { ProfileStatusBanners } from "../ProfileStatusBanners";
import { groupQuestionsBySection } from "../questionGroups";
import type { AiUsage, AnswerReviewState, ProfileSection, ProfileWorkspaceProps, SaveAction } from "../types";

const emptySectionStatus = {
  filled: 0,
  total: 0,
  complete: false,
  hasIgnoredAi: false,
  hasWithoutAi: false,
  hasRejectedAi: false,
  hasDraft: false,
};

export function ProfileWorkspace({
  profile,
  ai,
  error,
  isSaving,
  isSubmitting,
  aiCheckResults,
  aiAnswerSnapshots,
  aiCheckingKey,
  aiCheckError,
  onSave,
  onSubmit,
  onExport,
  onAiCheck,
}: ProfileWorkspaceProps) {
  const [answers, setAnswers] = useState<Record<string, string>>(profile.answers);
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [paused, setPaused] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [ignoredAiQuestions, setIgnoredAiQuestions] = useState<Set<string>>(new Set());
  const [unavailableAiQuestions, setUnavailableAiQuestions] = useState<Set<string>>(new Set());
  const [localDraftAiUsage, setLocalDraftAiUsage] = useState<Partial<AiUsage> | null>(null);

  useEffect(() => {
    let nextAnswers = profile.answers;
    let hasLocalDraft = false;
    try {
      const parsed = loadLocalDraft(profile.id);
      if (parsed && profile.workflow_status !== "hr_accepted") {
        if (parsed.answers && typeof parsed.answers === "object") {
          nextAnswers = { ...profile.answers, ...parsed.answers };
          hasLocalDraft = true;
          setLocalDraftAiUsage(parsed.ai_usage ?? null);
          setIgnoredAiQuestions(new Set(parsed.ai_usage?.ai_ignored_questions ?? []));
        } else {
          setLocalDraftAiUsage(null);
          setIgnoredAiQuestions(new Set());
        }
      }
    } catch {
      hasLocalDraft = false;
      setLocalDraftAiUsage(null);
      setIgnoredAiQuestions(new Set());
    }
    if (!hasLocalDraft) {
      setLocalDraftAiUsage(null);
      setIgnoredAiQuestions(new Set());
    }
    setAnswers(nextAnswers);
    setDirty(hasLocalDraft);
    setConfirming(false);
    setPaused(false);
    setActiveSectionIndex(0);
    setUnavailableAiQuestions(new Set());
  }, [profile.id]);

  const visibleQuestions = useMemo(
    () => profile.questions.filter((question) => !isHiddenQuestion(question)),
    [profile.questions],
  );
  const sections = useMemo(() => groupQuestionsBySection(visibleQuestions), [visibleQuestions]);
  const activeSection = sections[activeSectionIndex] ?? sections[0];
  const aiEnabled = Boolean(ai?.available);
  const latestReturn = profile.review_events.find(
    (event) => event.action === "returned" || event.action === "hr_returned",
  );

  function questionState(item: ProfileQuestion): AnswerReviewState {
    const liveState = answerReviewState({
      question: item,
      value: answers[item.key],
      aiAvailable: aiEnabled,
      aiUnavailable: unavailableAiQuestions.has(item.key),
      aiResult: aiCheckResults[item.key],
      aiResultCurrent: aiAnswerSnapshots[item.key] === answers[item.key],
      aiIgnored: ignoredAiQuestions.has(item.key),
    });
    if (liveState !== "draft") return liveState;
    if ((answers[item.key] ?? "") !== (profile.answers[item.key] ?? "")) return liveState;
    const persistedStatus = persistedAnswerState(profile.draft_assisted_sections?.answer_statuses?.[item.key]);
    if (persistedStatus) return persistedStatus;
    const localStatus = persistedAnswerState(localDraftAiUsage?.ai_answer_statuses?.[item.key]);
    if (localStatus) return localStatus;
    return liveState;
  }

  const completed = useMemo(
    () => visibleQuestions.filter((item) => isAcceptedAnswer(questionState(item))).length,
    [
      answers,
      aiAnswerSnapshots,
      aiCheckResults,
      aiEnabled,
      ignoredAiQuestions,
      localDraftAiUsage,
      profile.answers,
      profile.draft_assisted_sections,
      visibleQuestions,
      unavailableAiQuestions,
    ],
  );
  const progress = visibleQuestions.length ? Math.round((completed / visibleQuestions.length) * 100) : 100;

  function sectionProgress(section: ProfileSection) {
    const states = section.questions.map((item) => questionState(item));
    const filled = states.filter(isAcceptedAnswer).length;
    return {
      filled,
      total: section.questions.length,
      complete: filled === section.questions.length,
      hasIgnoredAi: states.includes("ignored"),
      hasWithoutAi: states.includes("without_ai"),
      hasRejectedAi: states.includes("rejected"),
      hasDraft: states.includes("draft"),
    };
  }

  const activeSectionStatus = activeSection ? sectionProgress(activeSection) : emptySectionStatus;

  function updateAnswer(questionKey: string, value: string) {
    setAnswers((existing) => ({ ...existing, [questionKey]: value }));
    setDirty(true);
    setNotice(null);
    setLocalError(null);
    setLocalDraftAiUsage((existing) => removeAiUsageQuestion(existing, questionKey));
    setIgnoredAiQuestions((existing) => {
      if (!existing.has(questionKey)) return existing;
      const next = new Set(existing);
      next.delete(questionKey);
      return next;
    });
    setUnavailableAiQuestions((existing) => {
      if (!existing.has(questionKey)) return existing;
      const next = new Set(existing);
      next.delete(questionKey);
      return next;
    });
  }

  function questionnaireAnswers(): Record<string, string> {
    return Object.fromEntries(
      profile.questions.map((question) => {
        const value = isHiddenQuestion(question)
          ? answers[question.key] || currentDateValue()
          : answers[question.key] ?? "";
        if (
          question.input_type === "single_choice" &&
          value &&
          !question.options?.some((option) => option.label === value)
        ) {
          return [question.key, ""];
        }
        return [question.key, value];
      }),
    );
  }

  async function checkAnswer(questionKey: string) {
    setNotice(null);
    setLocalError(null);
    try {
      await onAiCheck(profile.id, questionKey, questionnaireAnswers());
      setDirty(true);
      setUnavailableAiQuestions((existing) => {
        if (!existing.has(questionKey)) return existing;
        const next = new Set(existing);
        next.delete(questionKey);
        return next;
      });
    } catch {
      setDirty(true);
      setUnavailableAiQuestions((existing) => new Set(existing).add(questionKey));
    }
  }

  function aiUsage(): AiUsage {
    const checked = new Set(
      Object.entries(aiAnswerSnapshots)
        .filter(([key, snapshot]) => snapshot === answers[key])
        .map(([key]) => key),
    );
    profile.draft_assisted_sections?.checked_questions.forEach((key) => {
      if ((answers[key] ?? "") === (profile.answers[key] ?? "")) checked.add(key);
    });
    localDraftAiUsage?.ai_checked_questions?.forEach((key) => {
      const question = visibleQuestions.find((item) => item.key === key);
      if (question && isQuestionFilled(question, answers[key])) {
        checked.add(key);
      }
    });
    const ignored = new Set([...checked].filter((key) => ignoredAiQuestions.has(key)));
    profile.draft_assisted_sections?.ignored_questions.forEach((key) => {
      if (checked.has(key) && (answers[key] ?? "") === (profile.answers[key] ?? "")) ignored.add(key);
    });
    localDraftAiUsage?.ai_ignored_questions?.forEach((key) => {
      if (checked.has(key)) ignored.add(key);
    });
    const answerStatuses: Record<string, ProfileAnswerStatus> = {};
    visibleQuestions.forEach((question) => {
      const state = questionState(question);
      if (state === "accepted" || state === "ignored" || state === "rejected" || state === "without_ai") {
        answerStatuses[question.key] = state;
      }
    });
    return {
      ai_checked_questions: [...checked],
      ai_ignored_questions: [...ignored],
      ai_without_ai_questions: visibleQuestions
        .filter((question) => {
          if (questionState(question) !== "without_ai") return false;
          return isQuestionFilled(question, answers[question.key]);
        })
        .map((question) => question.key),
      ai_answer_statuses: answerStatuses,
    };
  }

  useEffect(() => {
    if (!dirty) return;
    try {
      saveLocalDraft(profile.id, answers, aiUsage());
    } catch {
      // If localStorage is unavailable, the explicit save button still persists the draft.
    }
  }, [
    aiAnswerSnapshots,
    aiCheckResults,
    aiEnabled,
    answers,
    dirty,
    ignoredAiQuestions,
    localDraftAiUsage,
    profile.answers,
    profile.draft_assisted_sections,
    profile.id,
    unavailableAiQuestions,
    visibleQuestions,
  ]);

  async function save(message: string, nextAnswers = questionnaireAnswers()): Promise<boolean> {
    try {
      const result = await onSave(profile.id, nextAnswers, aiUsage());
      setAnswers(result.answers);
      setDirty(false);
      removeLocalDraft(profile.id);
      setNotice(message);
      return true;
    } catch {
      return false;
    }
  }

  async function completeSaveAction(action: SaveAction) {
    const success = await save("Раздел сохранен как черновик. Незаполненные ответы можно пропустить и вернуться позже.");
    if (!success) return;
    if (action.type === "next" && activeSectionIndex < sections.length - 1) {
      setActiveSectionIndex((value) => value + 1);
    }
    if (action.type === "navigate") {
      setActiveSectionIndex(action.index);
    }
    if (action.type === "exit") {
      setPaused(true);
    }
  }

  function requestSaveAction(action: SaveAction) {
    setNotice(null);
    setLocalError(null);
    void completeSaveAction(action);
  }

  function goNext() {
    requestSaveAction({ type: "next" });
  }

  async function navigateTo(index: number) {
    if (!dirty) {
      setActiveSectionIndex(index);
      return;
    }
    requestSaveAction({ type: "navigate", index });
  }

  async function saveAndExit() {
    requestSaveAction({ type: "exit" });
  }

  async function startSubmit() {
    const missing = visibleQuestions.find((item) => !isAcceptedAnswer(questionState(item)));
    if (missing) {
      const sectionIndex = sections.findIndex((section) =>
        section.questions.some((item) => item.key === missing.key),
      );
      setActiveSectionIndex(Math.max(sectionIndex, 0));
      const state = questionState(missing);
      const message =
        state === "rejected"
          ? "Перед сдачей исправьте ответы, которые не соответствуют критериям ИИ, либо явно проигнорируйте рекомендацию ИИ."
          : state === "draft"
            ? "Перед сдачей проверьте заполненные ответы через ИИ. Если ИИ недоступен, ответы будут приняты без ИИ."
            : "Для сдачи нужно заполнить все обязательные поля шаблона профиля должности.";
      setNotice(message);
      return;
    }
    setConfirming(true);
    setNotice(null);
  }

  async function confirmSubmit() {
    try {
      const result = await onSubmit(profile.id, questionnaireAnswers(), aiUsage());
      setAnswers(result.answers);
      setDirty(false);
      removeLocalDraft(profile.id);
      setConfirming(false);
      setNotice(`Версия ${result.revisions[0].revision_no} отправлена на проверку.`);
    } catch {
      setConfirming(false);
    }
  }

  async function exportTemplate() {
    try {
      setExporting(true);
      await onExport(profile.id);
      setLocalError(null);
      setNotice("Excel-шаблон с текущей версией профиля подготовлен.");
    } catch {
      setNotice(null);
      setLocalError("Не удалось подготовить Excel-шаблон.");
    } finally {
      setExporting(false);
    }
  }

  function toggleIgnoreAiResult(questionKey: string) {
    setDirty(true);
    setNotice(null);
    setIgnoredAiQuestions((existing) => {
      const next = new Set(existing);
      if (next.has(questionKey)) {
        next.delete(questionKey);
      } else {
        next.add(questionKey);
      }
      return next;
    });
  }

  return (
    <section className="rounded-3xl border border-blue-100 bg-white p-5 shadow-sm">
      <ProfileProgress
        completed={completed}
        profile={profile}
        progress={progress}
        visibleQuestionCount={visibleQuestions.length}
      />

      <ProfileStatusBanners latestReturn={latestReturn} profile={profile} />

      {paused ? (
        <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50 p-5 text-sm text-emerald-900">
          <p className="font-semibold">Черновик сохранен</p>
          <p className="mt-1">Прогресс зафиксирован. Анкету можно продолжить с сохраненными ответами.</p>
          <button
            className="mt-4 rounded-xl bg-blue-900 px-5 py-2.5 font-semibold text-white"
            onClick={() => setPaused(false)}
            type="button"
          >
            Продолжить заполнение
          </button>
        </div>
      ) : (
        <>
          <div className="mt-5 grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
            <ProfileSectionNavigation
              activeSectionIndex={activeSectionIndex}
              onNavigate={navigateTo}
              sectionProgress={sectionProgress}
              sections={sections}
            />

            <div className="min-w-0">
              <ProfileSectionPanel
                activeSection={activeSection}
                activeSectionIndex={activeSectionIndex}
                activeSectionStatus={activeSectionStatus}
                aiAnswerSnapshots={aiAnswerSnapshots}
                aiCheckError={aiCheckError}
                aiCheckResults={aiCheckResults}
                aiCheckingKey={aiCheckingKey}
                aiEnabled={aiEnabled}
                aiFallbackMessage={ai?.fallback_message}
                answers={answers}
                canEdit={profile.can_edit}
                confirming={confirming}
                dirty={dirty}
                error={error}
                exporting={exporting}
                hasRevisions={profile.revisions.length > 0}
                ignoredAiQuestions={ignoredAiQuestions}
                isSaving={isSaving}
                isSubmitting={isSubmitting}
                localError={localError}
                notice={notice}
                onCancelSubmit={() => setConfirming(false)}
                onCheckAnswer={checkAnswer}
                onConfirmSubmit={confirmSubmit}
                onExportTemplate={exportTemplate}
                onGoNext={goNext}
                onNavigatePrevious={() => navigateTo(activeSectionIndex - 1)}
                onSaveAndExit={saveAndExit}
                onStartSubmit={startSubmit}
                onToggleIgnoreAi={toggleIgnoreAiResult}
                onUpdateAnswer={updateAnswer}
                questionState={questionState}
                sectionCount={sections.length}
                unavailableAiQuestions={unavailableAiQuestions}
              />
            </div>

            <ProfilePreview answers={answers} questions={activeSection?.questions} />
          </div>

          <ProfileHistory profile={profile} />
        </>
      )}
    </section>
  );
}
