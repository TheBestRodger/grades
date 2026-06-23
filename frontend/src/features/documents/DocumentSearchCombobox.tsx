import { useEffect, useId, useMemo, useRef, useState } from "react";

import type { DocumentRecord } from "../../types";
import {
  filterDocumentsForSearch,
  getDocumentQualityStatusText,
  isDocumentLinkDisabled,
} from "./documentSearch";

interface DocumentSearchComboboxProps {
  ariaLabel: string;
  documents: DocumentRecord[];
  linkedDocumentId?: number;
  isAssigning: boolean;
  onClose: (restoreFocus: boolean) => void;
  onSelect: (documentId: number | null) => void;
}

function nextEnabledIndex(documents: DocumentRecord[], startIndex: number, direction: 1 | -1) {
  if (!documents.length) return -1;

  let index = startIndex;
  for (let step = 0; step < documents.length; step += 1) {
    index = (index + direction + documents.length) % documents.length;
    if (!isDocumentLinkDisabled(documents[index])) {
      return index;
    }
  }

  return -1;
}

export function DocumentSearchCombobox({
  ariaLabel,
  documents,
  linkedDocumentId,
  isAssigning,
  onClose,
  onSelect,
}: DocumentSearchComboboxProps) {
  const inputId = useId();
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState("");
  const filteredDocuments = useMemo(() => filterDocumentsForSearch(documents, query), [documents, query]);
  const [activeIndex, setActiveIndex] = useState(() => nextEnabledIndex(filteredDocuments, -1, 1));

  useEffect(() => {
    setActiveIndex((currentIndex) => {
      if (currentIndex >= 0 && currentIndex < filteredDocuments.length) {
        const currentDocument = filteredDocuments[currentIndex];
        if (!isDocumentLinkDisabled(currentDocument)) return currentIndex;
      }

      return nextEnabledIndex(filteredDocuments, -1, 1);
    });
  }, [filteredDocuments]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        onClose(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [onClose]);

  const handleSelect = (document: DocumentRecord) => {
    if (isAssigning || isDocumentLinkDisabled(document)) return;
    onSelect(document.id);
    onClose(true);
  };

  const handleUnlink = () => {
    if (isAssigning) return;
    onSelect(null);
    onClose(true);
  };

  return (
    <div className="relative mt-1.5" ref={rootRef}>
      <div className="flex items-center gap-1 rounded-md border border-blue-300 bg-white px-2 py-1.5 focus-within:border-blue-700">
        <input
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-option-${filteredDocuments[activeIndex]?.id}` : undefined}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-expanded="true"
          aria-haspopup="listbox"
          aria-label={ariaLabel}
          autoComplete="off"
          autoFocus
          className="min-w-0 flex-1 bg-transparent text-xs text-slate-700 outline-none disabled:opacity-60"
          disabled={isAssigning}
          id={inputId}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              onClose(true);
              return;
            }

            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActiveIndex((currentIndex) => nextEnabledIndex(filteredDocuments, currentIndex, 1));
              return;
            }

            if (event.key === "ArrowUp") {
              event.preventDefault();
              setActiveIndex((currentIndex) => nextEnabledIndex(filteredDocuments, currentIndex, -1));
              return;
            }

            if (event.key === "Enter" && activeIndex >= 0) {
              event.preventDefault();
              const activeDocument = filteredDocuments[activeIndex];
              if (activeDocument) {
                handleSelect(activeDocument);
              }
            }
          }}
          placeholder="Поиск по названию, коду или версии"
          ref={inputRef}
          role="combobox"
          type="text"
          value={query}
        />
        {query && (
          <button
            aria-label="Очистить поиск"
            className="rounded px-1 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            type="button"
          >
            ×
          </button>
        )}
        <button
          aria-label="Закрыть выбор документа"
          className="rounded px-1 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          onClick={() => onClose(true)}
          type="button"
        >
          Ʌ
        </button>
      </div>

      <div className="absolute left-0 right-0 z-20 mt-1 rounded-lg border border-slate-200 bg-white p-1 text-xs shadow-xl">
        {linkedDocumentId !== undefined && (
          <button
            className="mb-1 flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-xs font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isAssigning}
            onClick={handleUnlink}
            type="button"
          >
            <span>Отвязать документ</span>
            <span aria-hidden="true">×</span>
          </button>
        )}

        <div className="max-h-72 overflow-auto" id={listboxId} role="listbox">
          {filteredDocuments.length === 0 && (
            <p className="px-2 py-3 text-center text-xs text-slate-500">Ничего не найдено</p>
          )}

          {filteredDocuments.map((document, index) => {
            const isUnavailable = isDocumentLinkDisabled(document);
            const isActive = index === activeIndex;
            const isSelected = document.id === linkedDocumentId;

            return (
              <button
                aria-disabled={isUnavailable}
                aria-selected={isSelected}
                className={`mb-1 w-full rounded-md px-2 py-2 text-left text-xs transition ${
                  isUnavailable
                    ? "cursor-not-allowed bg-slate-50 text-slate-400"
                    : isActive
                      ? "bg-blue-50 text-blue-900"
                      : "text-slate-700 hover:bg-slate-50"
                }`}
                disabled={isAssigning || isUnavailable}
                id={`${listboxId}-option-${document.id}`}
                key={document.id}
                onMouseEnter={() => {
                  if (!isUnavailable) setActiveIndex(index);
                }}
                onClick={() => handleSelect(document)}
                role="option"
                tabIndex={-1}
                type="button"
              >
                <span className="block font-semibold text-slate-900">{document.title}</span>
                <span className="mt-1 block text-[11px] text-slate-500">
                  {document.document_code} · версия {document.version || "не указана"}
                </span>
                <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  document.ocr_quality_status === "good"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}>
                  {getDocumentQualityStatusText(document)}
                </span>
                {isUnavailable && (
                  <span className="ml-1 text-[11px] font-medium text-amber-700">Нельзя привязать</span>
                )}
                {isSelected && <span className="ml-1 text-[11px] font-medium text-blue-700">Выбран</span>}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
