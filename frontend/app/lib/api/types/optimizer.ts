/* tslint:disable */

/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

import type { IngredientFood, IngredientUnit } from "./recipe";

export interface PantryItemCreate {
  foodId?: string | null;
  name?: string | null;
  isStaple?: boolean;
  assumeEnough?: boolean;
  quantity?: number | null;
  unitId?: string | null;
  expirationDate?: string | null;
  usePriority?: "auto" | "high" | "low";
}

export interface PantryItemUpdate extends PantryItemCreate {
  id: string;
}

export interface PantryItemOut extends PantryItemCreate {
  id: string;
  groupId: string;
  householdId: string;
  food?: IngredientFood | null;
  unit?: IngredientUnit | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface PantryItemPagination {
  page?: number;
  perPage?: number;
  total?: number;
  totalPages?: number;
  items: PantryItemOut[];
  next?: string | null;
  previous?: string | null;
}

export interface PantryDeficitItem {
  foodId?: string | null;
  foodName: string;
  recipeQuantity: number;
  recipeUnit?: IngredientUnit | null;
  pantryQuantity?: number | null;
  pantryUnit?: IngredientUnit | null;
  deficit: number;
  assumeEnough?: boolean;
  covered: boolean;
  conversionFailed?: boolean;
}

export interface PantryDeficitReport {
  items: PantryDeficitItem[];
  uncoveredItems: PantryDeficitItem[];
  totalItems: number;
  coveredCount: number;
  coveragePercent: number;
}

export interface PantryDeficitRequest {
  recipeIds: string[];
  excludeExpired?: boolean;
}

export interface PantryMealPlanDeficitRequest {
  startDate: string;
  endDate: string;
  excludeExpired?: boolean;
}

export interface PantryImportResult {
  importedCount: number;
  skippedCount: number;
}

export interface PantryDeductRequest {
  recipeId: string;
}

export interface ShoppingItemDeductRequest {
  shoppingListItemIds: string[];
}

export interface PantryQuickAddItem {
  foodId: string;
  quantity?: number | null;
  unitId?: string | null;
}

export interface PantryQuickAddRequest {
  items: PantryQuickAddItem[];
}

export interface OnHandCountResponse {
  count: number;
}

// --- Optimizer Config ---

export interface OptimizerConfigUpdate {
  overlapWeight: number;
  pantryUtilizationWeight: number;
  pantryUrgencyWeight: number;
  proteinDiversityWeight: number;
  categoryBalanceWeight: number;
  ratingWeight: number;
  slotOverlapPenaltyWeight: number;
  prepTimeBudgetMinutes: number | null;
  perishableLabelKeywords: string[];
  shelfStableLabelKeywords: string[];
  expirationWarningDays: number;
  onboardingCompleted: boolean;
}

export interface OptimizerConfigOut extends OptimizerConfigUpdate {
  id: string;
  groupId: string;
  householdId: string;
}

// --- Recipe-Foods Projection ---

export interface RecipeFoodProjection {
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

export interface RecipeFoodProjectionResponse {
  items: RecipeFoodProjection[];
  unlinkedRecipeCount: number;
}
