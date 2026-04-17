```yaml
spec_metadata:
  goal: "Fix all 17 findings from the optimizer implementation review (docs/reviews/2026-04-16-014250-optimizer-implementation.md) — 1 critical, 4 high, 7 medium, 5 low severity across backend pantry service, recipe projection, scoring engine, and frontend planner."
  constraints:
    - "All new code must stay in optimizer/ subdirectories per fork isolation rules"
    - "Modified upstream files must remain minimal — only shopping_lists.py, DefaultLayout.vue, and repository_generic.py are touched"
    - "No new Python dependencies — use functools, logging stdlib"
    - "Must not break existing scoring-engine tests (397 lines of vitest coverage)"
    - "Backend changes must be migration-free (no schema/model changes needed)"
  non_goals:
    - "Splitting PantryService into multiple services (Codex finding — accepted as appropriately scoped for fork)"
    - "Splitting useOptimizerPlanner composable (same rationale)"
    - "Adding server-side scoring boundary (client-side scoring is acceptable for personal fork)"
    - "Making deduction operations fully atomic/transactional (acceptable for personal use)"
    - "Implementing is_staple behavior or excludeExpired UI toggle (deferred — finding #8 and #16 are tracked but not addressed here)"
    - "Adding backend unit tests (noted as desirable but out of scope for this remediation)"
  timestamp: "2026-04-16T02:38:22"
  confidence: medium
  survey_consumed: false

current_state:
  summary: "The optimizer module is a well-layered fork addition (routes -> services -> repos -> models) with ~4500 lines across backend and frontend. The scoring engine has excellent test coverage. The main issues are: an N+1 query in deduction, unsafe unit handling with orphaned FKs, unbounded recipe projection endpoint, narrow time parsing, and in-place mutation in shopping list integration."
  relevant_files:
    - path: "mealie/services/optimizer/pantry.py"
      purpose: "Core pantry service — deficit calculation, deduction, shopping list integration, import"
      reuse_potential: high
    - path: "mealie/repos/optimizer/pantry.py"
      purpose: "Pantry repository with by_food_ids batch pattern"
      reuse_potential: high
    - path: "mealie/repos/repository_generic.py"
      purpose: "Base repository class — RepositoryGeneric and HouseholdRepositoryGeneric"
      reuse_potential: high
    - path: "mealie/services/optimizer/recipe_projection.py"
      purpose: "Recipe food projection service — loads all recipes with eager relationships"
      reuse_potential: medium
    - path: "mealie/routes/optimizer/controller_pantry.py"
      purpose: "Pantry REST endpoints"
      reuse_potential: low
    - path: "mealie/services/household_services/shopping_lists.py"
      purpose: "Upstream shopping list service — contains pantry integration try/except"
      reuse_potential: low
    - path: "frontend/app/composables/optimizer/scoring-engine.ts"
      purpose: "Client-side recipe scoring with weight-based ranking"
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/scoring-engine.test.ts"
      purpose: "397-line vitest suite covering all scoring functions"
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      purpose: "Planner composable — data loading, save orchestration, scoring coordination"
      reuse_potential: medium
    - path: "frontend/app/composables/optimizer/types.ts"
      purpose: "Shared TypeScript types for scoring engine"
      reuse_potential: high
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "API TypeScript types (auto-generated from Pydantic)"
      reuse_potential: low
    - path: "frontend/app/components/Layout/DefaultLayout.vue"
      purpose: "Main layout — nav links including optimizer section"
      reuse_potential: low
    - path: "frontend/app/lang/messages/en-US.json"
      purpose: "i18n translations — optimizer.pantry.title already exists at line 1486"
      reuse_potential: low
    - path: "mealie/services/parser_services/parser_utils/unit_utils.py"
      purpose: "UnitConverter class wrapping pint.UnitRegistry"
      reuse_potential: medium
  patterns_identified:
    - "Repository batch pattern: RepositoryPantryItem.by_food_ids uses filter().in_() for batch lookups"
    - "Running quantity tracking: deduct_recipe tracks running_qty dict, accumulates changes, persists at end"
    - "Pydantic model_copy: used elsewhere in Mealie for immutable data transformations"
    - "Module-level logger: Mealie services use get_logger(__name__) pattern"
    - "HouseholdRepositoryGeneric scoping: _filter_builder() automatically scopes queries to group+household"

gaps:
  exists:
    - component: "i18n key for pantry title"
      location: "frontend/app/lang/messages/en-US.json:1486"
      notes: "optimizer.pantry.title = 'Pantry' already defined — just need to use it in DefaultLayout.vue"
    - component: "Household scoping on shopping list items"
      location: "mealie/repos/repository_factory.py:317-325"
      notes: "group_shopping_list_item is HouseholdRepositoryGeneric — already scoped. Cross-household IDs return None from get_one. No additional controller check needed per Codex analysis."
    - component: "Batch fetch pattern"
      location: "mealie/repos/optimizer/pantry.py:17 (by_food_ids)"
      notes: "Existing IN() pattern to follow for new get_many method"
  partial:
    - component: "Time parsing"
      location: "frontend/app/composables/optimizer/scoring-engine.ts:10-29"
      missing: "Only handles 'X hour Y min' format. Needs ISO 8601 (PT1H30M), colon format (1:30), and variant text (90 minutes, 1.5 hours)"
    - component: "Unit guard in deduction"
      location: "mealie/services/optimizer/pantry.py:351-364, 420-441"
      missing: "When both unit_ids are None, need to check if either originally had a unit_id set to distinguish 'both unitless' from 'both units failed to load'"
    - component: "Deficit aggregation"
      location: "mealie/services/optimizer/pantry.py:65-244"
      missing: "Does not track running pantry quantity across duplicate food_ids in recipe ingredients"
    - component: "Save plan diff detection"
      location: "frontend/app/composables/optimizer/use-optimizer-planner.ts:392-393"
      missing: "Only compares recipeId — needs to also compare entryType and date"
    - component: "mapPantryToScoring typing"
      location: "frontend/app/composables/optimizer/use-optimizer-planner.ts:133-136"
      missing: "Uses 'any' type annotations — needs proper PantryItemOut[] input type"
  missing:
    - component: "get_many batch fetch on RepositoryGeneric"
      rationale: "No generic batch-by-ID method exists on the base repository. Needed to eliminate N+1 in deduct_shopping_items."
    - component: "Shared _deduct_items helper"
      rationale: "deduct_recipe and deduct_shopping_items share ~80% logic (running_qty, unit conversion, persist). Extracting avoids dual-maintenance."
    - component: "Module-level UnitConverter singleton"
      rationale: "Currently instantiated per-request, each creating a pint.UnitRegistry. Singleton avoids repeated parsing of unit definition files."

specification:
  files:
    # ── Finding #1 (critical) + #2 (high) + #6 (medium) + #14 (low): Backend pantry service ──
    - path: "mealie/repos/repository_generic.py"
      action: modify
      purpose: "Add generic batch-fetch method to base repository class"
      signature: |
        # Add to class RepositoryGeneric, after get_one():
        def get_many(
            self,
            values: Sequence[str | int | UUID4],
            key: str | None = None,
            override_schema: type | None = None,
        ) -> list[Schema]:
            """Batch-fetch multiple records by primary key or named column.
            Uses SQL IN() with tenant scoping from _filter_builder().
            Returns empty list for empty input. Order is NOT guaranteed to match input."""
            ...
      depends_on:
        - "collections.abc.Sequence (stdlib, already available)"
      acceptance_criteria:
        - "Empty input returns empty list without hitting DB"
        - "Uses _filter_builder() for tenant scoping (group/household)"
        - "Defaults key to self.primary_key"
        - "Returns list[Schema] with validated Pydantic models"
        - "Works for HouseholdRepositoryGeneric subclasses (inherits scoping)"

    - path: "mealie/services/optimizer/pantry.py"
      action: modify
      purpose: "Fix N+1 query, orphaned unit guard, deficit aggregation, extract shared deduction logic, singleton UnitConverter"
      signature: |
        # Module-level singleton (replaces per-request instantiation)
        _unit_converter = UnitConverter()

        class PantryService:
            def __init__(self, repos: AllRepositories) -> None:
                self.repos = repos
                self.pantry_items = repos.pantry_items
                self.converter = _unit_converter  # Use singleton

            def _deduct_items(
                self,
                food_qty_units: list[tuple[UUID4, float, object | None, UUID4 | None]],
                pantry_map: dict[UUID4, PantryItemOut],
            ) -> list[PantryItemOut]:
                """Shared deduction logic for both recipe and shopping item deduction.
                Each tuple is (food_id, quantity, unit_object_or_None, original_unit_id).
                Tracks running quantities, handles unit conversion, persists at end.
                Guards against orphaned unit FKs (both unit_ids None but original unit_id was set)."""
                ...

            def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
                """Normalize ingredients to (food_id, qty, unit, unit_id) tuples, delegate to _deduct_items."""
                ...

            def deduct_shopping_items(self, shopping_list_item_ids: list[UUID4]) -> list[PantryItemOut]:
                """Batch-fetch items via get_many, normalize to tuples, delegate to _deduct_items.
                Replaces per-item get_one loop (N+1 fix)."""
                ...

            def calculate_deficit(
                self,
                recipe_ingredients: list[RecipeIngredient],
                pantry_items: list[PantryItemOut] | None = None,
                exclude_expired: bool = False,
            ) -> PantryDeficitReport:
                """Aggregate ingredients by food_id before calculating deficit.
                Track running pantry quantity so duplicate food_ids accumulate correctly."""
                ...

            def check_shopping_items(
                self,
                items: list[ShoppingListItemCreate],
            ) -> list[ShoppingListItemCreate]:
                """Work on model_copy() of each item. Return new list — never mutate input."""
                ...
      depends_on:
        - "mealie/repos/repository_generic.py (get_many method)"
        - "mealie/services/parser_services/parser_utils/unit_utils.py (UnitConverter)"
      acceptance_criteria:
        - "deduct_shopping_items uses single batch query instead of N individual get_one calls"
        - "Orphaned unit FK guard: when both unit_ids are None but either original unit_id was set, skip deduction"
        - "calculate_deficit aggregates duplicate food_ids — second flour ingredient sees reduced pantry qty"
        - "check_shopping_items does not mutate input list items"
        - "UnitConverter instantiated once at module level, shared across all PantryService instances"
        - "_deduct_items consolidates shared logic — deduct_recipe and deduct_shopping_items are thin wrappers"

    # ── Finding #5 (high) + #12 (medium): Shopping list exception handling ──
    - path: "mealie/services/household_services/shopping_lists.py"
      action: modify
      purpose: "Log pantry integration errors instead of silently swallowing them"
      signature: |
        # Add at module level (follow Mealie pattern):
        from mealie.core.root_logger import get_logger
        logger = get_logger(__name__)

        # Replace bare except (around line 183):
        try:
            create_items = PantryService(self.repos).check_shopping_items(create_items)
        except Exception:
            logger.warning("Pantry check_shopping_items failed", exc_info=True)
      depends_on:
        - "mealie/core/root_logger.py (get_logger — existing utility)"
      acceptance_criteria:
        - "Pantry integration failures are logged with full traceback"
        - "Shopping list creation still succeeds when pantry integration fails"
        - "No behavior change for happy path"

    # ── Finding #3 (high): Recipe projection performance ──
    - path: "mealie/services/optimizer/recipe_projection.py"
      action: modify
      purpose: "Reduce query cost by selecting only needed columns instead of full ORM load. Defer caching to future iteration."
      signature: |
        class RecipeProjectionService:
            def get_all_recipe_food_projections(self) -> RecipeFoodProjectionResponse:
                """Optimize: select only (id, slug, name, rating, total_time) from RecipeModel
                instead of full ORM load. Keep selectinload for relationships that provide IDs.
                Note: full server-side caching deferred — cache key must include both
                group_id AND household_id due to per-household last_made values."""
                ...
      depends_on: []
      acceptance_criteria:
        - "Query selects only columns needed for RecipeFoodProjection (not full RecipeModel)"
        - "Response payload is identical to current implementation"
        - "Performance improvement measurable for 500+ recipe groups"

    # ── Finding #4 (high): Time parsing ──
    - path: "frontend/app/composables/optimizer/scoring-engine.ts"
      action: modify
      purpose: "Expand parseTimeToMinutes to handle common time formats"
      signature: |
        export function parseTimeToMinutes(totalTime: string | null): number | null {
          // Handles (in order):
          // 1. ISO 8601 durations: "PT1H30M", "PT45M", "PT2H"
          // 2. Colon format: "1:30", "0:45"
          // 3. Existing regex: "1 hour 30 min", "2 hours", "45 minutes"
          // 4. Decimal hours: "1.5 hours"
          // Returns null only if no format matches.
          ...
        }
      depends_on: []
      acceptance_criteria:
        - "Parses 'PT1H30M' -> 90"
        - "Parses 'PT45M' -> 45"
        - "Parses 'PT2H' -> 120"
        - "Parses '1:30' -> 90"
        - "Parses '0:45' -> 45"
        - "Parses '90 minutes' -> 90"
        - "Parses '1.5 hours' -> 90"
        - "Parses '1 hour 30 min' -> 90 (existing behavior preserved)"
        - "Returns null for truly unparseable strings"
        - "All existing scoring-engine tests still pass"
        - "New test cases added for each format"

    # ── Finding #17 (low): Overlap score clarification ──
    - path: "frontend/app/composables/optimizer/scoring-engine.ts"
      action: modify
      purpose: "Rename overlap weight to clarify that higher overlap = ingredient reuse = good"
      signature: |
        // In overlapScore function, add clarifying comment:
        // Higher score = more ingredient reuse with planned recipes (reduces shopping variety)
        // This is intentionally ADDED to total score — reuse is rewarded.
      depends_on: []
      acceptance_criteria:
        - "No behavior change — comment-only clarification"
        - "Existing tests unaffected"

    # ── Finding #9 (medium): Nav i18n ──
    - path: "frontend/app/components/Layout/DefaultLayout.vue"
      action: modify
      purpose: "Replace hardcoded 'Pantry' with i18n key"
      signature: |
        // Change:
        //   title: "Pantry",
        // To:
        //   title: i18n.t("optimizer.pantry.title"),
      depends_on:
        - "frontend/app/lang/messages/en-US.json (key exists at line 1486)"
      acceptance_criteria:
        - "Nav link displays 'Pantry' (unchanged visually)"
        - "Text is translatable via i18n system"

    # ── Finding #10 (medium) + #15 (low): Planner composable fixes ──
    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      action: modify
      purpose: "Fix savePlan diff detection and mapPantryToScoring typing"
      signature: |
        import type { PantryItemOut } from "~/lib/api/types/optimizer";
        import type { PantryItemScoring } from "./types";

        function mapPantryToScoring(items: PantryItemOut[]): PantryItemScoring[] {
          return items
            .filter((item) => item.foodId)
            .map((item) => ({ ... }));
        }

        // In savePlan diff detection (around line 393):
        // Change:
        //   if (snapEntry && snapEntry.recipeId !== draftEntry.recipeId)
        // To:
        //   if (snapEntry && (
        //     snapEntry.recipeId !== draftEntry.recipeId ||
        //     snapEntry.entryType !== draftEntry.entryType ||
        //     snapEntry.date !== draftEntry.date
        //   ))
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts (PantryItemOut)"
        - "frontend/app/composables/optimizer/types.ts (PantryItemScoring)"
      acceptance_criteria:
        - "mapPantryToScoring has proper TypeScript types — no 'any' annotations"
        - "Changing a meal's entryType (e.g., breakfast->lunch) triggers an update on save"
        - "Changing a meal's date triggers an update on save"
        - "No regression in create/delete detection"

    # ── Finding #11 (medium): Shopping item deduction validation ──
    # NOTE: Codex confirmed HouseholdRepositoryGeneric already scopes queries.
    # Cross-household IDs silently return None from get_one/get_many.
    # The real fix is making the batch fetch + validation explicit:
    - path: "mealie/services/optimizer/pantry.py"
      action: modify  # Already covered in pantry.py modifications above
      purpose: "In deduct_shopping_items: after batch fetch, log/warn if fetched count != requested count (indicates out-of-scope IDs)"
      signature: |
        def deduct_shopping_items(self, shopping_list_item_ids: list[UUID4]) -> list[PantryItemOut]:
            items = self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)
            # Items not found are silently filtered (household scoping).
            # This is acceptable — no error needed, just skip missing.
            ...
      depends_on: []
      acceptance_criteria:
        - "Cross-household item IDs are silently skipped (existing behavior preserved)"
        - "No 404 or error for missing IDs — graceful degradation"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/services/optimizer/pantry.py — fully read (605 lines), all methods understood"
    - "mealie/repos/optimizer/pantry.py — fully read, by_food_ids pattern documented"
    - "mealie/repos/repository_generic.py — read to line 50, get_one signature at 156-179, HouseholdRepositoryGeneric at 499"
    - "mealie/services/optimizer/recipe_projection.py — fully read (65 lines)"
    - "mealie/routes/optimizer/controller_pantry.py — fully read (100 lines)"
    - "mealie/services/household_services/shopping_lists.py — read lines 170-199"
    - "frontend/app/composables/optimizer/scoring-engine.ts — fully read (291 lines)"
    - "frontend/app/composables/optimizer/types.ts — fully read (48 lines)"
    - "frontend/app/composables/optimizer/use-optimizer-planner.ts — read lines 130-143, 340-419"
    - "frontend/app/lib/api/types/optimizer.ts — fully read (100 lines)"
    - "frontend/app/components/Layout/DefaultLayout.vue — searched, pantry nav at line 251"
    - "frontend/app/lang/messages/en-US.json — searched, optimizer.pantry.title at line 1486"
    - "mealie/services/parser_services/parser_utils/unit_utils.py — read class definition"
    - "mealie/repos/repository_factory.py — read group_shopping_list_item at 317-325"
  known_patterns:
    - "Repository batch IN(): see RepositoryPantryItem.by_food_ids — use _query().filter_by(**self._filter_builder()).filter(Model.col.in_(values))"
    - "Module logger: from mealie.core.root_logger import get_logger; logger = get_logger(__name__)"
    - "Pydantic copy: item.model_copy() for creating independent copies (Pydantic v2)"
    - "Running quantity tracking: dict[UUID4, float] keyed by food_id, modify in-memory, persist at end"
    - "i18n usage in DefaultLayout: i18n.t('optimizer.planner.title') pattern at line 257"
  decisions_made:
    - "No server-side caching for recipe projection yet: Codex noted cache key must include (group_id, household_id) and lru_cache on per-request instance is ineffective. Optimize the query first; add caching in a follow-up."
    - "No explicit error for cross-household shopping item IDs: HouseholdRepositoryGeneric already scopes queries, so cross-household IDs naturally return no results. Silent skip is acceptable."
    - "Overlap score direction is intentional: higher overlap = ingredient reuse = good (reduces shopping variety). Add comment, no behavior change."
    - "is_staple and excludeExpired are out of scope: findings #8 and #16 noted but not addressed in this remediation."
    - "get_many uses self.primary_key (not hardcoded 'id') per Codex recommendation for true genericity"
  warnings:
    - "get_many on RepositoryGeneric modifies a base class used across ALL of Mealie — test thoroughly"
    - "UnitConverter singleton: verify pint.UnitRegistry is thread-safe for concurrent reads (it is, but confirm)"
    - "scoring-engine.test.ts has 397 lines of tests — all must pass after parseTimeToMinutes changes"
    - "_deduct_items extraction must preserve exact behavior of both deduct_recipe and deduct_shopping_items including the unit conversion fallback paths"
    - "check_shopping_items model_copy: verify ShoppingListItemCreate has model_copy (Pydantic v2 BaseModel — it does)"

open_questions:
  - question: "Should parseTimeToMinutes return 0 instead of null for unparseable times? This would make the prep filter EXCLUDE unknown-time recipes (stricter). Current behavior lets them through."
    blocking: false
    default_assumption: "Keep returning null — don't penalize recipes with missing time data. This matches the current intent (prepTimeScore returns 1.0 for null)."
  - question: "Should recipe projection add pagination or is query optimization sufficient? For 2000+ recipes the response payload is still large."
    blocking: false
    default_assumption: "Optimize query first. The planner needs all recipes for client-side scoring, so pagination would require architectural changes to the scoring approach."
  - question: "Should deduct_shopping_items raise an error if some IDs were not found (cross-household), or silently skip?"
    blocking: false
    default_assumption: "Silently skip — consistent with existing behavior and HouseholdRepositoryGeneric scoping pattern."

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Codex identified 4 concerns:
    1. Cache for recipe projections must key on (group_id, household_id), not just group_id, due to per-household last_made values. lru_cache on per-request instance is ineffective. RESOLUTION: Defer caching; optimize query first.
    2. get_many on RepositoryGeneric must use self.primary_key (not hardcoded 'id') and accept Sequence[str|int|UUID4] for true genericity. RESOLUTION: Adopted — spec updated.
    3. Household verification for deduct_shopping_items is architecturally redundant — HouseholdRepositoryGeneric already scopes queries. RESOLUTION: Dropped explicit controller check; rely on existing scoping.
    4. shopping_lists.py needs a logger import before using logger.warning. RESOLUTION: Spec explicitly includes logger setup.

    Overall: Codex validated all file paths and structures as correct. Confirmed architectural patterns are consistent. Recommended changes have been incorporated into the specification.
```
