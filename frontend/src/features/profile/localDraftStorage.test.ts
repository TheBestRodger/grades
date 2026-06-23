import { afterEach, describe, expect, it } from "vitest";

import { loadLocalDraft, localDraftStorageKey, removeLocalDraft, saveLocalDraft } from "./localDraftStorage";
import type { AiUsage } from "./types";

const aiUsage: AiUsage = {
  ai_checked_questions: ["responsibilities"],
  ai_ignored_questions: [],
  ai_without_ai_questions: [],
  ai_answer_statuses: { responsibilities: "accepted" },
};

afterEach(() => {
  window.localStorage.clear();
});

describe("localDraftStorage", () => {
  it("builds profile-specific storage keys", () => {
    expect(localDraftStorageKey(12)).toBe("grades-profile-draft-v2:12");
  });

  it("returns null when draft is absent", () => {
    expect(loadLocalDraft(1)).toBeNull();
  });

  it("saves and loads local draft payload", () => {
    saveLocalDraft(1, { responsibilities: "answer" }, aiUsage);

    const draft = loadLocalDraft(1);

    expect(draft?.answers).toEqual({ responsibilities: "answer" });
    expect(draft?.ai_usage).toEqual(aiUsage);
    expect(draft?.updated_at).toEqual(expect.any(String));
  });

  it("removes saved local draft", () => {
    saveLocalDraft(1, { responsibilities: "answer" }, aiUsage);
    removeLocalDraft(1);

    expect(loadLocalDraft(1)).toBeNull();
  });
});
