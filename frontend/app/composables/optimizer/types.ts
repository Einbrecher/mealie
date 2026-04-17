import type { PlanEntryType } from "~/lib/api/types/meal-plan";

export interface ScoringWeights {
  overlap: number;
  pantryCoverage: number;
  pantryUrgency: number;
  proteinDiversity: number;
  categoryBalance: number;
  rating: number;
  slotOverlapPenalty: number;
  // Note: no prepTime weight. Prep time is a hard filter (exclude/include),
  // not a continuous score, so it doesn't participate in the weighted sum.
  perishableLabelKeywords: string[];
  shelfStableLabelKeywords: string[];
}

export interface RecipeFoodData {
  recipeId: string;
  slug: string;
  name: string;
  foodIds: string[];
  categoryIds: string[];
  tagIds: string[];
  rating: number | null;
  totalTime: string | null;
  lastMade: string | null;
}

export interface PantryMatchDetail {
  foodName: string;
  priority: "high" | "low";
  daysToExpiry: number | null;
}

export interface ScoredRecipe {
  recipeId: string;
  totalScore: number;
  breakdown: Record<string, number>;
  pantryMatches: PantryMatchDetail[];
}

export interface PantryItemScoring {
  foodId: string;
  foodName: string;
  labelName: string | null;
  usePriority: "auto" | "high" | "low";
  assumeEnough: boolean;
  expirationDate: string | null;
}

export interface DraftPlanEntry {
  localId: string;
  date: string;
  entryType: PlanEntryType;
  order: number;
  recipeId: string | null;
  recipeName: string | null;
  recipeSlug: string | null;
  existingEntryId: number | null;
  groupId: string | null;
  userId: string | null;
  householdId: string | null;
}
