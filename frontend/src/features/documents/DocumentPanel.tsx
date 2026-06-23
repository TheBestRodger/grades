import { DocumentCoverageCard } from "./DocumentCoverageCard";
import { DocumentRegistryTree } from "./DocumentRegistryTree";
import { WorkDocumentControls } from "./WorkDocumentControls";
import type { DocumentPanelProps } from "./types";

export function DocumentPanel({
  registry,
  tree,
  isLoading,
  error,
  viewer = "hr",
  canEdit = false,
  assigningKey = null,
  onSetLink,
  isUploading = false,
  reviewingDocumentId = null,
  onUpload,
  onReviewQuality,
  onDownloadSource,
}: DocumentPanelProps) {
  const isManagerView = viewer === "manager";

  return (
    <section className="rounded-3xl border border-indigo-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-700">
            {isManagerView ? "Руководитель: документы своей зоны" : "HR: документы"}
          </p>
          <h2 className="mt-2 text-xl font-bold text-slate-950">
            {isManagerView ? "Документальное обеспечение моей ветки" : "Документы по структуре и штатным позициям"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {isManagerView
              ? "Только доступная зона: ДИ, положения и профстандарты можно просматривать без изменения связей."
              : "Структура без сотрудников: для каждой штатной позиции проверяются ДИ, положение и профстандарт."}
          </p>
        </div>
        {registry && (
          <span className="rounded-full bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
            Документов в реестре: {registry.documents_total}
          </span>
        )}
      </div>

      {isLoading && <p className="mt-5 text-sm text-slate-500">Загружаю реестр документов...</p>}
      {error && <p className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      {registry && (
        <>
          <p className="mt-5 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {registry.note}
          </p>
          <div className="mt-5 grid gap-4 xl:grid-cols-3">
            <DocumentCoverageCard item={registry.coverage.job_instruction} />
            <DocumentCoverageCard item={registry.coverage.unit_regulation} />
            <DocumentCoverageCard item={registry.coverage.professional_standard} />
          </div>
          {canEdit && registry.scope === "work" && (
            <WorkDocumentControls
              isUploading={isUploading}
              onDownloadSource={onDownloadSource}
              onReviewQuality={onReviewQuality}
              onUpload={onUpload}
              registry={registry}
              reviewingDocumentId={reviewingDocumentId}
            />
          )}
          <DocumentRegistryTree
            assigningKey={assigningKey}
            canEdit={canEdit}
            onSetLink={onSetLink}
            registry={registry}
            tree={tree}
          />
        </>
      )}
    </section>
  );
}
