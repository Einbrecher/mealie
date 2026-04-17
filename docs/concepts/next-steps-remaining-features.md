# Next Steps: Remaining Feature Stages

## Current State (as of 2026-04-13)

**Complete:**
- Phase 1 (Foundation) — fork, CI pipeline, directory structure, isolation rules
- Phase 2 (Pantry Tracker) — full stack: model, migration, service with 7-rule deficit calculator, CRUD API, frontend page, tests, i18n, sidebar nav
- Shopping list pantry auto-check — integrated at `shopping_lists.py:178-184`, auto-adjusts quantities on list creation

**Remaining work** falls into four stages, ordered by dependency and user value.

---

## Stage A: Optimizer Foundation (Backend + Scoring Engine)

### Rationale

The scoring engine is the heart of the optimizer. Building it as a standalone, tested TypeScript module before any UI work forces early discovery of data shape constraints and performance characteristics. The config API is trivial backend work but defines the canonical weight schema that the scorer consumes — build it first.

### Scope

#### A1. Optimizer Config API (backend)

New model, schema, controller, and migration for per-household optimizer preferences.

| Layer | File | Details |
|-------|------|---------|
| Model | `mealie/db/models/optimizer/config.py` | `OptimizerConfigModel` — one row per household |
| Schema | `mealie/schema/optimizer/config.py` | Pydantic: `OptimizerConfigOut`, `OptimizerConfigUpdate` |
| Controller | `mealie/routes/optimizer/controller_config.py` | `GET/PUT /households/optimizer/config` |
| Migration | `mealie/alembic/versions/xxxx_add_optimizer_config.py` | New table, no upstream changes |

Config fields (all with sensible defaults):
- `overlap_weight: float = 1.0` — ingredient overlap importance
- `pantry_utilization_weight: float = 0.6` — boost recipes using pantry inventory
- `pantry_urgency_weight: float = 0.8` — boost recipes using perishable/expiring pantry items
- `protein_diversity_weight: float = 0.5` — penalize same-protein streaks
- `category_balance_weight: float = 0.3` — encourage cuisine/type variety
- `rating_weight: float = 0.2` — prefer highly-rated recipes
- `prep_time_budget_minutes: int | None` — optional per-meal time cap

Frontend API client follows the proven `BaseCRUDAPI` pattern from `optimizer-pantry.ts`, registered in `client-user.ts`.

#### A2. Pantry Use-Priority Field (model enhancement)

Add a `use_priority` field to `PantryItemModel` to support de minimis vs. use-it-up classification.

| Layer | File | Details |
|-------|------|---------|
| Migration | `mealie/alembic/versions/xxxx_add_pantry_use_priority.py` | Add column to existing `pantry_items` table |
| Model | `mealie/db/models/optimizer/pantry.py` | Add `use_priority` column |
| Schema | `mealie/schema/optimizer/pantry.py` | Add field to Create/Update/Out schemas |

**Values**: `"auto"` (default) | `"high"` | `"low"`

- `"auto"` — derive priority from the food's label + expiration date (zero config required)
- `"high"` — user override: always treat as "use this up" (e.g., fresh basil marked manually)
- `"low"` — user override: de minimis, don't prioritize (e.g., dried greek seasoning)

**Auto-derivation logic** (when `use_priority == "auto"`):
1. If `expiration_date` is within 5 days → `"high"` (regardless of label)
2. If food label is perishable (Vegetables & Greens, Fruits, Dairy & Eggs, Meats, Poultry, Fish, Herbs & Spices, etc.) → `"high"`
3. If food label is shelf-stable (Seasonings & Spice Blends, Oils & Fats, Baking, Canned Food, Grains, Pasta, etc.) → `"low"`
4. Unknown label → `"high"` (safe default: better to suggest using it than to ignore it)

**Why this design**: Most users never touch the field — `"auto"` does the right thing using label and expiration data that already exists. The override handles edge cases like "I have dried oregano (shelf-stable, low priority) vs. fresh oregano (perishable, high priority)" where the food label alone is ambiguous. Three values, not a boolean, because `"auto"` is the critical third state that eliminates configuration burden.

**Frontend**: Add a priority selector to `PantryItemRow.vue` — a small chip/toggle that defaults to "Auto" and lets users override to "Use up" or "Low priority" when they want to.

#### A3. Recipe-Foods Projection Endpoint (backend)

**Key architectural insight**: `RecipeSummary` does not include ingredients. Fetching 200+ full `Recipe` objects for client-side scoring is expensive. A lightweight projection endpoint solves this.

| Layer | File | Details |
|-------|------|---------|
| Controller | `mealie/routes/optimizer/controller_recipes.py` | `GET /households/optimizer/recipe-foods` |
| Schema | `mealie/schema/optimizer/recipe_projection.py` | `RecipeFoodProjection` — `{recipe_id, slug, name, food_ids: list[UUID], category_ids, tag_ids, rating, total_time, last_made}` |

Implementation is a read-only query against existing `recipes_ingredients` and `recipe_ingredient` tables — no new tables, no upstream changes. Returns only the fields the scorer needs.

**Why not fetch full recipes?** With 200 recipes, the full payload could be 2-5 MB. The projection is ~50 KB. This matters on mobile/tablet (the kitchen use case).

#### A4. Scoring Engine (frontend, framework-agnostic)

Pure TypeScript module with no Vue/Nuxt dependencies, fully unit-testable.

```
frontend/app/composables/optimizer/
  scoring-engine.ts          # pure functions, no framework deps
  scoring-engine.test.ts     # unit tests
  types.ts                   # ScoringWeights, OverlapResult, RecipeFoodData, PantryMatchDetail
  use-optimizer-scoring.ts   # thin Vue composable wrapper
```

**Composite scoring formula:**
```
total_score(candidate) =
    w_overlap   * overlap_score(candidate, planned_recipes)
  + w_pantry    * pantry_coverage_score(candidate, pantry_map)
  + w_urgency   * pantry_urgency_score(candidate, pantry_map)
  + w_diversity * protein_diversity_score(candidate, planned_recipes)
  + w_balance   * category_balance_score(candidate, planned_recipes)
  + w_rating    * normalized_rating(candidate)
  + w_preptime  * prep_time_score(candidate)
```

**Factor 1 — Ingredient overlap** (existing spec):
```
overlap_score(candidate, planned) =
    |candidate.food_ids ∩ all_planned_food_ids| / |candidate.food_ids|
```

**Factor 2 — Pantry coverage** (new):
Fraction of the recipe's ingredients that are in the pantry with tracked quantities (excludes `assume_enough` staples and expired items). This gives a mild boost to recipes that use what you already have, regardless of priority.
```
pantry_coverage_score(candidate, pantry_map) =
    |candidate.food_ids ∩ non_staple_non_expired_pantry_food_ids| / |candidate.food_ids|
```
De minimis items (dried greek seasoning, shelf-stable goods) contribute here — "it's nice that the recipe uses what we have" — but don't trigger urgency.

**Factor 3 — Pantry urgency** (new):
Counts only high-priority pantry matches (perishables, items nearing expiration), weighted by expiration proximity. This is the "use up the cilantro" signal.
```
pantry_urgency_score(candidate, pantry_map) =
    (matched_urgent_count / candidate.food_ids.length)
    * avg(expiration_multiplier for each matched urgent item)
```

Expiration multiplier tiers (discrete, not continuous — home-tracked dates don't warrant smooth curves):
| Days to expiry | Multiplier |
|----------------|------------|
| 7+ or no date  | 1.0        |
| 3–6 days       | 1.5        |
| 1–2 days       | 2.0        |
| Today/expired  | 2.5        |

The multiplier applies within the urgency score only, so it can't overwhelm other factors. A recipe using cilantro expiring tomorrow gets an urgency boost, but it can't outrank a recipe that's better on every other dimension.

**Factors 4–7** (from original spec):
- Protein diversity: penalize if candidate shares primary protein tag with N+ existing plan entries
- Category balance: bonus for underrepresented categories in current plan
- Rating boost: scale by `recipe.rating / 5.0`
- Prep time filter: exclude recipes exceeding `prep_time_budget_minutes`

**Score breakdown for UI annotations:**
The scoring engine returns a `ScoredRecipe` object with both the total score and a breakdown, plus pantry match details for human-readable display:
```typescript
interface ScoredRecipe {
  recipeId: string;
  totalScore: number;
  breakdown: Record<string, number>;  // { overlap: 0.6, pantryCoverage: 0.8, pantryUrgency: 0.4, ... }
  pantryMatches: PantryMatchDetail[];  // for UI annotation chips
}

interface PantryMatchDetail {
  foodName: string;
  priority: "high" | "low";         // effective priority (after auto-resolution)
  daysToExpiry: number | null;
}
```

The UI renders `pantryMatches` as annotation chips on recipe cards:
```
[Chicken Cilantro Tacos]  ★ 4.5  |  30 min
Uses 3 pantry items  ·  Cilantro expires tomorrow  ·  72% ingredient overlap
```

This gives the user's wife the "why" without exposing scoring weights — she sees "cilantro expires tomorrow" and thinks "oh right, I should use that up."

**Data flow for pantry-aware scoring:**
1. Fetch `GET /households/optimizer/recipe-foods` once → `recipeId → foodIds[]` map
2. Fetch pantry items once (already loaded by pantry composable) → `foodId → PantryItem` map with `use_priority` and `expiration_date`
3. Resolve `effective_priority` for each pantry item (auto → high/low using label + expiration)
4. For each candidate recipe, compute all factors using set intersections against both maps

Two queries total, O(candidates × avg_ingredients) set lookups. No additional endpoint changes needed — pantry data is fetched separately from recipe data.

**Edge cases to test:**
- Recipes with zero linked ingredients (no `food_id` on any ingredient) — skip from scoring, surface separately
- Zero planned recipes (cold start) — return all recipes sorted by rating + pantry urgency
- Identical food sets — 100% overlap, should rank highest
- All pantry items are `assume_enough` staples — pantry coverage and urgency scores are 0 for all recipes (no differentiation, which is correct)
- Recipe uses only de minimis pantry items — coverage score is nonzero, urgency score is 0
- Performance with 500 recipes — profile and determine if web worker is needed

**Data constraint**: `food_id` is nullable on `RecipeIngredientModel`. Ingredients without food references cannot participate in overlap or pantry scoring. The projection endpoint excludes them, and the UI surfaces an "N recipes have unlinked ingredients" hint.

### Dependencies
- Pantry Tracker (complete) — the scoring engine consumes the pantry map and `use_priority` field
- Existing recipe/food/label models (read-only) — for the projection endpoint and auto-derivation logic

### Outputs
- Config API with migration (includes pantry utilization + urgency weights)
- `use_priority` field on `PantryItemModel` with migration and frontend controls
- Recipe-foods projection endpoint
- Tested scoring engine with pantry-aware factors and score breakdown
- TypeScript types for all optimizer data shapes

---

## Stage B: Optimizer UI

### Rationale

With the scoring engine tested and the data pipeline proven, this stage builds the interactive planning interface. It's the largest single stage — the plan grid, suggestion sidebar, recipe cards, and the save-to-meal-plan flow.

### Scope

#### B1. Plan Grid Page

| File | Details |
|------|---------|
| `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` | Main page with week grid + suggestion sidebar |

**Layout**: Two-panel design.
- **Left panel**: 7-day grid (or configurable date range) with entry-type rows (breakfast, lunch, dinner, etc.). Each cell is a droppable slot. Clicking a slot opens the suggestion sidebar filtered to that meal type.
- **Right panel / sidebar**: Ranked recipe suggestions with overlap scores. Updates reactively as recipes are added to the plan.

**Interaction flow:**
1. User picks a date range (defaults to next 7 days)
2. Any existing meal plan entries for that range load into the grid
3. Suggestion sidebar shows recipes ranked by the scoring engine
4. User clicks/drags a recipe into a slot — scoring recalculates for remaining slots
5. "Save Plan" writes entries via existing `POST /households/mealplans` (one entry per slot)
6. "Generate Shopping List" calls existing `add_recipe_ingredients_to_list` — pantry auto-check applies automatically

**Existing API integration** (no new backend work):
- Meal plan CRUD: `api.mealplans.createOne()` / `updateOne()` / `deleteOne()`
- Recipe fetch: `GET /households/optimizer/recipe-foods` (from Stage A)
- Shopping list: `POST /households/shopping/lists` then `add_recipe_ingredients_to_list`
- Entry types: reuse `PlanEntryType` enum (breakfast, lunch, dinner, side, snack, drink, dessert)

#### B2. Components

| Component | Details |
|-----------|---------|
| `optimizer/PlanGrid.vue` | Week grid with draggable slots, renders `PlanEntryType` rows |
| `optimizer/PlanSlot.vue` | Individual meal slot — shows recipe thumbnail + name, or empty drop target |
| `optimizer/SuggestionSidebar.vue` | Scrollable ranked list, search/filter, recipe cards |
| `optimizer/RecipeCard.vue` | Compact card: name, image, overlap % badge, rating, prep time, pantry match chips (e.g., "Cilantro expires tomorrow") |
| `optimizer/ConfigPanel.vue` | Weight sliders wired to `GET/PUT /optimizer/config`, collapsible |

#### B3. Composable

| File | Details |
|------|---------|
| `frontend/app/composables/optimizer/use-optimizer-planner.ts` | Orchestrates grid state, scoring calls, meal plan API, shopping list generation |

Follows the pattern of `use-group-mealplan.ts` — wraps API calls in reactive actions, manages local draft state before save.

#### B4. Navigation

Add optimizer planner link to sidebar in `DefaultLayout.vue` (already a known upstream modification point). Icon + title, restricted to logged-in users.

#### B5. i18n

Add English keys under `optimizer.planner.*` namespace in `en-US.json`.

### Dependencies
- Stage A (scoring engine, config API, recipe-foods endpoint)
- Existing meal plan API (no changes needed)
- Existing shopping list API (pantry auto-check already integrated)

### Outputs
- Functional meal plan builder with ingredient-overlap suggestions
- Config panel for tuning scoring weights
- Shopping list generation from optimized plan

---

## Stage C: Shopping List Enhancements

### Rationale

These features complete the pantry-to-shopping-list loop. They are independent of the optimizer — a user benefits from them even when building meal plans manually. Sequenced after the optimizer because the optimizer is the headline feature and delivers more user value sooner.

**Key insight from codebase exploration**: The existing `find_matching_label()` method in `shopping_lists.py` already assigns labels from foods to shopping items during bulk creation. The "auto-section" enhancement the spec calls for may already be largely working — needs verification before building anything new.

### Scope

#### C1. Verify Auto-Section Assignment

Before building anything, verify what `find_matching_label()` (shopping_lists.py:145-152) already does:
- Does it reliably assign `food.label_id` to new shopping list items?
- Do labels map to sections in the frontend via `use-shopping-list-labels.ts`?
- If this already works, the spec item is done. If gaps exist, document and fix them.

#### C2. Deficit Visualization on Shopping Lists (frontend)

The `POST /households/optimizer/pantry/deficit` endpoint already exists. Add a UI element to the shopping list page showing pantry coverage:
- Badge or indicator on items that are partially covered by pantry
- "Pantry notes" already added by `check_shopping_items()` — ensure they render clearly
- Optional: summary banner showing "X of Y items covered by pantry"

This is a read-only UI addition to the existing shopping list page — one of the few touches to an upstream page.

#### C3. Deduct-on-Checkout + Quick-Add-to-Pantry

These are two sides of the same user interaction: checking off a shopping list item.

**Deduct from pantry**: When items are checked off, offer to deduct purchased quantities from pantry (for items being replenished). Backend: new endpoint or extend `POST /households/optimizer/pantry/deduct` to accept shopping list item IDs instead of recipe IDs.

**Quick-add to pantry**: When checking off an item that isn't in the pantry, offer to add it. Pre-fills food, quantity, and unit from the shopping list item. This bridges the "I bought it, now track it" gap.

Both features should be opt-in (confirmation dialog or toggle) to avoid disrupting the simple check-off flow.

### Dependencies
- Pantry Tracker (complete)
- Existing shopping list page (upstream code, minimal modifications)

### Outputs
- Verified (or fixed) auto-section assignment
- Pantry coverage indicators on shopping lists
- Two-way pantry integration on item checkout

---

## Stage D: Polish & Onboarding

### Rationale

These items depend on other features existing and working. They improve the experience but don't add core functionality.

### Scope

#### D1. Expiration Warnings (Pantry)

The `expiration_date` field already exists on `PantryItemModel`. Add:
- Visual indicator on pantry items expiring within 3 days (configurable)
- Sort expired items to top of pantry list
- Optional: daily summary notification (if Mealie's notification system supports it)

**Note**: This could be pulled into Stage C or done as a standalone small PR at any time — no dependencies beyond the pantry page.

#### D2. First-Run Pantry Import Prompt

The `POST /import-on-hand` endpoint already exists. Add first-run detection to the pantry page:
- If pantry has 0 items and household has `ingredient_foods_on_hand` entries, show a prompt: "Import X items from your food list?"
- One-click import, then user refines (mark staples, set quantities)

#### D3. Mobile-Responsive Plan Grid

The optimizer planner grid (Stage B) needs to work on:
- Kitchen tablet (landscape, touch-friendly slot targets)
- Phone at the grocery store (primarily the shopping list, not the planner)

This requires the planner UI to exist first. Focus on touch target sizes, swipe gestures for date navigation, and collapsible sidebar.

#### D4. Onboarding Wizard (stretch)

Guided flow for new users:
1. Set up pantry (import from on-hand, mark staples)
2. Configure optimizer weights
3. Create first optimized meal plan
4. Generate shopping list

This depends on all three features being stable. It's a nice-to-have, not a requirement for the fork to be useful.

---

## Stage Summary

| Stage | Primary Feature | Backend Work | Frontend Work | Upstream Touches |
|-------|----------------|--------------|---------------|-----------------|
| **A** | Optimizer Foundation | Config model + migration, `use_priority` migration, recipe-foods endpoint | Scoring engine + tests, priority controls on pantry row | None |
| **B** | Optimizer UI | None (uses existing APIs) | Plan grid, sidebar, cards with pantry chips, config panel | `DefaultLayout.vue` (nav link) |
| **C** | Shopping Enhancements | Possibly extend deduct endpoint | Deficit viz, checkout integration | Shopping list page (minimal) |
| **D** | Polish | None | Expiration warnings, import prompt, mobile layout | None |

**Estimated progression**: A → B → C → D, though C can begin in parallel with B once Stage A is complete (no dependencies between B and C).

## Architectural Decisions

### Client-side scoring (confirmed)

The scoring engine stays entirely in TypeScript. Rationale:
- Latency: scoring must feel instant as users modify the plan grid
- Simplicity: no new backend services, background jobs, or caching
- The recipe-foods projection endpoint provides efficient data transfer (~50 KB vs 2-5 MB for full recipes)
- Escape hatch for performance: web worker, not server endpoint (scoring is pure and stateless)

### Pantry-aware scoring as separate factors (new)

Pantry utilization and pantry urgency are separate weighted factors in the scoring formula, not modifiers on the overlap score. Rationale:
- **Overlap and pantry measure different things.** Overlap = "share ingredients across planned meals to reduce shopping." Pantry = "use what you already own." A recipe can score high on overlap (shares onions with 3 other meals) but low on pantry (you don't have onions). They're orthogonal.
- **Two pantry factors, not one.** Coverage gives a mild boost to all non-expired pantry matches (including de minimis items like dried spices). Urgency gives a strong boost only to high-priority matches (perishables, items nearing expiration). This models the user's intuition exactly: "I don't need to go out of my way for greek seasoning, but I should use the cilantro."
- **Expiration proximity multiplier** uses discrete tiers (1.0 / 1.5 / 2.0 / 2.5) within the urgency factor only — it can't overwhelm the total score.

### De minimis via `use_priority` with auto-derivation (new)

A three-value field (`auto` / `high` / `low`) on `PantryItemModel`, defaulting to `auto`. Auto-derivation uses food labels (perishable categories → high, shelf-stable → low) and expiration proximity (≤5 days → high regardless of label). User can override for edge cases (dried vs. fresh oregano). This eliminates configuration burden — most users never touch the field.

### Recipe-foods projection endpoint (new)

Not in the original spec but architecturally necessary. `RecipeSummary` lacks ingredients, and fetching full `Recipe` objects for 200+ recipes is prohibitive on mobile. A lightweight `GET /households/optimizer/recipe-foods` returning `{recipe_id, food_ids[], category_ids[], rating, total_time}` keeps the frontend fast. Pantry data is fetched separately — no changes to this endpoint for pantry-aware scoring.

### Unlinked ingredient handling

`food_id` is nullable on `RecipeIngredientModel` — ingredients typed freeform without linking to the food dictionary can't participate in overlap or pantry scoring. The projection endpoint excludes them, and the UI surfaces "N recipes have unlinked ingredients" as a quality hint to encourage food linking.
