import { describe, expect, it } from "vitest";

import type { ProfileQuestion } from "../../types";
import { groupQuestionsBySection } from "./questionGroups";

function question(key: string, section: string): ProfileQuestion {
  return {
    key,
    section,
    title: key,
    question: key,
    example: "",
    input_type: "text",
    quick_answers: [],
  };
}

describe("groupQuestionsBySection", () => {
  it("groups questions by section and preserves first section order", () => {
    const groups = groupQuestionsBySection([
      question("a", "Общее"),
      question("b", "Детали"),
      question("c", "Общее"),
    ]);

    expect(groups).toEqual([
      { title: "Общее", questions: [question("a", "Общее"), question("c", "Общее")] },
      { title: "Детали", questions: [question("b", "Детали")] },
    ]);
  });

  it("returns empty list for empty input", () => {
    expect(groupQuestionsBySection([])).toEqual([]);
  });
});
