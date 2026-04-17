import { describe, it, expect } from "vitest";
import { draftEntryFieldsChanged, DRAFT_PAYLOAD_FIELDS } from "./planner-diff";
import type { DraftPlanEntry } from "./types";

function makeEntry(overrides: Partial<DraftPlanEntry> = {}): DraftPlanEntry {
  return {
    localId: "local-1",
    date: "2026-04-17",
    entryType: "dinner",
    order: 0,
    recipeId: "recipe-1",
    recipeName: "Chili",
    recipeSlug: "chili",
    existingEntryId: null,
    groupId: "group-1",
    userId: "user-1",
    householdId: "household-1",
    ...overrides,
  };
}

describe("draftEntryFieldsChanged", () => {
  it("returns false for identical entries", () => {
    const a = makeEntry();
    const b = makeEntry();
    expect(draftEntryFieldsChanged(a, b)).toBe(false);
  });

  it("returns true when recipeId differs (including null to value)", () => {
    expect(
      draftEntryFieldsChanged(makeEntry({ recipeId: null }), makeEntry({ recipeId: "abc" })),
    ).toBe(true);
    expect(
      draftEntryFieldsChanged(makeEntry({ recipeId: "r1" }), makeEntry({ recipeId: "r2" })),
    ).toBe(true);
  });

  it("returns true when entryType differs", () => {
    expect(
      draftEntryFieldsChanged(makeEntry({ entryType: "breakfast" }), makeEntry({ entryType: "dinner" })),
    ).toBe(true);
  });

  it("returns true when date differs", () => {
    expect(
      draftEntryFieldsChanged(makeEntry({ date: "2026-04-17" }), makeEntry({ date: "2026-04-18" })),
    ).toBe(true);
  });

  it("returns false when only existingEntryId differs (identity, not payload)", () => {
    expect(
      draftEntryFieldsChanged(makeEntry({ existingEntryId: null }), makeEntry({ existingEntryId: 42 })),
    ).toBe(false);
  });

  it("returns false when only localId, order, recipeName, or recipeSlug differs (display/bookkeeping)", () => {
    expect(
      draftEntryFieldsChanged(makeEntry({ localId: "x" }), makeEntry({ localId: "y" })),
    ).toBe(false);
    expect(
      draftEntryFieldsChanged(makeEntry({ order: 0 }), makeEntry({ order: 3 })),
    ).toBe(false);
    expect(
      draftEntryFieldsChanged(makeEntry({ recipeName: "A" }), makeEntry({ recipeName: "B" })),
    ).toBe(false);
    expect(
      draftEntryFieldsChanged(makeEntry({ recipeSlug: "a" }), makeEntry({ recipeSlug: "b" })),
    ).toBe(false);
  });
});

describe("DRAFT_PAYLOAD_FIELDS", () => {
  it("exports the three payload-only field names", () => {
    expect(DRAFT_PAYLOAD_FIELDS).toEqual(["recipeId", "entryType", "date"]);
  });
});
