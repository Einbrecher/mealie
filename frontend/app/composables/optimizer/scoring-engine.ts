import type {
  PantryItemScoring,
  PantryMatchDetail,
  RecipeFoodData,
  ScoredRecipe,
  ScoringWeights,
} from "./types";

// ── Parsing & Resolution Helpers ──

export function parseTimeToMinutes(totalTime: string | null): number | null {
  if (!totalTime) return null;
  const t = totalTime.trim();

  // 1. ISO 8601: PT1H30M, PT45M, PT2H
  const iso = t.match(/^PT(?:(\d+)H)?(?:(\d+)M)?$/i);
  if (iso && (iso[1] || iso[2])) {
    return (parseInt(iso[1] || "0", 10) * 60) + parseInt(iso[2] || "0", 10);
  }

  // 2. Colon format: 1:30, 0:45
  const colon = t.match(/^(\d+):(\d{1,2})$/);
  if (colon) {
    return parseInt(colon[1], 10) * 60 + parseInt(colon[2], 10);
  }

  // 3. Text format: "1 hour 30 min", "2 hours", "45 minutes", "1.5 hours"
  let minutes = 0;
  let matched = false;

  const hourMatch = t.match(/(\d+(?:\.\d+)?)\s*hours?/i);
  if (hourMatch) {
    minutes += parseFloat(hourMatch[1]) * 60;
    matched = true;
  }

  const minMatch = t.match(/(\d+)\s*min(?:ute)?s?/i);
  if (minMatch) {
    minutes += parseInt(minMatch[1], 10);
    matched = true;
  }

  return matched ? minutes : null;
}

export function normalizedRating(rating: number | null): number {
  if (rating === null) return 0.5;
  return Math.max(0.0, Math.min(1.0, rating / 5.0));
}

export function resolveEffectivePriority(
  item: PantryItemScoring,
  perishableKeywords: string[],
  shelfStableKeywords: string[],
): "high" | "low" {
  if (item.usePriority !== "auto") return item.usePriority;

  // Auto-resolution: check expiration first
  if (item.expirationDate) {
    const daysToExpiry = Math.ceil(
      (new Date(item.expirationDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
    );
    if (daysToExpiry <= 5) return "high";
  }

  // Check label keywords
  if (item.labelName) {
    const lower = item.labelName.toLowerCase();
    if (perishableKeywords.some(kw => lower.includes(kw.toLowerCase()))) return "high";
    if (shelfStableKeywords.some(kw => lower.includes(kw.toLowerCase()))) return "low";
  }

  // Default: prefer to use up
  return "high";
}

export function expirationMultiplier(daysToExpiry: number | null): number {
  if (daysToExpiry === null) return 1.0;
  if (daysToExpiry >= 7) return 1.0;
  if (daysToExpiry >= 3) return 1.5;
  if (daysToExpiry >= 1) return 2.0;
  return 2.5; // expired or expiring today
}

// ── Individual Scoring Functions ──

// Higher score = more ingredient reuse with already-planned recipes (reduces shopping variety).
// This is intentionally ADDED to the total score — ingredient reuse is rewarded.
export function overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number {
  if (candidateFoodIds.length === 0) return 0;
  const matches = candidateFoodIds.filter(id => plannedFoodIds.has(id)).length;
  return matches / candidateFoodIds.length;
}

export function pantryCoverageScore(candidateFoodIds: string[], pantryFoodIds: Set<string>): number {
  if (candidateFoodIds.length === 0) return 0;
  const matches = candidateFoodIds.filter(id => pantryFoodIds.has(id)).length;
  return matches / candidateFoodIds.length;
}

export function pantryUrgencyScore(
  candidateFoodIds: string[],
  pantryMap: Map<string, PantryItemScoring>,
  perishableKeywords: string[],
  shelfStableKeywords: string[],
): { score: number; matches: PantryMatchDetail[] } {
  if (candidateFoodIds.length === 0) return { score: 0, matches: [] };

  let totalContribution = 0;
  const matches: PantryMatchDetail[] = [];

  for (const foodId of candidateFoodIds) {
    const item = pantryMap.get(foodId);
    if (!item || item.assumeEnough) continue;

    const priority = resolveEffectivePriority(item, perishableKeywords, shelfStableKeywords);
    const priorityWeight = priority === "high" ? 1.0 : 0.3;

    let daysToExpiry: number | null = null;
    if (item.expirationDate) {
      daysToExpiry = Math.ceil(
        (new Date(item.expirationDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
      );
    }

    totalContribution += priorityWeight * expirationMultiplier(daysToExpiry);
    matches.push({
      foodName: item.foodName,
      priority,
      daysToExpiry,
    });
  }

  return {
    score: totalContribution / candidateFoodIds.length,
    matches,
  };
}

export function proteinDiversityScore(
  candidateTagIds: string[],
  plannedProteinTags: Map<string, number>,
): number {
  if (candidateTagIds.length === 0) return 0.5;

  let overlapCount = 0;
  let totalPlannedForOverlapping = 0;
  for (const tagId of candidateTagIds) {
    const count = plannedProteinTags.get(tagId);
    if (count !== undefined && count > 0) {
      overlapCount++;
      totalPlannedForOverlapping += count;
    }
  }

  if (overlapCount === 0) return 1.0;

  // Penalize proportionally to how many times the overlapping tags appeared
  const avgCount = totalPlannedForOverlapping / overlapCount;
  return Math.max(0, 1.0 - (overlapCount / candidateTagIds.length) * Math.min(1, avgCount / 3));
}

export function categoryBalanceScore(
  candidateCategoryIds: string[],
  plannedCategoryCounts: Map<string, number>,
): number {
  if (candidateCategoryIds.length === 0) return 0.5;

  let totalScore = 0;
  for (const catId of candidateCategoryIds) {
    const count = plannedCategoryCounts.get(catId) ?? 0;
    // 1.0 if not yet planned, decreasing with count
    totalScore += 1.0 / (1.0 + count);
  }

  return totalScore / candidateCategoryIds.length;
}

export function prepTimeScore(totalTime: string | null, budgetMinutes: number | null): number {
  if (budgetMinutes === null) return 1.0;
  const parsed = parseTimeToMinutes(totalTime);
  if (parsed === null) return 1.0; // don't penalize missing data
  return parsed <= budgetMinutes ? 1.0 : 0.0;
}

// ── Slot Overlap (Complement Scoring) ──

export function slotOverlapScore(
  candidateFoodIds: string[],
  candidateTagIds: string[],
  candidateCategoryIds: string[],
  slotRecipes: RecipeFoodData[],
): number {
  if (slotRecipes.length === 0 || candidateFoodIds.length === 0) return 0;

  const slotFoodIds = new Set<string>();
  const slotTagIds = new Set<string>();
  const slotCategoryIds = new Set<string>();
  for (const recipe of slotRecipes) {
    for (const fid of recipe.foodIds) slotFoodIds.add(fid);
    for (const tid of recipe.tagIds) slotTagIds.add(tid);
    for (const cid of recipe.categoryIds) slotCategoryIds.add(cid);
  }

  const foodOverlap = candidateFoodIds.filter(id => slotFoodIds.has(id)).length / candidateFoodIds.length;
  const tagOverlap = candidateTagIds.length > 0
    ? candidateTagIds.filter(id => slotTagIds.has(id)).length / candidateTagIds.length
    : 0;
  const catOverlap = candidateCategoryIds.length > 0
    ? candidateCategoryIds.filter(id => slotCategoryIds.has(id)).length / candidateCategoryIds.length
    : 0;

  return foodOverlap * 0.5 + tagOverlap * 0.3 + catOverlap * 0.2;
}

// ── Orchestrator ──

export function scoreRecipes(
  candidates: RecipeFoodData[],
  plannedRecipes: RecipeFoodData[],
  pantryItems: PantryItemScoring[],
  weights: ScoringWeights,
  prepTimeBudget: number | null,
  plannedInSlot: RecipeFoodData[] = [],
): ScoredRecipe[] {
  // Build derived data structures
  const plannedFoodIds = new Set<string>();
  const plannedProteinTags = new Map<string, number>();
  const plannedCategoryCounts = new Map<string, number>();

  for (const recipe of plannedRecipes) {
    for (const fid of recipe.foodIds) plannedFoodIds.add(fid);
    for (const tagId of recipe.tagIds) {
      plannedProteinTags.set(tagId, (plannedProteinTags.get(tagId) ?? 0) + 1);
    }
    for (const catId of recipe.categoryIds) {
      plannedCategoryCounts.set(catId, (plannedCategoryCounts.get(catId) ?? 0) + 1);
    }
  }

  // Build pantry structures (exclude assume_enough items)
  const pantryFoodIds = new Set<string>();
  const pantryMap = new Map<string, PantryItemScoring>();
  for (const item of pantryItems) {
    if (!item.assumeEnough) {
      pantryFoodIds.add(item.foodId);
      pantryMap.set(item.foodId, item);
    }
  }

  // Score each candidate
  const scored: ScoredRecipe[] = [];
  for (const candidate of candidates) {
    if (candidate.foodIds.length === 0) continue;

    // Prep time is a hard filter
    const prepScore = prepTimeScore(candidate.totalTime, prepTimeBudget);
    if (prepScore === 0.0) continue;

    const overlap = overlapScore(candidate.foodIds, plannedFoodIds);
    const coverage = pantryCoverageScore(candidate.foodIds, pantryFoodIds);
    const urgencyResult = pantryUrgencyScore(
      candidate.foodIds,
      pantryMap,
      weights.perishableLabelKeywords,
      weights.shelfStableLabelKeywords,
    );
    const protein = proteinDiversityScore(candidate.tagIds, plannedProteinTags);
    const category = categoryBalanceScore(candidate.categoryIds, plannedCategoryCounts);
    const ratingScore = normalizedRating(candidate.rating);
    const slotSimilarity = slotOverlapScore(
      candidate.foodIds, candidate.tagIds, candidate.categoryIds, plannedInSlot,
    );

    // prepTime is NOT in the weighted sum — it acts only as a pre-filter
    const totalScore
      = weights.overlap * overlap
        + weights.pantryCoverage * coverage
        + weights.pantryUrgency * urgencyResult.score
        + weights.proteinDiversity * protein
        + weights.categoryBalance * category
        + weights.rating * ratingScore
        - weights.slotOverlapPenalty * slotSimilarity;

    scored.push({
      recipeId: candidate.recipeId,
      totalScore,
      breakdown: {
        overlap,
        pantryCoverage: coverage,
        pantryUrgency: urgencyResult.score,
        proteinDiversity: protein,
        categoryBalance: category,
        rating: ratingScore,
        prepTime: prepScore,
        slotSimilarity,
      },
      pantryMatches: urgencyResult.matches,
    });
  }

  // Sort by totalScore descending
  scored.sort((a, b) => b.totalScore - a.totalScore);

  return scored;
}
