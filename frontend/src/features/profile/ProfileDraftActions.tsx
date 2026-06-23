interface ProfileDraftActionsProps {
  activeSectionIndex: number;
  confirming: boolean;
  exporting: boolean;
  hasAiCheckInProgress: boolean;
  hasRevisions: boolean;
  isSaving: boolean;
  isSubmitting: boolean;
  isDirty: boolean;
  canEdit: boolean;
  sectionCount: number;
  onCancelSubmit: () => void;
  onConfirmSubmit: () => void;
  onExportTemplate: () => void;
  onGoNext: () => void;
  onNavigatePrevious: () => void;
  onSaveAndExit: () => void;
  onStartSubmit: () => void;
}

export function ProfileDraftActions({
  activeSectionIndex,
  confirming,
  exporting,
  hasAiCheckInProgress,
  hasRevisions,
  isSaving,
  isSubmitting,
  isDirty,
  canEdit,
  sectionCount,
  onCancelSubmit,
  onConfirmSubmit,
  onExportTemplate,
  onGoNext,
  onNavigatePrevious,
  onSaveAndExit,
  onStartSubmit,
}: ProfileDraftActionsProps) {
  return (
    <>
      {confirming && (
        <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
          <p className="font-semibold">Готовы отправить профиль на проверку?</p>
          <p className="mt-1">
            Будет создана новая неизменяемая версия. Если ИИ-проверка использовалась, это будет видно руководителю.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              className="rounded-lg bg-blue-900 px-4 py-2 font-semibold text-white"
              disabled={isSubmitting}
              onClick={onConfirmSubmit}
              type="button"
            >
              {isSubmitting ? "Отправляю..." : "Подтвердить отправку"}
            </button>
            <button className="rounded-lg border border-blue-200 px-4 py-2" onClick={onCancelSubmit} type="button">
              Вернуться к ответам
            </button>
          </div>
        </div>
      )}

      {!confirming && canEdit && (
        <div className="mt-5 flex flex-wrap justify-between gap-3">
          <div className="flex gap-2">
            <button
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm disabled:opacity-40"
              disabled={activeSectionIndex === 0}
              onClick={onNavigatePrevious}
              type="button"
            >
              Назад
            </button>
            <button
              className="rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-medium text-blue-900 disabled:opacity-50"
              disabled={isSaving || !isDirty}
              onClick={onSaveAndExit}
              type="button"
            >
              {isSaving ? "Сохраняю..." : "Сохранить и выйти"}
            </button>
          </div>
          {activeSectionIndex < sectionCount - 1 ? (
            <button
              className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              disabled={isSaving || hasAiCheckInProgress}
              onClick={onGoNext}
              type="button"
            >
              {hasAiCheckInProgress ? "Жду ответ LLM..." : isSaving ? "Сохраняю..." : "Сохранить раздел и далее"}
            </button>
          ) : (
            <button
              className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white"
              disabled={hasAiCheckInProgress}
              onClick={onStartSubmit}
              type="button"
            >
              {hasAiCheckInProgress ? "Жду ответ LLM..." : "Отправить на проверку"}
            </button>
          )}
        </div>
      )}

      {hasRevisions && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <button
            className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-900 disabled:opacity-50"
            disabled={exporting}
            onClick={onExportTemplate}
            type="button"
          >
            {exporting ? "Готовлю Excel..." : "Скачать Excel-шаблон"}
          </button>
          <p className="mt-2 text-xs text-slate-500">
            Заполняется исходная форма профиля должности, последняя отправленная версия.
          </p>
        </div>
      )}
    </>
  );
}
