import { describe, expect, it } from "vitest";

import { queryKeys } from "./queryKeys";

describe("queryKeys", () => {
  it("returns stable top-level keys", () => {
    expect(queryKeys.health()).toEqual(["health"]);
    expect(queryKeys.demoUsers()).toEqual(["demo-users"]);
    expect(queryKeys.authMe("token")).toEqual(["me", "token"]);
    expect(queryKeys.authMe(null)).toEqual(["me", null]);
  });

  it("includes scope only for scoped keys when scope is passed", () => {
    expect(queryKeys.campaigns(1)).toEqual(["campaigns", 1]);
    expect(queryKeys.campaigns(1, "work")).toEqual(["campaigns", 1, "work"]);
    expect(queryKeys.audit(null, "demo")).toEqual(["audit", null, "demo"]);
    expect(queryKeys.hrDocuments(2, "work")).toEqual(["hr-documents", 2, "work"]);
  });

  it("builds manager and profile keys", () => {
    expect(queryKeys.myProfiles(5)).toEqual(["my-profiles", 5]);
    expect(queryKeys.managerReviews(5)).toEqual(["manager-reviews", 5]);
    expect(queryKeys.managerDocuments(5)).toEqual(["manager-documents", 5]);
  });
});
