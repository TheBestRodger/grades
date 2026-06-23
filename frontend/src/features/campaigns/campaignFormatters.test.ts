import { describe, expect, it } from "vitest";

import { formatTimestamp } from "./campaignFormatters";

describe("campaignFormatters", () => {
  it("returns empty string for absent timestamp", () => {
    expect(formatTimestamp(null)).toBe("");
  });

  it("normalizes timestamps with and without trailing Z equally", () => {
    expect(formatTimestamp("2024-01-01T10:00:00")).toBe(formatTimestamp("2024-01-01T10:00:00Z"));
  });
});
