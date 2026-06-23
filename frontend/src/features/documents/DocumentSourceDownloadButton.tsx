export function DocumentSourceDownloadButton({
  documentId,
  onDownloadSource,
}: {
  documentId: number;
  onDownloadSource?: (documentId: number) => void;
}) {
  return (
    <button
      className="rounded-full border border-slate-200 bg-white px-3 py-1.5 font-semibold text-blue-800"
      onClick={() => onDownloadSource?.(documentId)}
      type="button"
    >
      Скачать оригинал
    </button>
  );
}
