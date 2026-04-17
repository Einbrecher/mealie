import type { DraftPlanEntry } from "./types";

export const DRAFT_PAYLOAD_FIELDS = ["recipeId", "entryType", "date"] as const;

export function draftEntryFieldsChanged(a: DraftPlanEntry, b: DraftPlanEntry): boolean {
  for (const field of DRAFT_PAYLOAD_FIELDS) {
    if (a[field] !== b[field]) return true;
  }
  return false;
}
