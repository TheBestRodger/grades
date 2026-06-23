import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { DocumentMatrixCell, DocumentRecord } from "../../types";
import { DocumentLinkCell } from "./DocumentLinkCell";

function makeDocument(overrides: Partial<DocumentRecord> = {}): DocumentRecord {
  return {
    id: 1,
    document_code: "DI-001",
    document_type: "job_instruction",
    document_type_label: "ДИ",
    title: "Должностная инструкция инженера",
    version: "v2",
    document_status: "active",
    ocr_quality_status: "good",
    ocr_quality_label: "Текст проверен",
    has_stored_original: true,
    has_extracted_text: true,
    content_text: "text",
    is_demo: false,
    created_at: null,
    links: [],
    ...overrides,
  };
}

const emptyCell: DocumentMatrixCell = {
  covered: false,
  documents: [],
};

describe("DocumentSearchCombobox", () => {
  it("filters and selects a document with the keyboard", async () => {
    const user = userEvent.setup();
    const onSetLink = vi.fn();

    render(
      <DocumentLinkCell
        canEdit
        cell={emptyCell}
        documentType="job_instruction"
        documents={[
          makeDocument(),
          makeDocument({
            id: 2,
            document_code: "DI-002",
            title: "Должностная инструкция аналитика",
            version: "v3",
          }),
        ]}
        isAssigning={false}
        label="ДИ"
        lineId={10}
        onSetLink={onSetLink}
        positionTitle="Инженер"
      />,
    );

    const trigger = screen.getByRole("button", { name: "Добавить ДИ для Инженер" });
    await user.click(trigger);

    const combobox = screen.getByRole("combobox", { name: "ДИ: документ для Инженер" });
    expect(combobox).toHaveFocus();

    await user.type(combobox, "аналитика");
    expect(screen.getByRole("option", { name: /Должностная инструкция аналитика/ })).toBeVisible();
    expect(screen.queryByRole("option", { name: /Должностная инструкция инженера/ })).not.toBeInTheDocument();

    await user.keyboard("{Enter}");

    expect(onSetLink).toHaveBeenCalledWith(10, "job_instruction", 2);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Добавить ДИ для Инженер" })).toHaveFocus(),
    );
  });

  it("returns focus to the trigger after Escape", async () => {
    const user = userEvent.setup();

    render(
      <DocumentLinkCell
        canEdit
        cell={emptyCell}
        documentType="job_instruction"
        documents={[makeDocument()]}
        isAssigning={false}
        label="ДИ"
        lineId={10}
        onSetLink={vi.fn()}
        positionTitle="Инженер"
      />,
    );

    const trigger = screen.getByRole("button", { name: "Добавить ДИ для Инженер" });
    await user.click(trigger);
    expect(screen.getByRole("combobox")).toHaveFocus();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Добавить ДИ для Инженер" })).toHaveFocus(),
    );
  });
});
