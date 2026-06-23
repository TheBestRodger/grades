import { describe, expect, it } from "vitest";

import type { AiAnswerCheckResult, EmployeeProfile, ProfileQuestion } from "../../types";
import {
  answerBadge,
  answerReviewState,
  assistantUsageLabel,
  fieldFrameClass,
  formatAnswer,
  isAcceptedAnswer,
  isAiCheckableQuestion,
  isHiddenQuestion,
  isLockedPrefilledQuestion,
  isQuestionFilled,
  parseTableAnswer,
  persistedAnswerState,
  removeAiUsageQuestion,
} from "./answerStatus";
import type { AiUsage } from "./types";

function question(overrides: Partial<ProfileQuestion> = {}): ProfileQuestion {
  return {
    key: "responsibilities",
    section: "Основное",
    title: "Обязанности",
    question: "Опишите обязанности",
    example: "Пример",
    input_type: "textarea",
    quick_answers: [],
    ...overrides,
  };
}

function aiResult(overrides: Partial<AiAnswerCheckResult> = {}): AiAnswerCheckResult {
  return {
    profile_id: 1,
    question_key: "responsibilities",
    question_title: "Обязанности",
    payload_policy: "full",
    available: true,
    provider: "test",
    model: "test-model",
    clarity_threshold: 70,
    clarity_percent: 90,
    status: "accepted",
    accepted: true,
    explanation: "ok",
    followup_question: "",
    raw_text: "{}",
    ...overrides,
  };
}

describe("answerStatus helpers", () => {
  it("detects hidden and locked prefilled questions", () => {
    expect(isHiddenQuestion(question({ key: "completion_date" }))).toBe(true);
    expect(isHiddenQuestion(question({ key: "responsibilities" }))).toBe(false);

    expect(isLockedPrefilledQuestion(question({ key: "position_name" }))).toBe(true);
    expect(isLockedPrefilledQuestion(question({ key: "responsibilities" }))).toBe(false);
  });

  it("parses table answers and falls back to row labels for invalid JSON", () => {
    const tableQuestion = question({
      input_type: "table",
      rows: 2,
      columns: ["Показатель", "Ответ"],
      row_labels: ["A", "B"],
    });

    expect(parseTableAnswer(tableQuestion, JSON.stringify([["wrong", "one"], ["wrong", "two"]]))).toEqual([
      ["A", "one"],
      ["B", "two"],
    ]);
    expect(parseTableAnswer(tableQuestion, "not-json")).toEqual([
      ["A", ""],
      ["B", ""],
    ]);
  });

  it("checks filled values for text, single choice and table questions", () => {
    expect(isQuestionFilled(question(), "  ")).toBe(false);
    expect(isQuestionFilled(question(), "Готово")).toBe(true);

    const choiceQuestion = question({
      input_type: "single_choice",
      options: [{ label: "Да", description: "" }],
    });
    expect(isQuestionFilled(choiceQuestion, "Да")).toBe(true);
    expect(isQuestionFilled(choiceQuestion, "Нет")).toBe(false);

    const tableQuestion = question({ input_type: "table", rows: 1, columns: ["A", "B"], row_labels: ["row"] });
    expect(isQuestionFilled(tableQuestion, JSON.stringify([["row", "value"]]))).toBe(true);
    expect(isQuestionFilled(tableQuestion, JSON.stringify([["row", ""]]))).toBe(false);
  });

  it("formats empty, invalid choice and table answers", () => {
    expect(formatAnswer(question(), "")).toBe("Еще не заполнено");

    const choiceQuestion = question({ input_type: "single_choice", options: [{ label: "Да", description: "" }] });
    expect(formatAnswer(choiceQuestion, "Нет")).toBe("Еще не заполнено");

    const tableQuestion = question({ input_type: "table", rows: 1, columns: ["A", "B"], row_labels: ["row"] });
    expect(formatAnswer(tableQuestion, JSON.stringify([["row", "value"]]))).toBe("row / value");
  });

  it("detects AI-checkable questions", () => {
    expect(isAiCheckableQuestion(question())).toBe(true);
    expect(isAiCheckableQuestion(question({ input_type: "single_choice" }))).toBe(false);
    expect(isAiCheckableQuestion(question({ ai_check_enabled: false }))).toBe(false);
  });

  it("returns answer review state for main AI states", () => {
    const base = {
      question: question(),
      value: "filled",
      aiAvailable: true,
      aiUnavailable: false,
      aiResultCurrent: true,
      aiIgnored: false,
    };

    expect(answerReviewState({ ...base, value: "", aiResult: undefined })).toBe("empty");
    expect(answerReviewState({ ...base, question: question({ key: "position_name" }), aiResult: undefined })).toBe("accepted");
    expect(answerReviewState({ ...base, aiAvailable: false, aiResult: undefined })).toBe("without_ai");
    expect(answerReviewState({ ...base, aiResult: aiResult({ accepted: true }) })).toBe("accepted");
    expect(answerReviewState({ ...base, aiResult: aiResult({ accepted: false }), aiIgnored: true })).toBe("ignored");
    expect(answerReviewState({ ...base, aiResult: aiResult({ accepted: false }) })).toBe("rejected");
    expect(answerReviewState({ ...base, aiResult: undefined })).toBe("draft");
  });

  it("maps persisted statuses and visual labels", () => {
    expect(persistedAnswerState("ignored_ai")).toBe("ignored");
    expect(persistedAnswerState("filled_without_ai")).toBe("without_ai");
    expect(persistedAnswerState("unknown")).toBeNull();

    expect(isAcceptedAnswer("accepted")).toBe(true);
    expect(isAcceptedAnswer("rejected")).toBe(false);
    expect(answerBadge("accepted").label).toContain("принят");
    expect(fieldFrameClass("rejected")).toContain("red");
  });

  it("removes AI usage for one question without mutating source object", () => {
    const usage: AiUsage = {
      ai_checked_questions: ["a", "b"],
      ai_ignored_questions: ["b"],
      ai_without_ai_questions: ["c"],
      ai_answer_statuses: { a: "accepted", b: "ignored" },
    };

    const result = removeAiUsageQuestion(usage, "b");

    expect(result?.ai_checked_questions).toEqual(["a"]);
    expect(result?.ai_ignored_questions).toEqual([]);
    expect(result?.ai_answer_statuses).toEqual({ a: "accepted" });
    expect(usage.ai_checked_questions).toEqual(["a", "b"]);
  });

  it("formats assistant usage labels for revisions", () => {
    const revision: EmployeeProfile["revisions"][number] = {
      id: 1,
      revision_no: 1,
      submitted_at: "2024-01-01T10:00:00",
      assistant_mode: "token",
      assistance_level: "full",
      assisted_sections: {
        checked_questions: ["a"],
        ignored_questions: [],
        without_ai_questions: ["b"],
      },
      answers: {},
    };

    expect(assistantUsageLabel({ ...revision, assistant_mode: "off" })).toBe("ИИ не использовался");
    expect(assistantUsageLabel(revision)).toContain("проверено ответов: 1");
  });
});
