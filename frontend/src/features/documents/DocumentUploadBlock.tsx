import { useState, type FormEvent } from "react";

import type { DocumentPanelProps, DocumentType } from "./types";

export function DocumentUploadBlock({
  isUploading,
  onUpload,
}: {
  isUploading: boolean;
  onUpload?: DocumentPanelProps["onUpload"];
}) {
  const [documentCode, setDocumentCode] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType>("job_instruction");
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("1.0");
  const [file, setFile] = useState<File | null>(null);

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !documentCode.trim() || !title.trim() || !version.trim()) return;
    onUpload?.(file, documentCode.trim(), documentType, title.trim(), version.trim());
  }

  return (
    <form className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4" onSubmit={submitUpload}>
      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-blue-700">Новый оригинал</p>
      <h3 className="mt-1 text-base font-bold text-slate-950">Загрузить документ</h3>
      <p className="mt-1 text-xs text-slate-600">
        TXT, MD и DOCX получают первоначальный текст локально. Для PDF внесите распознанный текст при проверке.
      </p>
      <div className="mt-4 grid gap-3">
        <input
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setDocumentCode(event.target.value)}
          placeholder="Код документа"
          required
          value={documentCode}
        />
        <select
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setDocumentType(event.target.value as DocumentType)}
          value={documentType}
        >
          <option value="job_instruction">Должностная инструкция</option>
          <option value="unit_regulation">Положение подразделения</option>
          <option value="professional_standard">Профстандарт</option>
        </select>
        <input
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Название"
          required
          value={title}
        />
        <input
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setVersion(event.target.value)}
          placeholder="Версия"
          required
          value={version}
        />
        <input
          accept=".txt,.md,.docx,.pdf"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          required
          type="file"
        />
        <button
          className="rounded-lg bg-blue-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
          disabled={isUploading}
          type="submit"
        >
          {isUploading ? "Загружаю..." : "Загрузить оригинал"}
        </button>
      </div>
    </form>
  );
}
