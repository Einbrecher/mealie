# Implementation Plan: Optimizer UI — Meal Planner Page

Source: docs/plans/2026-04-14-060214-optimizer-ui.md
Revised: 2026-04-14

<plan_metadata>
  <feature>Optimizer Meal Planner UI</feature>
  <source>docs/plans/2026-04-14-060214-optimizer-ui.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>5</phases>
  <tasks>12</tasks>
  <status>revised</status>
  <critical_path>0.1 → 1.1a → 1.1b → 2.1 → 2.2 → 4.1a → 4.1b → 4.2</critical_path>
  <parallel_paths>Phase 2 (2.1 → 2.2) and Phase 3 (3.1 → 3.2, 3.3) run concurrently after Phase 1. Task 1.2 is independent of all other Phase 1 tasks.</parallel_paths>
</plan_metadata>

## Overview

Build the Optimizer Meal Planner page — a two-panel layout at `/g/{groupSlug}/optimizer/planner` where users build weekly meal plans using AI-scored recipe suggestions. The left panel shows a 7-day grid (PlanGrid) with multi-entry PlanSlot cells organized by entry type (breakfast, lunch, dinner by default). The right panel shows a SuggestionSidebar with ranked recipe cards (OptimizerRecipeCard) displaying scoring breakdowns and pantry match chips, plus a collapsible ConfigPanel for tuning scoring weights.

**Multi-entry slots**: Each slot (date+entryType) holds an ordered list of recipes — the first is the primary (entree), subsequent entries are complements (sides, accompaniments). The scoring engine uses two-context scoring: `plannedOutsideSlot` (recipes in other slots — ingredient overlap here is rewarded) and `plannedInSlot` (recipes already in this slot — high similarity here is penalized via `slotOverlapPenalty` to promote complementary suggestions).

Recipes are dragged from the sidebar into grid slots using native HTML drag-and-drop. A composable (use-optimizer-planner) orchestrates all data loading, draft state management, scoring integration, and meal plan CRUD. All code lives in `optimizer/` subdirectories per fork isolation rules, except for one sidebar nav link addition in DefaultLayout.vue and i18n keys in en-US.json.

## Changes from Original

<revision_summary>
<change type="critical-fix">
  Fixed `updateOne` API call signature in task 1.1b: was `api.mealplans.updateOne({...})` (single object), corrected to `api.mealplans.updateOne(existingEntryId, payload)` (two arguments) matching BaseCRUDAPI contract.
</change>
<change type="critical-fix">
  Added `groupId`, `userId`, `householdId` fields to DraftPlanEntry for existing entries. UpdatePlanEntry requires these non-optional fields; the original plan discarded them during ReadPlanEntry → DraftPlanEntry mapping.
</change>
<change type="structural">
  Reuse existing `DateRange` interface from `frontend/app/composables/use-group-mealplan.ts:28-31` instead of redefining an identical interface.
</change>
<change type="structural">
  Fixed critical_path metadata: removed task 1.2 from the sequence (it has no dependencies and runs in parallel). Added explicit parallel_paths notation.
</change>
<change type="added">
  Added unsaved changes navigation guard as subtask in 4.1a. The i18n key `optimizer.planner.unsaved-changes` existed but no implementation was planned.
</change>
<change type="added">
  Added error handling UX (snackbar/toast on API failure) as subtasks in 1.1a and 1.1b. Original plan had "don't corrupt state" but no user-facing feedback.
</change>
<change type="clarity">
  Fixed N+1 recipe fetch in task 4.1b: changed sequential `for...of` loop to `Promise.all` with chunking for parallel fetches.
</change>
<change type="clarity">
  Elaborated savePlan() in 1.1b: split into explicit build-diff → execute-API → re-snapshot steps with clear data flow for groupId/userId.
</change>
<change type="clarity">
  Specified ReadPlanEntry → DraftPlanEntry field mapping in loadData(), including recipe name/slug extraction from ReadPlanEntry.recipe (RecipeSummary).
</change>
<change type="added">
  Added mobile/touch limitation to risk register — native HTML drag-and-drop does not work on mobile without polyfills.
</change>
<change type="dependency">
  Resolved Q2: `api.recipes.getOne(slug)` confirmed as correct method. RecipeAPI extends BaseCRUDAPI with `itemRoute = routes.recipesRecipeSlug` which takes a slug string.
</change>
</revision_summary>

## Prerequisites

<prerequisites>
<prereq id="P1" type="library" verified="true">
  <description>Vue 3 + Nuxt 4.4.2 + Vuetify 4.0.5 + TypeScript 5.3</description>
  <verification>Confirmed in frontend/package.json</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>vue-draggable-plus ^0.6.0 (NOT used for sidebar→grid, but available for future use)</description>
  <verification>Confirmed in frontend/package.json:35</verification>
</prereq>
<prereq id="P3" type="service" verified="true">
  <description>Scoring engine: scoreRecipes() in frontend/app/composables/optimizer/scoring-engine.ts — will be extended in Phase 0 with plannedInSlot parameter and slotOverlapPenalty</description>
  <verification>Read file, confirmed exports scoreRecipes(candidates, planned, pantryItems, weights, budget) → ScoredRecipe[]</verification>
</prereq>
<prereq id="P4" type="service" verified="true">
  <description>Scoring composable: useOptimizerScoring() in frontend/app/composables/optimizer/use-optimizer-scoring.ts — will be extended with setPlannedInSlot()</description>
  <verification>Read file, confirmed returns { scoredRecipes, setCandidates, setPlannedRecipes, setPantryItems, setWeights, setPrepTimeBudget }</verification>
</prereq>
<prereq id="P5" type="service" verified="true">
  <description>Optimizer API client: OptimizerApi in frontend/app/lib/api/user/optimizer-pantry.ts</description>
  <verification>Read file, confirmed .pantry (BaseCRUDAPI), .config.getConfig(), .config.updateConfig(), .getRecipeFoods()</verification>
</prereq>
<prereq id="P6" type="service" verified="true">
  <description>Meal plan CRUD API: api.mealplans — BaseCRUDAPI with createOne(payload), updateOne(itemId, payload), deleteOne(itemId), getAll(page, perPage, params)</description>
  <verification>Confirmed at frontend/app/lib/api/user/group-mealplan.ts:12-17. updateOne takes (itemId: string|number, payload: UpdatePlanEntry).</verification>
</prereq>
<prereq id="P7" type="data" verified="true">
  <description>All TypeScript types: PlanEntryType, CreatePlanEntry, ReadPlanEntry, UpdatePlanEntry, RecipeSummary (meal-plan.ts); OptimizerConfigOut, OptimizerConfigUpdate, RecipeFoodProjectionResponse (optimizer.ts); ScoringWeights, RecipeFoodData, ScoredRecipe, PantryMatchDetail, PantryItemScoring (types.ts). DateRange (use-group-mealplan.ts:28-31).</description>
  <verification>Read all type files. Note: UpdatePlanEntry requires id, groupId, userId as non-optional fields (meal-plan.ts:143-152).</verification>
</prereq>
<prereq id="P8" type="library" verified="true">
  <description>RecipeCardImage component with props: recipeId (required), slug, tiny/small/large, iconSize, height</description>
  <verification>Read frontend/app/components/Domain/Recipe/RecipeCardImage.vue:34-52</verification>
</prereq>
<prereq id="P9" type="library" verified="true">
  <description>RecipeDialogAddToShoppingList component — expects RecipeWithScale[] (extends Recipe with scale field) and ShoppingListSummary[]</description>
  <verification>Read component, confirmed Props interface. RecipeWithScale = Recipe & { scale: number }. Requires full Recipe objects, not RecipeFoodData.</verification>
</prereq>
<prereq id="P10" type="library" verified="true">
  <description>calendarWeek icon exists in $globals.icons</description>
  <verification>Confirmed at frontend/app/lib/icons/icons.ts:198 — calendarWeek: mdiCalendarWeek</verification>
</prereq>
<prereq id="P11" type="library" verified="true">
  <description>date-fns format() function for date formatting</description>
  <verification>Already used in use-group-mealplan.ts and mealplan planner pages</verification>
</prereq>
<prereq id="P12" type="data" verified="true">
  <description>Backend allows multiple meal plan entries per date+entryType (no uniqueness constraint)</description>
  <verification>Confirmed: GroupMealPlan model has no UniqueConstraint on date+entry_type. API layer does no duplicate validation.</verification>
</prereq>
<prereq id="P13" type="service" verified="true">
  <description>Recipe API: api.recipes.getOne(slug) returns full Recipe object. RecipeAPI extends BaseCRUDAPI with itemRoute = routes.recipesRecipeSlug which takes a slug string.</description>
  <verification>Confirmed at frontend/app/lib/api/user/recipes/recipe.ts:93-95. getOne inherited from BaseCRUDAPIReadOnly.</verification>
</prereq>
</prerequisites>

## Phase 0: Scoring Engine Extension

<phase id="0" name="Scoring Engine Extension">

### 0.1 Add Two-Context Scoring and Slot Overlap Penalty

<task id="0.1" status="pending" depends="" risk="medium">
<context>
Extend the scoring engine to support complement-aware scoring by adding a `plannedInSlot` context and a `slotOverlapPenalty` weight. This is a backwards-compatible change to two existing files and one composable.

**File 1: `frontend/app/composables/optimizer/types.ts`**

Add `slotOverlapPenalty` to the `ScoringWeights` interface:

```typescript
export interface ScoringWeights {
  overlap: number;
  pantryCoverage: number;
  pantryUrgency: number;
  proteinDiversity: number;
  categoryBalance: number;
  rating: number;
  slotOverlapPenalty: number;  // NEW: penalize similarity to recipes already in the active slot
  perishableLabelKeywords: string[];
  shelfStableLabelKeywords: string[];
}
```

**File 2: `frontend/app/composables/optimizer/scoring-engine.ts`**

Add a new scoring function `slotOverlapScore()` and extend `scoreRecipes()`:

```typescript
// NEW function — measures how similar a candidate is to recipes already in the active slot
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

  // Weighted average: ingredients matter most, then tags, then categories
  return foodOverlap * 0.5 + tagOverlap * 0.3 + catOverlap * 0.2;
}
```

Extend `scoreRecipes()` signature — add `plannedInSlot` parameter with a default of `[]`:

```typescript
export function scoreRecipes(
  candidates: RecipeFoodData[],
  plannedRecipes: RecipeFoodData[],       // recipes in OTHER slots (overlap here is good)
  pantryItems: PantryItemScoring[],
  weights: ScoringWeights,
  prepTimeBudget: number | null,
  plannedInSlot: RecipeFoodData[] = [],   // NEW: recipes in the ACTIVE slot (similarity here is penalized)
): ScoredRecipe[] {
```

In the scoring loop, after computing all existing scores, add:

```typescript
const slotSimilarity = slotOverlapScore(
  candidate.foodIds, candidate.tagIds, candidate.categoryIds, plannedInSlot,
);

const totalScore
  = weights.overlap * overlap
    + weights.pantryCoverage * coverage
    + weights.pantryUrgency * urgencyResult.score
    + weights.proteinDiversity * protein
    + weights.categoryBalance * category
    + weights.rating * ratingScore
    - weights.slotOverlapPenalty * slotSimilarity;  // SUBTRACT penalty
```

Add `slotSimilarity` to the breakdown object in the ScoredRecipe result.

**File 3: `frontend/app/composables/optimizer/use-optimizer-scoring.ts`**

Add `plannedInSlot` ref and `setPlannedInSlot` method. Pass `plannedInSlot.value` as the new parameter to `scoreRecipes()` in the computed. Update default weights to include `slotOverlapPenalty: 0.7`.

**Backwards compatibility**: All changes are additive. The new `plannedInSlot` parameter defaults to `[]`, which produces `slotSimilarity = 0`, so the penalty term vanishes. Existing tests and callers are unaffected.
</context>

<subtasks>
- [ ] Add `slotOverlapPenalty: number` to ScoringWeights interface in types.ts
- [ ] Add `slotOverlapScore()` function in scoring-engine.ts
- [ ] Extend `scoreRecipes()` with `plannedInSlot` parameter (default `[]`)
- [ ] Integrate slotSimilarity into totalScore calculation (subtracted, not added)
- [ ] Add `slotSimilarity` to the breakdown object in scored results
- [ ] Add `plannedInSlot` ref and `setPlannedInSlot` method to use-optimizer-scoring.ts
- [ ] Pass `plannedInSlot.value` to `scoreRecipes()` in the computed
- [ ] Update default weights in use-optimizer-scoring.ts to include `slotOverlapPenalty: 0.7`
- [ ] Verify existing scoring-engine.test.ts tests still pass (they use the old signature with default param)
</subtasks>

<acceptance>
- `ScoringWeights` has `slotOverlapPenalty` field
- `scoreRecipes()` accepts `plannedInSlot` parameter (defaults to `[]`)
- When `plannedInSlot = []`, scoring results are identical to before (no penalty)
- When `plannedInSlot` has recipes, candidates with high ingredient/tag/category overlap get penalized
- `slotSimilarity` appears in `ScoredRecipe.breakdown`
- `useOptimizerScoring()` exposes `setPlannedInSlot()` method
- Existing tests pass: `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts`
- TypeScript compiles without errors
</acceptance>

<rollback risk="medium">
These are modifications to existing files. Revert the three files to their pre-change state if needed. Changes are additive (new parameter with default), so partial application won't break existing callers.
</rollback>
</task>

### Phase 0 Checkpoint

<checkpoint phase="0">
<verification>
- [ ] `scoring-engine.test.ts` tests pass: `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts`
- [ ] TypeScript compiles for all three modified files
- [ ] `slotOverlapScore()` returns 0 when `slotRecipes` is empty
- [ ] `slotOverlapScore()` returns > 0 when candidate shares ingredients with slot recipes
- [ ] `scoreRecipes()` with empty `plannedInSlot` produces identical results to before
</verification>
<gate>Scoring engine supports two-context scoring with backwards compatibility. The slotOverlapPenalty is functional and tested.</gate>
</checkpoint>

</phase>

## Phase 1: Foundation — Composable & i18n

<phase id="1" name="Foundation" depends="0">

### 1.1a Create use-optimizer-planner.ts — Data Loading & Normalization

<task id="1.1a" status="pending" depends="0.1" risk="medium">
<context>
Create `frontend/app/composables/optimizer/use-optimizer-planner.ts` with the data loading and normalization portion of the composable. This composable is the single source of truth for the planner page.

**Why bypass useMealplans**: The existing `useMealplans(range)` composable (at `frontend/app/composables/use-group-mealplan.ts:33-115`) auto-calls `getAll()` on initialization AND watches the range ref for changes, triggering automatic refreshes. The optimizer planner needs a draft-based editing model where loaded entries are snapshotted and edits happen locally until explicitly saved. Using `useMealplans` would cause double-fetches and conflict with the draft model. Instead, call `api.mealplans.getAll()` directly for initial load and use `api.mealplans.createOne/updateOne/deleteOne` for saves.

**Reuse existing DateRange**: Import `DateRange` from `~/composables/use-group-mealplan` instead of redefining. It's `{ start: Date; end: Date }` — exactly what we need.

**Data normalization in this composable**:
1. `api.optimizer.getRecipeFoods()` returns `RecipeFoodProjectionResponse` (defined in `frontend/app/lib/api/types/optimizer.ts`). MUST unwrap `.items` to get `RecipeFoodProjection[]`. Each `RecipeFoodProjection` matches `RecipeFoodData` shape exactly, so can be cast directly.
2. `api.optimizer.pantry.getAll()` returns paginated `PantryItemOut[]`. Must map each to `PantryItemScoring` (defined in `frontend/app/composables/optimizer/types.ts`): extract `foodId`, `food.name` → `foodName`, `food.label.name` → `labelName`, `usePriority`, `assumeEnough`, `expirationDate`. Items without a `foodId` should be filtered out.
3. `api.optimizer.config.getConfig()` returns `OptimizerConfigOut`. Must map to `ScoringWeights`: `overlapWeight`→`overlap`, `pantryUtilizationWeight`→`pantryCoverage`, `pantryUrgencyWeight`→`pantryUrgency`, `proteinDiversityWeight`→`proteinDiversity`, `categoryBalanceWeight`→`categoryBalance`, `ratingWeight`→`rating`, plus `perishableLabelKeywords` and `shelfStableLabelKeywords` pass through. **NEW**: Map the slotOverlapPenalty — if the backend config doesn't have this field yet, default to `0.7`.

**Multi-entry draft model**: Slots hold lists of entries, not single entries.

```typescript
export interface DraftPlanEntry {
  localId: string;                     // client-side UUID for tracking new entries
  date: string;                        // "YYYY-MM-DD"
  entryType: PlanEntryType;
  order: number;                       // 0 = primary (entree), 1+ = complement (side)
  recipeId: string | null;
  recipeName: string | null;
  recipeSlug: string | null;
  existingEntryId: number | null;      // non-null → maps to a backend ReadPlanEntry.id
  // Backend fields needed for UpdatePlanEntry — only populated for existing entries
  groupId: string | null;
  userId: string | null;
  householdId: string | null;
}
```

**IMPORTANT — Backend fields**: `UpdatePlanEntry` (at `frontend/app/lib/api/types/meal-plan.ts:143-152`) requires `id: number`, `groupId: string`, `userId: string` as non-optional fields. When loading existing entries from `ReadPlanEntry`, copy these fields into `DraftPlanEntry`. For new entries (added via drag/click), these are null and will not need updating (they use `createOne` instead).

**Key exports from this file (this task)**:
```typescript
export function useOptimizerPlanner(): UsePlannerReturn { ... }
```

**Reactive state returned**:
- `dateRange: Ref<DateRange>` — import DateRange from `~/composables/use-group-mealplan`. Defaults to today + 6 days (7 days total)
- `days: ComputedRef<Date[]>` — array of dates derived from dateRange
- `draftEntries: Ref<Map<string, DraftPlanEntry[]>>` — keyed by `"YYYY-MM-DD|entryType"`, values are ordered arrays (index 0 = primary)
- `scoredRecipes: ComputedRef<ScoredRecipe[]>` — from useOptimizerScoring()
- `recipeDataMap: ComputedRef<Map<string, RecipeFoodData>>` — keyed by recipeId for O(1) lookups
- `config: Ref<OptimizerConfigOut | null>`
- `loading: Ref<boolean>`
- `saving: Ref<boolean>`
- `error: Ref<string | null>` — error message for user-facing feedback
- `unlinkedRecipeCount: Ref<number>` — from RecipeFoodProjectionResponse.unlinkedRecipeCount
- `activeSlotKey: Ref<string | null>` — currently selected slot for sidebar context

**loadData() implementation**:
1. Set loading = true, error = null
2. Wrap in try/catch. On error: set `error = "Failed to load planner data"`, set loading = false, return early.
3. Fetch in parallel: api.optimizer.getRecipeFoods(), api.optimizer.pantry.getAll(1, -1), api.optimizer.config.getConfig(), api.mealplans.getAll(1, -1, { start_date, end_date })
4. Normalize all responses as described above
5. Feed into useOptimizerScoring(): setCandidates(recipeFoodData), setPantryItems(pantryScoring), setWeights(scoringWeights), setPrepTimeBudget(config.prepTimeBudgetMinutes)
6. Build recipeDataMap as Map<string, RecipeFoodData>
7. Populate draftEntries from existing meal plan entries: group ReadPlanEntry[] by `"date|entryType"` key, sort by id ascending within each group (preserves creation order), map to DraftPlanEntry[] with:
   - `localId`: crypto.randomUUID()
   - `order`: array index (0, 1, 2, ...)
   - `existingEntryId`: entry.id
   - `recipeName`: entry.recipe?.name ?? null
   - `recipeSlug`: entry.recipe?.slug ?? null
   - `recipeId`: entry.recipeId ?? null
   - `groupId`: entry.groupId
   - `userId`: entry.userId
   - `householdId`: entry.householdId
8. Snapshot loaded entries for diff comparison on save (deep clone the draftEntries Map)
9. Set loading = false

**Active slot and complement scoring**: When `activeSlotKey` changes, look up the recipes in that slot from draftEntries, resolve them to RecipeFoodData via recipeDataMap, and call `setPlannedInSlot()` on the scoring composable. When no slot is active (or the active slot is empty), call `setPlannedInSlot([])`.

**Important**: Store the `useUserApi()` result inside the composable. Follow the pattern from `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue:134` where `useUserApi()` is called and `userApi.optimizer.*` is used.

**File location**: `frontend/app/composables/optimizer/use-optimizer-planner.ts`
</context>

<subtasks>
- [ ] Create the file with all imports (import DateRange from `~/composables/use-group-mealplan`, types from existing files)
- [ ] Define DraftPlanEntry interface with localId, order, AND groupId/userId/householdId fields (export it)
- [ ] Define UsePlannerReturn interface
- [ ] Implement useOptimizerPlanner() function shell with all reactive refs including `error: Ref<string | null>`
- [ ] Implement loadData() with parallel API fetches wrapped in try/catch with error message
- [ ] Implement RecipeFoodProjectionResponse → RecipeFoodData[] normalization (unwrap .items)
- [ ] Implement PantryItemOut[] → PantryItemScoring[] mapping (filter items without foodId)
- [ ] Implement OptimizerConfigOut → ScoringWeights mapping (including slotOverlapPenalty default)
- [ ] Implement ReadPlanEntry[] → Map<string, DraftPlanEntry[]> population — extract recipeName from entry.recipe?.name, recipeSlug from entry.recipe?.slug, groupId/userId/householdId from the entry
- [ ] Build recipeDataMap (Map<string, RecipeFoodData>) as computed
- [ ] Wire useOptimizerScoring() — set candidates, pantry, weights, prepTimeBudget
- [ ] Compute days array from dateRange
- [ ] Store loaded entries snapshot (deep clone) for save diffing
- [ ] Implement activeSlotKey watcher that updates setPlannedInSlot() on the scoring composable
- [ ] Generate localId using crypto.randomUUID()
</subtasks>

<acceptance>
- File exists at `frontend/app/composables/optimizer/use-optimizer-planner.ts`
- TypeScript compiles without errors: `cd frontend && npx nuxi typecheck` (or no IDE errors)
- DraftPlanEntry has localId, order, groupId, userId, householdId fields
- DateRange is imported from `~/composables/use-group-mealplan`, NOT redefined
- draftEntries is Map<string, DraftPlanEntry[]> (arrays, not single entries)
- Multiple ReadPlanEntry items with same date+entryType are all loaded (grouped, ordered by creation)
- Loaded entries have recipeName from ReadPlanEntry.recipe?.name and recipeSlug from entry.recipe?.slug
- Loaded entries have groupId/userId/householdId from ReadPlanEntry
- useOptimizerPlanner() returns all properties defined in UsePlannerReturn
- loadData() calls all 4 APIs and normalizes responses
- loadData() sets error ref on API failure (does not throw)
- recipeDataMap is a computed Map keyed by recipeId
- scoredRecipes comes from useOptimizerScoring() and reactively updates
- activeSlotKey changes trigger setPlannedInSlot() updates for complement scoring
</acceptance>

<rollback risk="medium">
This file is new — delete it to rollback. No existing files modified.
</rollback>
</task>

### 1.1b Create use-optimizer-planner.ts — Draft Actions & Save Orchestration

<task id="1.1b" status="pending" depends="1.1a" risk="high">
<context>
Add the draft manipulation methods and save orchestration to `use-optimizer-planner.ts`. This is the most complex part of the composable.

**Draft actions (multi-entry)**:
- `addToDraft(date: string, entryType: PlanEntryType, recipeId: string)`: Look up recipe in recipeDataMap to get name and slug. Get the current entries array for the slot key `"${date}|${entryType}"` (or create empty array). Determine order: if array is empty, order = 0 (primary); otherwise order = array.length (complement). Create DraftPlanEntry with a new localId (crypto.randomUUID()), existingEntryId=null, groupId=null, userId=null, householdId=null. Append to array. After adding, update scoring context:
  - Update `setPlannedRecipes()` with all recipes across ALL slots (for global overlap/diversity)
  - If this slot is the active slot, update `setPlannedInSlot()` with this slot's recipes (for complement scoring)
- `removeFromDraft(slotKey: string, localId: string)`: Find and remove the specific entry by localId from the slot's array. Re-number remaining entries' order values (0-based contiguous). Recalculate scoring context.
- `clearSlot(slotKey: string)`: Remove all entries from a slot. Recalculate scoring context.
- `clearAllDrafts()`: Reset all draftEntries to empty Map. Recalculate scoring context.

**plannedRecipeIds** (ComputedRef<Set<string>>): Derive from ALL draftEntries values across all slots, collecting all non-null recipeId values.

**hasUnsavedChanges** (ComputedRef<boolean>): Compare current draftEntries against loadedEntriesSnapshot. True if:
- Any slot has different number of entries
- Any entry's recipeId differs at the same position
- Any new entries added (existingEntryId is null)
- Any loaded entries removed

**Scoring reactivity**: When draftEntries changes, the planned recipes for the scoring engine must update. Use a `watch` on draftEntries (deep: true) to call `setPlannedRecipes()` with ALL planned recipe data across all slots. Add a 150ms debounce using a timeout to avoid churn during rapid drag operations. Also update `setPlannedInSlot()` if the active slot's contents changed.

**savePlan()**: This is the critical method. Three-step implementation:

**Step 1 — Build diff**: Iterate each slot key in the union of draftEntries keys and loadedEntriesSnapshot keys. For each slot, compare draft entries to snapshot entries:
- **New entries**: draft entries with `existingEntryId === null` and `recipeId !== null` → mark for create
- **Updated entries**: draft entries with `existingEntryId !== null` and `recipeId` differs from snapshot → mark for update
- **Deleted entries**: snapshot entries whose `existingEntryId` has no match in the draft → mark for delete

**Step 2 — Execute API calls**:
- For creates: `api.mealplans.createOne({ date, entryType, recipeId })` — uses CreatePlanEntry (no id/groupId/userId needed)
- For updates: `api.mealplans.updateOne(existingEntryId, { date, entryType, recipeId, id: existingEntryId, groupId, userId })` — **TWO arguments**: first is the id, second is UpdatePlanEntry. The `groupId` and `userId` come from the DraftPlanEntry fields (populated during loadData from ReadPlanEntry).
- For deletes: `api.mealplans.deleteOne(existingEntryId)`
- Use `Promise.allSettled()` to execute all operations, then check for failures.

**Step 3 — Re-snapshot**: After all operations complete, re-load entries for the date range via `api.mealplans.getAll()` and rebuild draftEntries + snapshot. This ensures consistency even if some operations failed.

**Error handling**: Wrap in try/catch. On failure: set `error = "Some changes could not be saved"`, still re-load to sync state. Set saving = false regardless.

**updateConfig(config: OptimizerConfigUpdate)**: Call api.optimizer.config.updateConfig(config), then update local config ref and re-map to ScoringWeights for the scoring engine.

**setActiveSlot(slotKey: string | null)**: Set activeSlotKey. When set, resolve the slot's recipes to RecipeFoodData[] and call setPlannedInSlot(). When null, call setPlannedInSlot([]).
</context>

<subtasks>
- [ ] Implement addToDraft() with localId generation, order assignment, null groupId/userId/householdId for new entries, and scoring update
- [ ] Implement removeFromDraft(slotKey, localId) with order renumbering and scoring update
- [ ] Implement clearSlot(slotKey) and clearAllDrafts()
- [ ] Implement plannedRecipeIds computed (across all slots)
- [ ] Implement hasUnsavedChanges computed (diff draftEntries vs loadedEntriesSnapshot, per-slot per-entry)
- [ ] Add debounced (150ms) watch on draftEntries to update plannedRecipes in scoring engine
- [ ] Implement savePlan() Step 1: build diff lists (toCreate, toUpdate, toDelete)
- [ ] Implement savePlan() Step 2: execute API calls — createOne(payload), updateOne(existingEntryId, updatePayload), deleteOne(existingEntryId) — using Promise.allSettled
- [ ] Implement savePlan() Step 3: re-load entries from API and rebuild draftEntries + snapshot
- [ ] Add error handling: try/catch, set error ref on failure, always re-sync state
- [ ] Implement setActiveSlot() that updates activeSlotKey and calls setPlannedInSlot()
- [ ] Implement updateConfig() with API call and scoring weight re-mapping
</subtasks>

<acceptance>
- addToDraft() appends to slot array with correct order (0 for primary, N for complement)
- New draft entries have groupId=null, userId=null, householdId=null
- removeFromDraft() removes by localId and renumbers remaining entries
- hasUnsavedChanges is true after addToDraft/removeFromDraft and false after savePlan
- savePlan() correctly calls `api.mealplans.updateOne(existingEntryId, payload)` with TWO arguments
- savePlan() passes groupId/userId from DraftPlanEntry into the UpdatePlanEntry payload
- savePlan() creates new entries with `api.mealplans.createOne({ date, entryType, recipeId })`
- savePlan() deletes removed entries with `api.mealplans.deleteOne(existingEntryId)`
- savePlan() re-loads and re-snapshots after all operations
- API failures set the `error` ref with a user-facing message
- setActiveSlot() triggers setPlannedInSlot() for complement scoring
- updateConfig() persists to API and updates scoring weights
- TypeScript compiles without errors
</acceptance>

<rollback risk="high">
This modifies the file created in 1.1a. If save logic is buggy, it could create/delete wrong meal plan entries. The draft model isolates changes until explicit save, so the risk is contained to the save action. If rollback needed, revert the file to 1.1a state.
</rollback>
</task>

### 1.2 Add i18n Keys

<task id="1.2" status="pending" depends="" risk="low">
<context>
Add all planner i18n keys to `frontend/app/lang/messages/en-US.json`. This task has NO dependencies and can run in parallel with all other Phase 1 tasks.

The file currently has an "optimizer" object at line 1484 with "pantry" and "config" sub-objects. Add a new "planner" object AFTER the "config" block, before the closing `}` of "optimizer". Also add a new key to the existing "config" block.

**Keys to add** (under `optimizer.planner.*`):
```json
"planner": {
  "title": "Meal Planner",
  "date-range": "Date Range",
  "save-plan": "Save Plan",
  "saving": "Saving...",
  "generate-shopping-list": "Generate Shopping List",
  "no-suggestions": "No recipe suggestions available",
  "search-recipes": "Search recipes...",
  "suggestions-for": "Suggestions for {entryType} on {date}",
  "complement-for": "Complement for {entryType} on {date}",
  "overlap": "{percent}% ingredient overlap",
  "pantry-match": "Uses {count} pantry item | Uses {count} pantry items",
  "expires-in-days": "expires in {days} day | expires in {days} days",
  "expires-today": "expires today",
  "expired": "expired",
  "empty-slot": "Click to add or drag a recipe here",
  "add-complement": "Add a side or complement",
  "primary": "Entree",
  "complement": "Complement",
  "unsaved-changes": "You have unsaved changes. Save before leaving?",
  "plan-saved": "Meal plan saved",
  "save-error": "Some changes could not be saved",
  "load-error": "Failed to load planner data",
  "unlinked-recipes-hint": "{count} recipe has unlinked ingredients | {count} recipes have unlinked ingredients",
  "config-panel-title": "Scoring Weights",
  "slot-overlap-penalty-weight": "Complement Contrast",
  "clear-slot": "Clear slot",
  "clear-all": "Clear All",
  "no-planned-recipes": "No recipes in the plan yet"
}
```

Also add to the existing `optimizer.config` block:
```json
"slot-overlap-penalty-weight": "Complement Contrast"
```

Note: Pluralization syntax uses `|` separator per vue-i18n convention.
</context>

<subtasks>
- [ ] Add comma after the "config" block's closing `}`
- [ ] Add `"slot-overlap-penalty-weight"` key to the "config" block
- [ ] Insert the "planner" block with all keys (including error message keys)
- [ ] Verify JSON is valid: `node -e "JSON.parse(require('fs').readFileSync('frontend/app/lang/messages/en-US.json'))"`
</subtasks>

<acceptance>
- JSON file parses without errors: `node -e "JSON.parse(require('fs').readFileSync('frontend/app/lang/messages/en-US.json'))"`
- All 25 planner keys exist under `optimizer.planner.*` (including save-error, load-error, no-planned-recipes)
- `slot-overlap-penalty-weight` key exists under `optimizer.config.*`
- No other keys were modified
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `frontend/app/composables/optimizer/use-optimizer-planner.ts` exists and exports `useOptimizerPlanner`, `DraftPlanEntry`
- [ ] DraftPlanEntry has `localId`, `order`, `groupId`, `userId`, `householdId` fields
- [ ] DateRange is imported from `~/composables/use-group-mealplan`, not redefined
- [ ] draftEntries is Map of arrays
- [ ] TypeScript compiles: `cd frontend && npx nuxi typecheck` (or at minimum, no IDE errors)
- [ ] en-US.json is valid JSON with all optimizer.planner.* keys including error messages
- [ ] updateOne call uses two arguments: `updateOne(id, payload)`
- [ ] Scoring updates when active slot changes (complement scoring kicks in)
</verification>
<gate>The composable is complete with multi-entry slot support, complement-aware scoring, and correct API call signatures. i18n keys exist for all UI text. No UI yet — that comes in Phase 2-4.</gate>
</checkpoint>

</phase>

## Phase 2: Grid Components

<phase id="2" name="Grid Components" depends="1">

### 2.1 Create PlanSlot.vue

<task id="2.1" status="pending" depends="1.1b" risk="low">
<context>
Create `frontend/app/components/optimizer/PlanSlot.vue` — a multi-entry meal plan slot that shows a list of recipes (primary + complements) or an empty drop target.

**Props** (use defineProps with TypeScript generics):
```typescript
const props = defineProps<{
  entries: DraftPlanEntry[];       // ordered array: [0] = primary, [1+] = complements
  slotKey: string;                 // "YYYY-MM-DD|entryType" for identifying this slot
  isActive: boolean;               // true = highlighted for sidebar context
}>();
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "click"): void;                           // slot clicked (set as active)
  (e: "remove", localId: string): void;          // remove specific entry by localId
  (e: "drop", recipeId: string): void;           // recipe dropped onto slot
}>();
```

**Template structure**:
- Outer `div` with drop zone handlers (`@dragover.prevent`, `@drop`)
- **Active state**: Add a `border: 2px solid rgb(var(--v-theme-primary))` CSS class when `isActive` is true. Click on the slot area → emits "click".

- **Empty state** (entries is empty): Dashed border card with `$mdi-plus` icon and `$t('optimizer.planner.empty-slot')` text. Clickable → emits "click".

- **Filled state** (entries has items): Render each entry in a vertical list:
  - **Primary entry** (order 0): Slightly larger card with:
    - Small RecipeCardImage (import from `~/components/Domain/Recipe/RecipeCardImage.vue`) with `tiny` prop, using `entry.recipeId` and `entry.recipeSlug`
    - Recipe name text (`entry.recipeName`)
    - Small chip/label: `$t('optimizer.planner.primary')` ("Entree")
    - Remove button (X icon) visible on hover → emits "remove" with `entry.localId`
  - **Complement entries** (order 1+): Smaller/more compact cards with:
    - Recipe name text (smaller font)
    - Small chip/label: `$t('optimizer.planner.complement')` ("Complement")
    - Remove button on hover → emits "remove" with `entry.localId`
  - **Add complement prompt**: After existing entries, a subtle "+" button with `$t('optimizer.planner.add-complement')` text, clickable → emits "click" to set active slot for adding more

- **Drop handling**: `@drop` handler extracts `recipeId` from `event.dataTransfer.getData("text/recipeId")`. Emits "drop" with the recipeId.

**CSS**: Use scoped styles. Hover effect for remove button (opacity 0 → 1 on card hover). Complements should be visually subordinate to the primary (smaller font, lighter background or indented).

**File location**: `frontend/app/components/optimizer/PlanSlot.vue`
</context>

<subtasks>
- [ ] Create file with `<template>`, `<script setup lang="ts">`, `<style scoped>` sections
- [ ] Import DraftPlanEntry type from composable
- [ ] Import RecipeCardImage component
- [ ] Implement empty state with dashed border, plus icon, and click handler
- [ ] Implement filled state with primary entry (larger, with "Entree" chip)
- [ ] Implement complement entries (smaller, with "Complement" chip)
- [ ] Implement "Add complement" prompt after existing entries
- [ ] Implement active state with highlighted border
- [ ] Implement native HTML drop handlers (@dragover.prevent, @drop with dataTransfer)
- [ ] Add hover CSS for remove button visibility
- [ ] Style complements as visually subordinate to primary
</subtasks>

<acceptance>
- Component renders empty state when entries is empty
- Component renders primary entry (order 0) with image, name, and "Entree" chip
- Component renders complement entries (order 1+) with name and "Complement" chip
- "Add complement" button appears after existing entries
- Active state shows highlighted border
- Drop handler reads recipeId from dataTransfer and emits "drop" event
- Remove button visible on hover, emits "remove" with correct localId
- Click on empty slot or add-complement emits "click"
- TypeScript compiles without errors
</acceptance>
</task>

### 2.2 Create PlanGrid.vue

<task id="2.2" status="pending" depends="2.1" risk="low">
<context>
Create `frontend/app/components/optimizer/PlanGrid.vue` — a grid layout with day columns and entry type rows, using PlanSlot for each cell.

**Props**:
```typescript
import type { PlanEntryType } from "~/lib/api/types/meal-plan";
import type { DraftPlanEntry } from "~/composables/optimizer/use-optimizer-planner";

const props = defineProps<{
  days: Date[];                              // array of Date objects for column headers
  entries: Map<string, DraftPlanEntry[]>;    // key: "YYYY-MM-DD|entryType", values: ordered entry arrays
  entryTypes: PlanEntryType[];               // rows to display (default: breakfast, lunch, dinner)
  activeSlot: string | null;                 // currently selected slot key
}>();
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "slot-click", date: string, entryType: PlanEntryType): void;
  (e: "slot-drop", date: string, entryType: PlanEntryType, recipeId: string): void;
  (e: "entry-remove", slotKey: string, localId: string): void;
}>();
```

**Template layout**: Use a CSS grid or Vuetify v-row/v-col:
- **Header row**: Empty cell (for row labels) + one cell per day showing formatted date. Use `date-fns` `format(day, "EEE M/d")` for display (e.g., "Mon 4/14"). Import `format` from `date-fns`.
- **Entry type rows**: For each entryType in props.entryTypes:
  - First cell: entry type label using `$t("meal-plan." + entryType)` (these i18n keys already exist)
  - Per-day cells: PlanSlot component with:
    - `:entries="entries.get(formatDate(day) + '|' + entryType) ?? []"`
    - `:slot-key="formatDate(day) + '|' + entryType"`
    - `:is-active="activeSlot === formatDate(day) + '|' + entryType"`
    - `@click` → emit slot-click with date string and entryType
    - `@drop="(recipeId) => emit('slot-drop', formatDate(day), entryType, recipeId)"`
    - `@remove="(localId) => emit('entry-remove', formatDate(day) + '|' + entryType, localId)"`

**Date formatting helper**: `function formatDate(date: Date): string { return format(date, "yyyy-MM-dd"); }` — import `format` from `date-fns`.

**Scrollable**: The grid should be horizontally scrollable if there are more days than fit the viewport (wrap in a div with `overflow-x: auto`).

**File location**: `frontend/app/components/optimizer/PlanGrid.vue`
</context>

<subtasks>
- [ ] Create file with template, script setup, and scoped styles
- [ ] Import PlanSlot component, date-fns format, and required types
- [ ] Implement grid layout with day headers and entry type row labels
- [ ] Render PlanSlot for each cell, passing entries array (not single entry)
- [ ] Wire all emit handlers (slot-click, slot-drop, entry-remove with slotKey + localId)
- [ ] Add horizontal scroll for wide grids
- [ ] Style grid cells with consistent sizing
</subtasks>

<acceptance>
- Grid renders correct number of columns (days.length + 1 for labels)
- Grid renders correct number of rows (entryTypes.length + 1 for header)
- Each cell contains a PlanSlot with correct entries array from the Map
- Multi-entry slots show all entries (primary + complements)
- Date headers show formatted dates
- Entry type labels use existing i18n keys
- All events (slot-click, slot-drop, entry-remove) propagate correctly with correct parameters
- TypeScript compiles without errors
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `frontend/app/components/optimizer/PlanSlot.vue` renders empty, single-entry (primary only), and multi-entry (primary + complements) states
- [ ] `frontend/app/components/optimizer/PlanGrid.vue` renders a grid of PlanSlots with correct multi-entry data
- [ ] Native HTML drag-and-drop: dropping onto a PlanSlot emits "drop" with recipeId
- [ ] Remove events carry the correct localId for identifying which entry to remove
- [ ] TypeScript compiles without errors for both components
</verification>
<gate>Grid components render correctly with multi-entry slot support. PlanSlot handles empty/primary/complement states and native drag-drop. PlanGrid wires slots into a days × entryTypes layout.</gate>
</checkpoint>

</phase>

## Phase 3: Sidebar Components

<phase id="3" name="Sidebar Components" depends="1">

Note: Phase 3 can run **in parallel** with Phase 2. Both depend on Phase 1 completion but are independent of each other.

### 3.1 Create OptimizerRecipeCard.vue

<task id="3.1" status="pending" depends="1.1a" risk="low">
<context>
Create `frontend/app/components/optimizer/OptimizerRecipeCard.vue` — a compact, draggable recipe card showing scoring breakdown and pantry match chips.

**Props**:
```typescript
import type { ScoredRecipe, RecipeFoodData, PantryMatchDetail } from "~/composables/optimizer/types";

const props = defineProps<{
  scored: ScoredRecipe;
  recipe: RecipeFoodData;
}>();
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "select", recipeId: string): void;
}>();
```

**Template structure** (use Vuetify v-card):
- **Card root**: `draggable="true"` attribute, `@dragstart` handler that sets `event.dataTransfer.setData("text/recipeId", recipe.recipeId)` and `event.dataTransfer.effectAllowed = "copy"`. Click → emit select.
- **Card content**:
  - Row 1: Small RecipeCardImage (tiny) + recipe name (bold) + total score badge
  - Row 2: Scoring breakdown chips:
    - Overlap percentage: `$t('optimizer.planner.overlap', { percent: Math.round(scored.breakdown.overlap * 100) })`
    - Rating: show as `★ X.X` if recipe.rating is not null
    - Prep time: show recipe.totalTime if available
    - Slot similarity: if `scored.breakdown.slotSimilarity > 0`, show a chip indicating complement contrast
  - Row 3: Pantry match chips (from `scored.pantryMatches`):
    - Each PantryMatchDetail → chip showing `match.foodName`
    - Chip color: warning (orange) if `match.daysToExpiry !== null && match.daysToExpiry <= 3`, success (green) otherwise
    - Chip subtitle: expiration text using i18n keys (expired, expires-today, expires-in-days)
    - Limit to first 5 matches; show "+X more" if there are more

**Visual style**: Compact card with dense information. Use v-chip for badges/tags. Card should have `cursor: grab` on hover to indicate draggability.

**File location**: `frontend/app/components/optimizer/OptimizerRecipeCard.vue`
</context>

<subtasks>
- [ ] Create file with template, script setup, scoped styles
- [ ] Import required types and RecipeCardImage component
- [ ] Implement HTML draggable attribute and dragstart handler with dataTransfer
- [ ] Implement card layout with recipe image, name, and score badge
- [ ] Implement scoring breakdown display (overlap percentage, rating, prep time, slot similarity)
- [ ] Implement pantry match chips with expiration-based coloring
- [ ] Implement chip limit (5 max) with "+X more" overflow indicator
- [ ] Add CSS for grab cursor and card hover effect
</subtasks>

<acceptance>
- Card shows recipe name, thumbnail, and total score
- Overlap percentage displays correctly (e.g., "72% ingredient overlap")
- Slot similarity indicator shows when applicable (complement context)
- Pantry match chips show food names with appropriate colors
- Expiring-soon items (<=3 days) show warning color
- Card is HTML-draggable; dragstart sets recipeId in dataTransfer
- Click on card emits "select" event with recipeId
- TypeScript compiles without errors
</acceptance>
</task>

### 3.2 Create SuggestionSidebar.vue

<task id="3.2" status="pending" depends="3.1" risk="low">
<context>
Create `frontend/app/components/optimizer/SuggestionSidebar.vue` — a scrollable panel showing ranked recipe suggestions with a search filter and complement-aware context hints.

**Props**:
```typescript
import type { ScoredRecipe, RecipeFoodData } from "~/composables/optimizer/types";

const props = defineProps<{
  scoredRecipes: ScoredRecipe[];
  recipeDataMap: Map<string, RecipeFoodData>;
  loading: boolean;
  activeEntryType: string | null;    // context hint: e.g., "dinner"
  activeDate: string | null;         // context hint: e.g., "2026-04-15"
  slotHasEntries: boolean;           // true if active slot already has recipes (complement mode)
}>();
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "select", recipeId: string): void;
}>();
```

**Template structure**:
- **Context hint** (when activeEntryType and activeDate are set):
  - If `!slotHasEntries`: Show `$t('optimizer.planner.suggestions-for', { entryType, date })` — "Suggestions for Tuesday dinner"
  - If `slotHasEntries`: Show `$t('optimizer.planner.complement-for', { entryType, date })` — "Complement for Tuesday dinner" — visually distinct to indicate complement mode
- **Search input**: `v-text-field` with search icon, `v-model` bound to local `searchQuery` ref, clearable, density="compact"
- **Loading state**: Show `v-skeleton-loader` (3-4 card-shaped skeletons) when `loading` is true
- **Recipe list**: Scrollable div (`overflow-y: auto`, `max-height: calc(100vh - 300px)`) containing OptimizerRecipeCard for each filtered recipe
- **Empty state**: When `filteredRecipes.length === 0` and not loading, show `$t('optimizer.planner.no-suggestions')` with an appropriate icon

**Search filtering**: `filteredRecipes` computed filters `scoredRecipes` where the recipe name (looked up via `recipeDataMap.get(scored.recipeId)?.name`) includes `searchQuery` (case-insensitive). Already sorted by totalScore descending (scoring engine sorts).

**Note on complement scoring**: When `slotHasEntries` is true, the scoring engine is already applying the `slotOverlapPenalty` via `setPlannedInSlot()` in the composable. The sidebar just needs to display the context hint — the scoring numbers in the recipe cards will naturally reflect the complement-aware ranking.

**File location**: `frontend/app/components/optimizer/SuggestionSidebar.vue`
</context>

<subtasks>
- [ ] Create file with template, script setup, scoped styles
- [ ] Import OptimizerRecipeCard and required types
- [ ] Implement search input with v-text-field
- [ ] Implement filteredRecipes computed with case-insensitive name search
- [ ] Implement scrollable recipe list rendering OptimizerRecipeCard per recipe
- [ ] Pass correct recipe prop from recipeDataMap lookup
- [ ] Implement context hint display with complement-aware messaging
- [ ] Implement loading skeleton state
- [ ] Implement empty state message
- [ ] Wire select event from OptimizerRecipeCard to emit
</subtasks>

<acceptance>
- Sidebar shows recipes sorted by score descending
- Search filters recipes by name (case-insensitive)
- Context hint shows "Suggestions for..." when slot is empty
- Context hint shows "Complement for..." when slot has entries (complement mode)
- Loading state shows skeletons
- Empty state shows message when no recipes match
- Select event propagates from card to sidebar emit
- TypeScript compiles without errors
</acceptance>
</task>

### 3.3 Create ConfigPanel.vue

<task id="3.3" status="pending" depends="1.1a" risk="low">
<context>
Create `frontend/app/components/optimizer/ConfigPanel.vue` — a collapsible panel with weight sliders for the scoring engine configuration, including the new slotOverlapPenalty weight.

**Props**:
```typescript
import type { OptimizerConfigOut, OptimizerConfigUpdate } from "~/lib/api/types/optimizer";

const props = defineProps<{
  config: OptimizerConfigOut | null;
  slotOverlapPenalty: number;        // managed client-side, not persisted to backend config (yet)
}>();
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "update", config: OptimizerConfigUpdate): void;
  (e: "update-slot-penalty", value: number): void;    // separate because it's client-side only
}>();
```

**Template structure**: Wrap everything in `v-expansion-panels` with a single `v-expansion-panel`:
- Panel title: `$t('optimizer.planner.config-panel-title')` (= "Scoring Weights")
- Panel content: One slider per weight, using `v-slider` with:
  - min="0", max="2", step="0.1"
  - thumb-label="always"
  - Each slider's label uses existing i18n keys from `optimizer.config.*`
  - **NEW**: `$t('optimizer.config.slot-overlap-penalty-weight')` → slotOverlapPenalty (0-2, step 0.1)
  - Prep time budget: `v-text-field` with type="number", min="0", clearable (null = no limit)

**Local state**: Use a reactive copy of props.config (`localConfig`) and a local copy of `slotOverlapPenalty`. Watch props to sync when they change externally (initial load).

**Debounced emit**: When any slider or the prep time input changes, debounce 500ms before emitting "update" with the full OptimizerConfigUpdate object. The slotOverlapPenalty slider emits "update-slot-penalty" separately (also debounced).

**Collapsed by default**: The v-expansion-panels should have no initial model value (all panels collapsed).

**Note on Vuetify 4**: Vuetify 4 `v-slider` supports `thumb-label` prop with values `true | false | "always"`. No existing usage in the codebase to cross-reference, but this is documented in Vuetify 4 API. If `thumb-label="always"` doesn't work, fall back to `thumb-label` (boolean, shows on interaction).

**File location**: `frontend/app/components/optimizer/ConfigPanel.vue`
</context>

<subtasks>
- [ ] Create file with template, script setup, scoped styles
- [ ] Import OptimizerConfigOut and OptimizerConfigUpdate types
- [ ] Implement v-expansion-panels with single panel, collapsed by default
- [ ] Create localConfig reactive copy from props.config with watch sync
- [ ] Implement 6 v-slider components for backend weights (0-2, step 0.1)
- [ ] Implement 1 v-slider for slotOverlapPenalty (client-side weight)
- [ ] Implement v-text-field for prep time budget (nullable number)
- [ ] Implement 500ms debounced emit on any value change
- [ ] Separate emit for slotOverlapPenalty (update-slot-penalty)
- [ ] Guard against emit when config is null (initial loading state)
</subtasks>

<acceptance>
- Panel renders collapsed by default
- Expanding shows 7 weight sliders (6 backend + 1 slot penalty) and 1 prep time input
- Sliders range 0.0 to 2.0 with 0.1 step and thumb labels
- Changing any backend slider triggers debounced (500ms) "update" emit
- Changing slot penalty slider triggers debounced "update-slot-penalty" emit
- Prep time input accepts numbers and null (clearable)
- All labels use i18n keys
- TypeScript compiles without errors
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `frontend/app/components/optimizer/OptimizerRecipeCard.vue` renders with scoring data including slotSimilarity and is draggable
- [ ] `frontend/app/components/optimizer/SuggestionSidebar.vue` renders ranked recipes with search and complement-aware context hints
- [ ] `frontend/app/components/optimizer/ConfigPanel.vue` renders 7 sliders (including slot penalty) and emits debounced updates
- [ ] All three components compile without TypeScript errors
</verification>
<gate>All sidebar components render correctly with complement-aware features. Recipe cards show slot similarity. Sidebar shows complement context hints. Config panel includes slot overlap penalty slider.</gate>
</checkpoint>

</phase>

## Phase 4: Assembly & Navigation

<phase id="4" name="Assembly" depends="2,3">

### 4.1a Create planner.vue Page — Layout & Core Wiring

<task id="4.1a" status="pending" depends="2.2,3.2,3.3" risk="medium">
<context>
Create `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` — the main optimizer planner page. This task covers the page layout, composable wiring, core interactions, and unsaved changes guard.

**Page structure** (following optimizer page pattern from pantry.vue):
```typescript
const { t } = useI18n();
useSeoMeta({ title: t("optimizer.planner.title") });
```

**Composable wiring**:
```typescript
const {
  dateRange, days, draftEntries, scoredRecipes, recipeDataMap,
  config, loading, saving, error, unlinkedRecipeCount, activeSlotKey,
  loadData, addToDraft, removeFromDraft, clearSlot, clearAllDrafts,
  savePlan, updateConfig, setActiveSlot,
  plannedRecipeIds, hasUnsavedChanges,
} = useOptimizerPlanner();
```

**Template — two-panel layout**:
Use `v-container` with `v-row`:
- **Left panel** (`v-col cols="12" md="8"`):
  - **Header row**: Title + date range picker (v-menu + v-date-picker with range selection, following pattern from `frontend/app/pages/household/mealplan/planner.vue:9-62`). The existing planner uses `v-date-picker` with `multiple="range"` and a `v-menu` trigger. Replicate this pattern: v-btn showing formatted date range → v-menu containing v-date-picker → on selection, update dateRange ref.
  - **Error alert**: Show `v-alert type="error"` when `error` ref is non-null, with error message text
  - **PlanGrid** component with props: `:days`, `:entries="draftEntries"`, `:entry-types="activeEntryTypes"`, `:active-slot="activeSlotKey"`
  - **Action buttons row**: Save Plan button (`:loading="saving"`, `:disabled="!hasUnsavedChanges"`), Generate Shopping List button, Clear All button
  - **Unlinked recipes hint**: Show `$t('optimizer.planner.unlinked-recipes-hint', { count: unlinkedRecipeCount })` when count > 0

- **Right panel** (`v-col cols="12" md="4"`):
  - **ConfigPanel** with `:config`, `:slot-overlap-penalty="localSlotPenalty"`, `@update="onConfigUpdate"`, `@update-slot-penalty="onSlotPenaltyUpdate"`
  - **SuggestionSidebar** with `:scored-recipes`, `:recipe-data-map`, `:loading`, `:active-entry-type`, `:active-date`, `:slot-has-entries="activeSlotHasEntries"`

**Local state**:
- `activeEntryTypes: Ref<PlanEntryType[]>` — default `["breakfast", "lunch", "dinner"]`
- `localSlotPenalty: Ref<number>` — default `0.7`, updated via ConfigPanel
- `activeEntryType` and `activeDate` — computed from activeSlotKey by splitting on "|"
- `activeSlotHasEntries` — computed: checks if activeSlotKey's entries array is non-empty

**Event handlers**:
- `onSlotClick(date, entryType)`: Call `setActiveSlot("${date}|${entryType}")`. This triggers complement scoring update in the composable.
- `onSlotDrop(date, entryType, recipeId)`: Validate recipeId exists in recipeDataMap, then call `addToDraft(date, entryType, recipeId)`.
- `onEntryRemove(slotKey, localId)`: Call `removeFromDraft(slotKey, localId)`.
- `onRecipeSelect(recipeId)`: If activeSlotKey is set, add recipe to that slot via `addToDraft`. The composable determines order (0 if first, N if complement).
- `onConfigUpdate(config)`: Call `updateConfig(config)`.
- `onSlotPenaltyUpdate(value)`: Update `localSlotPenalty`. Update the scoring engine's weights by calling `updateConfig` or directly setting weights on the scoring composable (the composable should expose a way to update the client-side slotOverlapPenalty weight without a backend call).
- `onSavePlan()`: Call `savePlan()`. If `error` is null after, show success snackbar.

**Unsaved changes guard**: Import `onBeforeRouteLeave` from `vue-router`. Add guard:
```typescript
onBeforeRouteLeave((_to, _from, next) => {
  if (hasUnsavedChanges.value) {
    const answer = window.confirm(t("optimizer.planner.unsaved-changes"));
    next(answer);
  } else {
    next();
  }
});
```
This uses the existing i18n key. Pattern exists in the codebase at `frontend/app/pages/g/[groupSlug]/r/create/url.vue`.

**Lifecycle**: Call `loadData()` on mount (`onMounted`).

**Date range watcher**: Watch `dateRange` and call `loadData()` when it changes (to reload meal plan entries for new range).

**File location**: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue`
</context>

<subtasks>
- [ ] Create file with template, script setup, and scoped styles
- [ ] Import all required components (PlanGrid, SuggestionSidebar, ConfigPanel)
- [ ] Import and destructure useOptimizerPlanner() including `error` ref
- [ ] Set up useSeoMeta with i18n title
- [ ] Implement two-panel layout with v-container/v-row/v-col
- [ ] Implement date range picker (v-menu + v-date-picker with multiple="range") following existing planner.vue:9-62 pattern
- [ ] Add v-alert for error display when error ref is non-null
- [ ] Wire PlanGrid with all props and event handlers (multi-entry aware)
- [ ] Wire SuggestionSidebar with all props including slotHasEntries
- [ ] Wire ConfigPanel with config, slotOverlapPenalty, and both update handlers
- [ ] Implement all event handlers (onSlotClick → setActiveSlot, onSlotDrop, onEntryRemove with localId, onRecipeSelect, onConfigUpdate, onSlotPenaltyUpdate, onSavePlan)
- [ ] Implement action buttons (Save Plan with loading/disabled states, Generate Shopping List, Clear All)
- [ ] Implement unsaved changes navigation guard with onBeforeRouteLeave and window.confirm
- [ ] Call loadData() on mount
- [ ] Add loading overlay/progress while loading
</subtasks>

<acceptance>
- Page renders at `/g/{groupSlug}/optimizer/planner`
- Two-panel layout: grid on left, sidebar on right
- Date range picker works and triggers data reload
- Error alert visible when API calls fail
- Clicking empty slot highlights it and sidebar shows "Suggestions for..."
- Clicking slot with entries highlights it and sidebar shows "Complement for..."
- Dropping recipe from sidebar into empty slot adds as primary (order 0)
- Dropping recipe into slot with entries adds as complement (order N)
- Clicking recipe in sidebar when slot is active adds it appropriately
- Remove button removes specific entry by localId
- Save Plan button calls savePlan and shows success feedback
- Config panel changes (including slot penalty) trigger scoring recalculation
- Loading state shown while data loads
- Navigation guard prompts on unsaved changes: verified by adding a recipe, then navigating away (browser confirm dialog appears)
</acceptance>

<rollback risk="medium">
New file — delete to rollback.
</rollback>
</task>

### 4.1b Add Shopping List Dialog Integration

<task id="4.1b" status="pending" depends="4.1a" risk="medium">
<context>
Add shopping list dialog integration to the planner page. This is separated because the RecipeDialogAddToShoppingList component requires full Recipe objects (not RecipeFoodData), necessitating an on-demand data fetch.

**The challenge**: `RecipeDialogAddToShoppingList` accepts `RecipeWithScale[]` where `RecipeWithScale extends Recipe { scale: number }`. The planner composable only has `RecipeFoodData` (lightweight projection). Full Recipe objects must be fetched on demand.

**API method**: `api.recipes.getOne(slug)` — confirmed. RecipeAPI extends BaseCRUDAPI with `itemRoute = routes.recipesRecipeSlug` which takes a slug string. Returns `RequestResponse<Recipe>`.

**Implementation**:
- Add import: `import RecipeDialogAddToShoppingList from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";`
- Add local state:
  ```typescript
  const shoppingListDialog = ref(false);
  const shoppingListRecipes = ref<any[]>([]);
  const shoppingLists = ref<ShoppingListSummary[]>([]);
  const shoppingListLoading = ref(false);
  ```
- Add the dialog component in the template:
  ```html
  <RecipeDialogAddToShoppingList
    v-if="shoppingLists.length"
    v-model="shoppingListDialog"
    :recipes="shoppingListRecipes"
    :shopping-lists="shoppingLists"
  />
  ```
- Implement `onGenerateShoppingList()` using **parallel fetches** (not sequential):
  ```typescript
  async function onGenerateShoppingList() {
    const recipeIds = [...plannedRecipeIds.value]; // deduplicated Set
    if (recipeIds.length === 0) {
      // Show toast: "No recipes in the plan yet"
      return;
    }
    shoppingListLoading.value = true;

    // Fetch all recipes in parallel (not sequentially!)
    const slugs = recipeIds
      .map(id => recipeDataMap.value.get(id)?.slug)
      .filter((s): s is string => !!s);

    const recipeResults = await Promise.all(
      slugs.map(slug => api.recipes.getOne(slug))
    );
    const recipes = recipeResults
      .filter(r => r.data)
      .map(r => ({ ...r.data!, scale: 1 }));

    shoppingListRecipes.value = recipes;

    const { data } = await api.shopping.lists.getAll(1, -1, {
      orderBy: "name", orderDirection: "asc",
    });
    if (data) shoppingLists.value = data.items as ShoppingListSummary[] ?? [];
    shoppingListDialog.value = true;
    shoppingListLoading.value = false;
  }
  ```

**Note**: `api.recipes` is available from `useUserApi()`. The API is at `frontend/app/lib/api/user/recipes/recipe.ts:93`.
</context>

<subtasks>
- [ ] Import RecipeDialogAddToShoppingList component
- [ ] Import ShoppingListSummary type
- [ ] Add shoppingListDialog, shoppingListRecipes, shoppingLists, shoppingListLoading refs
- [ ] Add RecipeDialogAddToShoppingList to template with v-model and props
- [ ] Implement onGenerateShoppingList() — fetch full recipes using **Promise.all** (parallel, not sequential) and shopping lists
- [ ] Wire "Generate Shopping List" button to onGenerateShoppingList with loading state
- [ ] Handle edge case: no planned recipes → show toast `$t('optimizer.planner.no-planned-recipes')` instead of opening empty dialog
</subtasks>

<acceptance>
- Clicking "Generate Shopping List" with no recipes shows toast, does not open dialog
- Clicking "Generate Shopping List" with recipes fetches full recipe data using Promise.all (verify: network tab shows parallel requests, not sequential)
- RecipeDialogAddToShoppingList opens with correct recipe data
- Shopping lists are fetched and displayed in the dialog
- Loading indicator shows while fetching
- All planned recipes across all slots are included (deduplicated)
</acceptance>

<rollback risk="medium">
Revert changes to planner.vue (remove dialog import, state, template element, and handler). The page itself remains functional without the shopping list feature.
</rollback>
</task>

### 4.2 Add Sidebar Navigation Link

<task id="4.2" status="pending" depends="4.1a" risk="low">
<context>
Add the optimizer planner link to the sidebar navigation in `frontend/app/components/Layout/DefaultLayout.vue`.

**Current state**: The `topLinks` computed array contains sidebar links. The Pantry link is at approximately lines 249-254:
```typescript
{
  icon: $globals.icons.pantry,
  title: "Pantry",
  to: `/g/${groupSlug.value}/optimizer/pantry`,
  restricted: true,
},
```

The Timeline link follows immediately after.

**Change**: Insert a new link AFTER the Pantry link and BEFORE the Timeline link:
```typescript
{
  icon: $globals.icons.calendarWeek,
  title: i18n.t("optimizer.planner.title"),
  to: `/g/${groupSlug.value}/optimizer/planner`,
  restricted: true,
},
```

This is a modification to an upstream file (listed in CLAUDE.md as a known upstream touch point). The Pantry link already establishes the pattern for optimizer links here.
</context>

<subtasks>
- [ ] Open `frontend/app/components/Layout/DefaultLayout.vue`
- [ ] Locate the Pantry link entry
- [ ] Insert the new planner link immediately after the Pantry entry and before the Timeline entry
- [ ] Use `$globals.icons.calendarWeek` for the icon
- [ ] Use `i18n.t("optimizer.planner.title")` for the title
- [ ] Use `` `/g/${groupSlug.value}/optimizer/planner` `` for the `to` path
- [ ] Set `restricted: true`
</subtasks>

<acceptance>
- Planner link appears in sidebar between Pantry and Timeline
- Link icon is calendarWeek
- Link text shows "Meal Planner" (from i18n)
- Link navigates to `/g/{groupSlug}/optimizer/planner`
- Link is restricted (only visible to logged-in users)
- No other sidebar links were modified
- TypeScript compiles without errors
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] Page loads at `/g/{groupSlug}/optimizer/planner` without errors
- [ ] Sidebar shows "Meal Planner" link between Pantry and Timeline
- [ ] Date range picker works and reloads data
- [ ] Error alert shows when API calls fail
- [ ] Empty grid slots are clickable and accept drops (adds as primary, order 0)
- [ ] Slots with a primary accept additional drops (adds as complement, order N)
- [ ] Sidebar context hint changes between "Suggestions for..." and "Complement for..." based on slot state
- [ ] Recipe cards in sidebar are draggable onto grid slots
- [ ] Complement scoring: after placing a primary, sidebar rankings shift to favor complementary recipes
- [ ] Filled slots show primary and complement entries with visual hierarchy
- [ ] Remove button on individual entries works (removes by localId)
- [ ] Save Plan creates/updates/deletes entries via API (handles multi-entry slots)
- [ ] Config panel sliders (including Complement Contrast) update scoring in real-time
- [ ] Generate Shopping List opens dialog with all planned recipes (deduplicated, fetched in parallel)
- [ ] Search filter in sidebar works
- [ ] Navigation guard prompts on unsaved changes
</verification>
<gate>The complete planner page is functional with multi-entry slots and complement-aware scoring. Users can build meal plans, save them, and generate shopping lists. Error handling and navigation guards are in place.</gate>
</checkpoint>

</phase>

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="high">
  <description>savePlan() creates/deletes wrong meal plan entries due to diff logic bug</description>
  <mitigation>Draft model isolates all changes until explicit save. Save logic diffs per-entry using existingEntryId for existing and localId for new. Re-loads from API after save to re-sync.</mitigation>
  <detection>After saving, verify entries in upstream mealplan planner view. If entries are duplicated or missing, the diff logic has a bug.</detection>
</risk>
<risk id="R2" likelihood="medium" impact="low">
  <description>Vuetify 4 v-slider thumb-label="always" prop may not work as expected</description>
  <mitigation>Fall back to thumb-label (boolean) if "always" is not supported. Test in dev server.</mitigation>
  <detection>Slider renders without thumb labels. Check browser console for Vuetify prop warnings.</detection>
</risk>
<risk id="R3" likelihood="medium" impact="low">
  <description>Native HTML drag-and-drop does not work on mobile/touch devices</description>
  <mitigation>Desktop-first scope for v1. Click-to-add (via sidebar select + active slot) works on all devices as a fallback. Touch drag support can be added later with a polyfill or vue-draggable-plus.</mitigation>
  <detection>Test on mobile browser — drag from sidebar fails. Click-to-add should still work.</detection>
</risk>
<risk id="R4" likelihood="low" impact="medium">
  <description>Large number of parallel recipe fetches in shopping list generation overwhelms the API</description>
  <mitigation>For v1, Promise.all is acceptable for typical meal plans (10-20 unique recipes). If performance is an issue, chunk into batches of 5.</mitigation>
  <detection>Shopping list generation takes >5 seconds or returns errors. Add chunking if observed.</detection>
</risk>
<risk id="R5" likelihood="low" impact="medium">
  <description>DateRange import collision: both use-group-mealplan.ts and use-optimizer-planner.ts export DateRange</description>
  <mitigation>use-optimizer-planner.ts imports DateRange from use-group-mealplan.ts and re-exports it. No new definition. Consumers import from whichever module is more natural.</mitigation>
  <detection>TypeScript compilation errors about ambiguous DateRange imports.</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] TypeScript compiles: `cd frontend && npx nuxi typecheck`
- [ ] ESLint passes for all new/modified files: `cd frontend && npx eslint app/composables/optimizer/use-optimizer-planner.ts app/components/optimizer/*.vue app/pages/g/\\[groupSlug\\]/optimizer/planner.vue`
- [ ] Existing scoring engine tests pass: `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts`
- [ ] Frontend dev server starts without errors: `task ui`
- [ ] Page loads at `/g/{groupSlug}/optimizer/planner` in browser
- [ ] Full flow: select date range → see suggestions → drag entree to slot → sidebar shifts to complement suggestions → drag side to same slot → save → verify in upstream mealplan view (both entries appear)
- [ ] Complement scoring: placing a chicken dinner as primary should deprioritize other chicken dishes and promote vegetable sides
- [ ] Config changes (including Complement Contrast slider) persist across page reload (backend weights) / are applied (client-side slot penalty)
- [ ] Shopping list generation includes all entries from all slots (deduplicated), fetches in parallel
- [ ] Error handling: disconnect network → trigger save → error alert appears, state is not corrupted
- [ ] Navigation guard: add recipe → navigate away → browser confirm dialog appears
- [ ] No regressions: existing Pantry page still works, existing Mealplan planner still works
- [ ] Sidebar navigation shows all expected links in correct order
</verification>
<acceptance>The optimizer planner page is fully functional with multi-entry slots and complement-aware scoring. Users can build meal plans with entrees and complementary sides, receiving contextually relevant suggestions at each step. Error handling and navigation guards protect user work. All code follows fork isolation rules. No regressions in existing functionality.</acceptance>
</final_validation>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-14-055009-optimizer-ui.md">
  <question>Should the grid show all 7 entry types by default, or a configurable subset?</question>
  <default_assumption>Show breakfast, lunch, and dinner by default. Extensibility (add row control) is a future enhancement — v1 defaults to 3 rows.</default_assumption>
  <impact>Affects grid height and usability. Current implementation hardcodes 3 entry types.</impact>
</question>
<question id="Q3" blocking="false" owner="human">
  <question>Should the slotOverlapPenalty weight be persisted to the backend OptimizerConfig, or remain client-side only?</question>
  <default_assumption>Client-side only for v1 (default 0.7). Backend persistence can be added in a future migration when the optimizer config schema is next updated.</default_assumption>
  <impact>If client-side only, the complement contrast setting resets on page reload. If persisted, requires a backend migration to add the column.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/plans/2026-04-14-060214-optimizer-ui.md">
<resolved original_question="Q2: What Recipe API method should be used to fetch full recipe data for the shopping list dialog?">
  <resolution>Confirmed: `api.recipes.getOne(slug)` is the correct method. RecipeAPI extends BaseCRUDAPI with `itemRoute = routes.recipesRecipeSlug` which takes a slug string. getOne is inherited from BaseCRUDAPIReadOnly at base-clients.ts:53.</resolution>
</resolved>
</resolved_from_source>

<resolved_from_source source="docs/specs/2026-04-14-055009-optimizer-ui.md">
<resolved original_question="Should there be an undo/redo for draft changes?">
  <resolution>No undo/redo. Draft changes are lightweight — Clear Slot and Clear All buttons are sufficient. The draft model provides protection against accidental saves.</resolution>
</resolved>
<resolved original_question="How should the page handle the case where Stage A endpoints are not deployed yet?">
  <resolution>Show error alert with clear message if API calls fail. The error ref in the composable surfaces API failures to the UI.</resolution>
</resolved>
<resolved original_question="Should clicking an empty slot auto-fill with the top suggestion, or just highlight it?">
  <resolution>Highlight only. Clicking sets the slot as active, sidebar updates context hint, user explicitly selects a recipe.</resolution>
</resolved>
<resolved original_question="Does the backend enforce a uniqueness constraint on (date, entryType) for meal plan entries?">
  <resolution>No. Confirmed: GroupMealPlan model has no UniqueConstraint. Multiple entries per date+entryType are allowed by design.</resolution>
</resolved>
</resolved_from_source>
