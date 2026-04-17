import { computed, ref, type ComputedRef } from "vue";
import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring } from "./types";
import { scoreRecipes } from "./scoring-engine";

export function useOptimizerScoring() {
  const candidates = ref<RecipeFoodData[]>([]);
  const plannedRecipes = ref<RecipeFoodData[]>([]);
  const plannedInSlot = ref<RecipeFoodData[]>([]);
  const pantryItems = ref<PantryItemScoring[]>([]);
  const weights = ref<ScoringWeights>({
    overlap: 1.0,
    pantryCoverage: 0.6,
    pantryUrgency: 0.8,
    proteinDiversity: 0.5,
    categoryBalance: 0.3,
    rating: 0.2,
    slotOverlapPenalty: 0.7,
    perishableLabelKeywords: ["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"],
    shelfStableLabelKeywords: ["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"],
  });
  const prepTimeBudget = ref<number | null>(null);

  const scoredRecipes: ComputedRef<ScoredRecipe[]> = computed(() =>
    scoreRecipes(
      candidates.value,
      plannedRecipes.value,
      pantryItems.value,
      weights.value,
      prepTimeBudget.value,
      plannedInSlot.value,
    ),
  );

  return {
    scoredRecipes,
    setCandidates: (data: RecipeFoodData[]) => { candidates.value = data; },
    setPlannedRecipes: (data: RecipeFoodData[]) => { plannedRecipes.value = data; },
    setPlannedInSlot: (data: RecipeFoodData[]) => { plannedInSlot.value = data; },
    setPantryItems: (items: PantryItemScoring[]) => { pantryItems.value = items; },
    setWeights: (w: ScoringWeights) => { weights.value = w; },
    setPrepTimeBudget: (minutes: number | null) => { prepTimeBudget.value = minutes; },
  };
}
