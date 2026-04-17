import { describe, it, expect } from "vitest";
import {
  parseTimeToMinutes,
  overlapScore,
  pantryCoverageScore,
  pantryUrgencyScore,
  proteinDiversityScore,
  categoryBalanceScore,
  normalizedRating,
  prepTimeScore,
  resolveEffectivePriority,
  expirationMultiplier,
  scoreRecipes,
} from "./scoring-engine";
import type { PantryItemScoring, RecipeFoodData, ScoringWeights } from "./types";

// ── Test Helpers ──

function makePantryItem(overrides: Partial<PantryItemScoring> = {}): PantryItemScoring {
  return {
    foodId: "food-1",
    foodName: "Test Food",
    labelName: null,
    usePriority: "auto",
    assumeEnough: false,
    expirationDate: null,
    ...overrides,
  };
}

function makeRecipe(overrides: Partial<RecipeFoodData> = {}): RecipeFoodData {
  return {
    recipeId: "recipe-1",
    slug: "test-recipe",
    name: "Test Recipe",
    foodIds: ["food-1", "food-2"],
    categoryIds: ["cat-1"],
    tagIds: ["tag-1"],
    rating: 4,
    totalTime: "30 Minutes",
    lastMade: null,
    ...overrides,
  };
}

function defaultWeights(): ScoringWeights {
  return {
    overlap: 1.0,
    pantryCoverage: 0.6,
    pantryUrgency: 0.8,
    proteinDiversity: 0.5,
    categoryBalance: 0.3,
    rating: 0.2,
    slotOverlapPenalty: 0.7,
    perishableLabelKeywords: ["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"],
    shelfStableLabelKeywords: ["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"],
  };
}

// ── parseTimeToMinutes ──

describe("parseTimeToMinutes", () => {
  it("parses '30 Minutes'", () => {
    expect(parseTimeToMinutes("30 Minutes")).toBe(30);
  });

  it("parses '1 Hour'", () => {
    expect(parseTimeToMinutes("1 Hour")).toBe(60);
  });

  it("parses '1 Hour 15 Minutes'", () => {
    expect(parseTimeToMinutes("1 Hour 15 Minutes")).toBe(75);
  });

  it("parses '1.5 Hours'", () => {
    expect(parseTimeToMinutes("1.5 Hours")).toBe(90);
  });

  it("returns null for null input", () => {
    expect(parseTimeToMinutes(null)).toBeNull();
  });

  it("returns null for unparseable string", () => {
    expect(parseTimeToMinutes("garbage")).toBeNull();
  });

  // ISO 8601 formats
  it("parses ISO 8601 'PT1H30M'", () => {
    expect(parseTimeToMinutes("PT1H30M")).toBe(90);
  });

  it("parses ISO 8601 'PT45M'", () => {
    expect(parseTimeToMinutes("PT45M")).toBe(45);
  });

  it("parses ISO 8601 'PT2H'", () => {
    expect(parseTimeToMinutes("PT2H")).toBe(120);
  });

  // Colon formats
  it("parses colon format '1:30'", () => {
    expect(parseTimeToMinutes("1:30")).toBe(90);
  });

  it("parses colon format '0:45'", () => {
    expect(parseTimeToMinutes("0:45")).toBe(45);
  });

  // Variant text
  it("parses '90 minutes'", () => {
    expect(parseTimeToMinutes("90 minutes")).toBe(90);
  });
});

// ── normalizedRating ──

describe("normalizedRating", () => {
  it("returns 1.0 for rating 5", () => {
    expect(normalizedRating(5)).toBe(1.0);
  });

  it("returns 0.5 for null rating", () => {
    expect(normalizedRating(null)).toBe(0.5);
  });

  it("returns 0.0 for rating 0", () => {
    expect(normalizedRating(0)).toBe(0.0);
  });

  it("returns 0.6 for rating 3", () => {
    expect(normalizedRating(3)).toBeCloseTo(0.6);
  });

  it("clamps to 1.0 for rating > 5", () => {
    expect(normalizedRating(10)).toBe(1.0);
  });
});

// ── resolveEffectivePriority ──

describe("resolveEffectivePriority", () => {
  const perishable = ["vegetable", "fruit", "dairy"];
  const shelfStable = ["spice", "grain", "pasta"];

  it("returns explicit priority when not auto", () => {
    const item = makePantryItem({ usePriority: "high" });
    expect(resolveEffectivePriority(item, perishable, shelfStable)).toBe("high");
  });

  it("returns high for expiring soon (auto)", () => {
    const soon = new Date();
    soon.setDate(soon.getDate() + 3);
    const item = makePantryItem({ expirationDate: soon.toISOString() });
    expect(resolveEffectivePriority(item, perishable, shelfStable)).toBe("high");
  });

  it("returns high for perishable label (auto)", () => {
    const item = makePantryItem({ labelName: "Fresh Vegetables" });
    expect(resolveEffectivePriority(item, perishable, shelfStable)).toBe("high");
  });

  it("returns low for shelf-stable label (auto)", () => {
    const item = makePantryItem({ labelName: "Dried Pasta" });
    expect(resolveEffectivePriority(item, perishable, shelfStable)).toBe("low");
  });

  it("returns high for unknown label (auto, safe default)", () => {
    const item = makePantryItem({ labelName: "Unknown Category" });
    expect(resolveEffectivePriority(item, perishable, shelfStable)).toBe("high");
  });

  it("matches custom keyword lists", () => {
    const item = makePantryItem({ labelName: "Frozen Pizza" });
    expect(resolveEffectivePriority(item, ["frozen"], [])).toBe("high");
    expect(resolveEffectivePriority(item, [], ["frozen"])).toBe("low");
  });
});

// ── expirationMultiplier ──

describe("expirationMultiplier", () => {
  it("returns 1.0 for null", () => {
    expect(expirationMultiplier(null)).toBe(1.0);
  });

  it("returns 1.0 for 10 days", () => {
    expect(expirationMultiplier(10)).toBe(1.0);
  });

  it("returns 1.5 for 5 days", () => {
    expect(expirationMultiplier(5)).toBe(1.5);
  });

  it("returns 2.0 for 2 days", () => {
    expect(expirationMultiplier(2)).toBe(2.0);
  });

  it("returns 2.5 for 0 (expired today)", () => {
    expect(expirationMultiplier(0)).toBe(2.5);
  });

  it("returns 2.5 for negative (past expired)", () => {
    expect(expirationMultiplier(-1)).toBe(2.5);
  });
});

// ── overlapScore ──

describe("overlapScore", () => {
  it("returns 0 for no overlap", () => {
    expect(overlapScore(["a", "b"], new Set(["c", "d"]))).toBe(0);
  });

  it("returns 1.0 for full overlap", () => {
    expect(overlapScore(["a", "b"], new Set(["a", "b", "c"]))).toBe(1.0);
  });

  it("returns fraction for partial overlap", () => {
    expect(overlapScore(["a", "b"], new Set(["a"]))).toBe(0.5);
  });

  it("returns 0 for empty candidate", () => {
    expect(overlapScore([], new Set(["a"]))).toBe(0);
  });
});

// ── pantryCoverageScore ──

describe("pantryCoverageScore", () => {
  it("returns 1.0 when all in pantry", () => {
    expect(pantryCoverageScore(["a", "b"], new Set(["a", "b"]))).toBe(1.0);
  });

  it("returns 0 when none in pantry", () => {
    expect(pantryCoverageScore(["a", "b"], new Set(["c"]))).toBe(0);
  });

  it("returns fraction for partial pantry coverage", () => {
    expect(pantryCoverageScore(["a", "b", "c"], new Set(["a"]))).toBeCloseTo(1 / 3);
  });
});

// ── pantryUrgencyScore ──

describe("pantryUrgencyScore", () => {
  const perishable = ["vegetable"];
  const shelfStable = ["spice"];

  it("returns high score for high-priority expiring item", () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const pantryMap = new Map([
      ["food-1", makePantryItem({ foodId: "food-1", expirationDate: tomorrow.toISOString(), labelName: "Vegetable" })],
    ]);
    const result = pantryUrgencyScore(["food-1"], pantryMap, perishable, shelfStable);
    expect(result.score).toBeGreaterThan(0);
    expect(result.matches).toHaveLength(1);
    expect(result.matches[0].priority).toBe("high");
  });

  it("returns lower score for low-priority item", () => {
    const pantryMap = new Map([
      ["food-1", makePantryItem({ foodId: "food-1", usePriority: "low" })],
    ]);
    const result = pantryUrgencyScore(["food-1"], pantryMap, perishable, shelfStable);
    // low priority weight = 0.3, no expiration multiplier = 1.0 -> 0.3 / 1 = 0.3
    expect(result.score).toBeCloseTo(0.3);
  });

  it("skips assume_enough items", () => {
    const pantryMap = new Map([
      ["food-1", makePantryItem({ foodId: "food-1", assumeEnough: true })],
    ]);
    const result = pantryUrgencyScore(["food-1"], pantryMap, perishable, shelfStable);
    expect(result.score).toBe(0);
    expect(result.matches).toHaveLength(0);
  });

  it("returns 0 for empty input", () => {
    const result = pantryUrgencyScore([], new Map(), perishable, shelfStable);
    expect(result.score).toBe(0);
  });
});

// ── proteinDiversityScore ──

describe("proteinDiversityScore", () => {
  it("returns 1.0 for unique tags", () => {
    expect(proteinDiversityScore(["tag-1"], new Map())).toBe(1.0);
  });

  it("returns lower score for duplicate tags", () => {
    const planned = new Map([["tag-1", 3]]);
    const score = proteinDiversityScore(["tag-1"], planned);
    expect(score).toBeLessThan(1.0);
  });

  it("returns 0.5 for no tags", () => {
    expect(proteinDiversityScore([], new Map())).toBe(0.5);
  });
});

// ── categoryBalanceScore ──

describe("categoryBalanceScore", () => {
  it("returns 1.0 for new category", () => {
    expect(categoryBalanceScore(["cat-new"], new Map())).toBe(1.0);
  });

  it("returns lower for overrepresented category", () => {
    const planned = new Map([["cat-1", 5]]);
    const score = categoryBalanceScore(["cat-1"], planned);
    expect(score).toBeLessThan(1.0);
    // 1 / (1 + 5) = ~0.167
    expect(score).toBeCloseTo(1 / 6);
  });

  it("returns 0.5 for no categories", () => {
    expect(categoryBalanceScore([], new Map())).toBe(0.5);
  });
});

// ── prepTimeScore ──

describe("prepTimeScore", () => {
  it("returns 1.0 within budget", () => {
    expect(prepTimeScore("30 Minutes", 60)).toBe(1.0);
  });

  it("returns 0.0 exceeding budget", () => {
    expect(prepTimeScore("90 Minutes", 60)).toBe(0.0);
  });

  it("returns 1.0 with no budget", () => {
    expect(prepTimeScore("30 Minutes", null)).toBe(1.0);
  });

  it("returns 1.0 for unparseable time", () => {
    expect(prepTimeScore("some time", 60)).toBe(1.0);
  });

  it("returns 1.0 for null time", () => {
    expect(prepTimeScore(null, 60)).toBe(1.0);
  });
});

// ── scoreRecipes integration ──

describe("scoreRecipes", () => {
  it("excludes zero-food recipes", () => {
    const candidates = [makeRecipe({ foodIds: [] })];
    const result = scoreRecipes(candidates, [], [], defaultWeights(), null);
    expect(result).toHaveLength(0);
  });

  it("cold start: zero planned, ranks by pantry+rating", () => {
    const candidates = [
      makeRecipe({ recipeId: "r1", foodIds: ["a"], rating: 5 }),
      makeRecipe({ recipeId: "r2", foodIds: ["b"], rating: 1 }),
    ];
    const result = scoreRecipes(candidates, [], [], defaultWeights(), null);
    expect(result).toHaveLength(2);
    // All get overlapScore=0, r1 should rank higher (better rating)
    expect(result[0].recipeId).toBe("r1");
    expect(result[0].breakdown.overlap).toBe(0);
  });

  it("100% overlap produces high overlap score", () => {
    const planned = [makeRecipe({ foodIds: ["a", "b"] })];
    const candidates = [makeRecipe({ recipeId: "c1", foodIds: ["a", "b"] })];
    const result = scoreRecipes(candidates, planned, [], defaultWeights(), null);
    expect(result[0].breakdown.overlap).toBe(1.0);
  });

  it("all assume_enough pantry -> coverage=0, urgency=0", () => {
    const pantry = [makePantryItem({ foodId: "a", assumeEnough: true })];
    const candidates = [makeRecipe({ foodIds: ["a"] })];
    const result = scoreRecipes(candidates, [], pantry, defaultWeights(), null);
    expect(result[0].breakdown.pantryCoverage).toBe(0);
    expect(result[0].breakdown.pantryUrgency).toBe(0);
  });

  it("filters out recipes exceeding prep time budget", () => {
    const candidates = [
      makeRecipe({ recipeId: "fast", totalTime: "20 Minutes" }),
      makeRecipe({ recipeId: "slow", totalTime: "2 Hours" }),
    ];
    const result = scoreRecipes(candidates, [], [], defaultWeights(), 30);
    expect(result).toHaveLength(1);
    expect(result[0].recipeId).toBe("fast");
  });

  it("prepTime is NOT in the weighted sum", () => {
    const candidates = [makeRecipe({ totalTime: "20 Minutes" })];
    const result = scoreRecipes(candidates, [], [], defaultWeights(), 30);
    // breakdown includes prepTime for reference, but totalScore doesn't include it
    expect(result[0].breakdown.prepTime).toBe(1.0);
    // Verify totalScore = sum of (weight * score) for 6 factors, NOT 7
    const w = defaultWeights();
    const b = result[0].breakdown;
    const expected =
      w.overlap * b.overlap +
      w.pantryCoverage * b.pantryCoverage +
      w.pantryUrgency * b.pantryUrgency +
      w.proteinDiversity * b.proteinDiversity +
      w.categoryBalance * b.categoryBalance +
      w.rating * b.rating;
    expect(result[0].totalScore).toBeCloseTo(expected);
  });

  it("returns sorted by totalScore descending", () => {
    const pantry = [
      makePantryItem({ foodId: "a", usePriority: "high" }),
      makePantryItem({ foodId: "b", usePriority: "high" }),
    ];
    const candidates = [
      makeRecipe({ recipeId: "low", foodIds: ["c"], rating: 1 }),
      makeRecipe({ recipeId: "high", foodIds: ["a", "b"], rating: 5 }),
    ];
    const result = scoreRecipes(candidates, [], pantry, defaultWeights(), null);
    expect(result[0].recipeId).toBe("high");
    expect(result[0].totalScore).toBeGreaterThan(result[1].totalScore);
  });
});
