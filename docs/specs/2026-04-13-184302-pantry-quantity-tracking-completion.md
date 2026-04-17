```yaml
spec_metadata:
  goal: "Complete the pantry quantity tracking feature by addressing technical debt (N+1 fix, TypeScript regeneration, i18n) and implementing the feature backlog (meal plan deficit, bulk import from on_hand, expiration awareness, conversion failure UI, pantry deduction)"
  constraints:
    - "All new code must live in optimizer/ subdirectories per fork isolation rules"
    - "Upstream file modifications must be kept minimal — CLAUDE.md tracks the list"
    - "Shopping list integration must remain non-critical (try/except guard)"
    - "Existing API endpoints must not break — new schemas must be backward-compatible or use new endpoints"
    - "Database changes require Alembic migrations"
  non_goals:
    - "Reworking the core deficit calculation algorithm"
    - "Changing the existing CRUD API contract"
    - "Multi-household pantry sharing"
    - "Recipe ingredient parser improvements"
    - "Unit conversion algorithm improvements"
  timestamp: "2026-04-13T18:43:02"
  confidence: medium
  survey_consumed: false

current_state:
  summary: "A full pantry CRUD system with deficit calculation, shopping list integration, and frontend page is implemented. The system has 7 deficit rules, unit conversion via pint, and auto-check on shopping list creation. Technical debt items (N+1 fetch, manual TS types, no i18n) and a feature backlog (meal plan deficit, on_hand import, expiration, deduction) remain."
  relevant_files:
    - path: "mealie/db/models/optimizer/pantry.py"
      purpose: "PantryItemModel — SQLAlchemy model with group_id, household_id, food_id, quantity, unit_id, assume_enough, is_staple, expiration_date"
      reuse_potential: high
    - path: "mealie/schema/optimizer/pantry.py"
      purpose: "8 Pydantic schemas (Create/Save/Update/UpdateBulk/Out/Pagination + DeficitItem/DeficitReport)"
      reuse_potential: high
    - path: "mealie/repos/optimizer/pantry.py"
      purpose: "RepositoryPantryItem — HouseholdRepositoryGeneric with by_food_id, by_food_ids"
      reuse_potential: high
    - path: "mealie/services/optimizer/pantry.py"
      purpose: "PantryService — calculate_deficit (7 rules), check_shopping_items, helper methods"
      reuse_potential: high
    - path: "mealie/routes/optimizer/controller_pantry.py"
      purpose: "PantryItemController — 5 CRUD endpoints + POST /deficit"
      reuse_potential: high
    - path: "mealie/repos/repository_recipes.py"
      purpose: "RepositoryRecipes — no batch-by-ids method currently"
      reuse_potential: medium
    - path: "mealie/repos/repository_meals.py"
      purpose: "RepositoryMeals — get_today, get_meals_by_date_range returning ReadPlanEntry (has recipe_id)"
      reuse_potential: high
    - path: "mealie/db/models/recipe/ingredient.py"
      purpose: "households_to_ingredient_foods join table — existing boolean on_hand mechanism"
      reuse_potential: medium
    - path: "mealie/db/models/household/household.py"
      purpose: "Household model with ingredient_foods_on_hand relationship"
      reuse_potential: medium
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "Manually created TypeScript interfaces — should be regenerated"
      reuse_potential: low
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue"
      purpose: "Pantry management page"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/PantryItemRow.vue"
      purpose: "Row component with auto-save, always-available toggle"
      reuse_potential: high
    - path: "tests/unit_tests/services_tests/test_pantry_service.py"
      purpose: "12 unit tests covering all deficit rules + shopping item adjustment"
      reuse_potential: high
    - path: "tests/integration_tests/user_household_tests/test_pantry_items.py"
      purpose: "9 integration tests for API CRUD + validation + household isolation"
      reuse_potential: high
  patterns_identified:
    - "Class-based controllers: @controller(router) decorator on BaseCrudController subclasses with cached_property for repo/mixins/service"
    - "HttpRepo mixins: HttpRepo[CreateType, OutType, UpdateType] for standard CRUD"
    - "HouseholdRepositoryGeneric: base class that auto-filters by group_id/household_id"
    - "Schema hierarchy: Create -> Save (adds group_id/household_id) -> Update (adds id) -> Out (full response)"
    - "PaginationBase: standard pagination wrapper with items list"
    - "Fork isolation: all optimizer code under optimizer/ subdirectories"
    - "Graceful degradation: pantry integration wrapped in try/except in shopping_lists.py"

gaps:
  exists:
    - component: "Pantry CRUD (model, schema, repo, routes, service)"
      location: "mealie/*/optimizer/pantry.py"
      notes: "Fully working, no changes needed"
    - component: "Deficit calculation (7 rules)"
      location: "mealie/services/optimizer/pantry.py:49-221"
      notes: "calculate_deficit already accepts optional pantry_items param — reusable for all deficit variants"
    - component: "Shopping list integration"
      location: "mealie/services/household_services/shopping_lists.py:178-184"
      notes: "try/except guarded, stable"
    - component: "Meal plan repository"
      location: "mealie/repos/repository_meals.py"
      notes: "get_meals_by_date_range returns ReadPlanEntry with recipe_id — usable for meal plan deficit"
    - component: "on_hand relationship"
      location: "mealie/db/models/household/household.py:72-76"
      notes: "ingredient_foods_on_hand is a many-to-many via households_to_ingredient_foods — readable for bulk import"
    - component: "UnitConverter"
      location: "mealie/services/parser_services/parser_utils/unit_utils.py"
      notes: "Pint-based converter, already integrated into PantryService"
  partial:
    - component: "Deficit endpoint"
      location: "mealie/routes/optimizer/controller_pantry.py:44-55"
      missing: "N+1 recipe fetch (loops get_one per recipe_id). Needs batch fetch. Also needs request schema wrapper for exclude_expired option."
    - component: "TypeScript types"
      location: "frontend/app/lib/api/types/optimizer.ts"
      missing: "Manually created — needs regeneration via task dev:generate to pick up new schemas"
    - component: "is_staple field"
      location: "mealie/db/models/optimizer/pantry.py:34"
      missing: "Column exists in DB but removed from UI. Needs re-surfacing in expandable metadata section."
  missing:
    - component: "Batch recipe fetch"
      rationale: "RepositoryRecipes has no get_by_ids method. Deficit endpoint does N+1 queries. Need either a batch helper in optimizer/ or a new method on RepositoryRecipes."
    - component: "Meal plan deficit endpoint"
      rationale: "Users want to calculate deficit for an entire meal plan date range, not manually collect recipe IDs"
    - component: "Bulk import from on_hand"
      rationale: "Users migrating from Mealie's boolean on_hand need a one-click path to quantity-tracked pantry items"
    - component: "Expiration awareness"
      rationale: "expiration_date exists but is informational only — users expect expired items to optionally not count as available"
    - component: "Conversion failure UI"
      rationale: "DeficitReport items with conversion_failed=True have no visual indicator in the frontend"
    - component: "Pantry deduction"
      rationale: "Users want pantry quantities to auto-decrease when recipes are cooked or shopping trips completed"
    - component: "Frontend i18n"
      rationale: "Pantry page uses hardcoded English strings — not localizable"

specification:
  files:
    # --- 1. Batch recipe fetch helper (fork-isolated) ---
    - path: "mealie/services/optimizer/recipe_utils.py"
      action: create
      purpose: "Batch recipe ingredient fetcher that avoids N+1 queries while respecting fork isolation (does not modify RepositoryRecipes)"
      signature: |
        from pydantic import UUID4
        from sqlalchemy.orm import Session

        from mealie.schema.recipe.recipe_ingredient import RecipeIngredient


        def get_ingredients_for_recipes(
            session: Session,
            group_id: UUID4,
            recipe_ids: list[UUID4],
        ) -> list[RecipeIngredient]:
            """
            Batch-fetch all ingredients for the given recipe IDs in a single query.
            Uses RecipeModel.id IN (...) with eager-loaded recipe_ingredient.
            Returns flattened list of RecipeIngredient from all matched recipes.
            Recipes not found are silently skipped.
            """
            ...
      depends_on:
        - "mealie/db/models/recipe/recipe.py (RecipeModel)"
        - "mealie/schema/recipe/recipe_ingredient.py (RecipeIngredient)"
      acceptance_criteria:
        - "Single SQL query (SELECT ... WHERE id IN ...) instead of N get_one calls"
        - "Returns empty list for empty recipe_ids input"
        - "Silently skips recipe_ids that don't exist"
        - "Eager-loads recipe_ingredient relationship to avoid lazy-load N+1"

    # --- 2. Updated schemas ---
    - path: "mealie/schema/optimizer/pantry.py"
      action: modify
      purpose: "Add request schemas for deficit endpoint (replaces bare list[UUID4]), meal plan deficit, and import result"
      signature: |
        class PantryDeficitRequest(MealieModel):
            """Request body for POST /deficit — replaces bare list[UUID4]."""
            recipe_ids: list[UUID4]
            exclude_expired: bool = False

        class PantryMealPlanDeficitRequest(MealieModel):
            """Request body for POST /deficit/meal-plan."""
            start_date: date
            end_date: date
            exclude_expired: bool = False

            @model_validator(mode="after")
            def validate_date_range(self) -> PantryMealPlanDeficitRequest:
                """Ensure start_date <= end_date."""
                ...

        class PantryImportResult(MealieModel):
            """Response for POST /import-on-hand."""
            imported_count: int
            skipped_count: int

        class PantryDeductRequest(MealieModel):
            """Request body for POST /deduct."""
            recipe_id: UUID4
      depends_on:
        - "mealie/schema/_mealie/mealie_model.py (MealieModel)"
      acceptance_criteria:
        - "PantryDeficitRequest defaults exclude_expired=False for backward compatibility"
        - "PantryMealPlanDeficitRequest validates start_date <= end_date"
        - "PantryImportResult has imported_count and skipped_count as non-negative ints"

    # --- 3. Updated PantryService ---
    - path: "mealie/services/optimizer/pantry.py"
      action: modify
      purpose: "Add expiration filtering, bulk import, and pantry deduction methods"
      signature: |
        # New parameter on existing method:
        def calculate_deficit(
            self,
            recipe_ingredients: list[RecipeIngredient],
            pantry_items: list[PantryItemOut] | None = None,
            exclude_expired: bool = False,
        ) -> PantryDeficitReport:
            """
            Extended: when exclude_expired=True, filters out pantry items
            where expiration_date is not None and < date.today() before
            building the pantry_map.
            """
            ...

        # New methods:
        def import_from_on_hand(self) -> tuple[int, int]:
            """
            Read household's ingredient_foods_on_hand relationship.
            For each food_id not already in pantry_items, create a new
            PantryItem with quantity=None, assume_enough=False.
            Returns (imported_count, skipped_count).
            Uses a single query to fetch existing food_ids for conflict avoidance.
            """
            ...

        def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
            """
            Subtract recipe ingredient quantities from matching pantry items.
            Rules:
            - Skip ingredients with no food_id
            - Skip pantry items with assume_enough=True (don't deduct staples)
            - Skip pantry items with quantity=None (untracked)
            - For compatible units: pantry.quantity = max(0, pantry.quantity - recipe_qty)
            - For incompatible units: skip (don't deduct)
            - Persist changes and return updated pantry items
            """
            ...
      depends_on:
        - "mealie/repos/optimizer/pantry.py (RepositoryPantryItem)"
        - "mealie/services/parser_services/parser_utils/unit_utils.py (UnitConverter)"
        - "mealie/db/models/household/household.py (Household.ingredient_foods_on_hand)"
      acceptance_criteria:
        - "calculate_deficit with exclude_expired=False behaves identically to current implementation"
        - "calculate_deficit with exclude_expired=True filters pantry items with expiration_date < today"
        - "import_from_on_hand creates PantryItems only for foods not already in pantry"
        - "import_from_on_hand handles empty on_hand list gracefully (returns 0, 0)"
        - "deduct_recipe does not deduct from assume_enough or untracked items"
        - "deduct_recipe clamps quantity to 0 (never negative)"
        - "deduct_recipe persists changes via repository update"

    # --- 4. Updated controller ---
    - path: "mealie/routes/optimizer/controller_pantry.py"
      action: modify
      purpose: "Refactor deficit endpoint to use batch fetch + request schema; add meal plan deficit, import, and deduct endpoints"
      signature: |
        @router.post("/deficit", response_model=PantryDeficitReport)
        def calculate_deficit(self, data: PantryDeficitRequest) -> PantryDeficitReport:
            """Refactored: accepts PantryDeficitRequest, uses batch ingredient fetch."""
            ...

        @router.post("/deficit/meal-plan", response_model=PantryDeficitReport)
        def calculate_meal_plan_deficit(self, data: PantryMealPlanDeficitRequest) -> PantryDeficitReport:
            """
            Extract recipe_ids from meal plan entries in date range,
            deduplicate, batch-fetch ingredients, delegate to calculate_deficit.
            Entries with recipe_id=None are ignored.
            """
            ...

        @router.post("/import-on-hand", response_model=PantryImportResult)
        def import_from_on_hand(self) -> PantryImportResult:
            """Bulk import on_hand foods as pantry items."""
            ...

        @router.post("/deduct", response_model=list[PantryItemOut])
        def deduct_recipe(self, data: PantryDeductRequest) -> list[PantryItemOut]:
            """Deduct recipe ingredient quantities from pantry."""
            ...
      depends_on:
        - "mealie/services/optimizer/pantry.py (PantryService)"
        - "mealie/services/optimizer/recipe_utils.py (get_ingredients_for_recipes)"
        - "mealie/repos/repository_meals.py (RepositoryMeals.get_meals_by_date_range)"
        - "mealie/schema/optimizer/pantry.py (new request/response schemas)"
      acceptance_criteria:
        - "POST /deficit still works with recipe_ids list (now inside request body object)"
        - "POST /deficit/meal-plan returns deficit report for all recipes in date range"
        - "POST /deficit/meal-plan with no recipes in range returns 100% coverage"
        - "POST /import-on-hand returns count of imported + skipped items"
        - "POST /import-on-hand is idempotent (second call returns 0 imported)"
        - "POST /deduct returns updated pantry items after deduction"
        - "All new endpoints require authentication (inherited from BaseCrudController)"

    # --- 5. TypeScript type regeneration ---
    - path: "frontend/app/lib/api/types/optimizer.ts"
      action: modify
      purpose: "Regenerate from Pydantic schemas via task dev:generate to pick up new request/response types"
      signature: |
        // Auto-generated — will include:
        // PantryDeficitRequest { recipeIds: string[], excludeExpired?: boolean }
        // PantryMealPlanDeficitRequest { startDate: string, endDate: string, excludeExpired?: boolean }
        // PantryImportResult { importedCount: number, skippedCount: number }
        // PantryDeductRequest { recipeId: string }
      depends_on:
        - "mealie/schema/optimizer/pantry.py (source Pydantic schemas)"
      acceptance_criteria:
        - "File is auto-generated, not manually edited"
        - "All new schemas from pantry.py appear as TypeScript interfaces"

    # --- 6. Frontend API client updates ---
    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      action: modify
      purpose: "Add API methods for new endpoints (meal plan deficit, import, deduct)"
      signature: |
        // Existing: extends BaseCRUDAPI
        // Add methods:
        async calculateDeficit(data: PantryDeficitRequest): Promise<PantryDeficitReport> { ... }
        async calculateMealPlanDeficit(data: PantryMealPlanDeficitRequest): Promise<PantryDeficitReport> { ... }
        async importFromOnHand(): Promise<PantryImportResult> { ... }
        async deductRecipe(data: PantryDeductRequest): Promise<PantryItemOut[]> { ... }
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "Each method calls the corresponding backend endpoint"
        - "Return types match the backend response schemas"

    # --- 7. Conversion failure UI ---
    - path: "frontend/app/components/optimizer/PantryItemRow.vue"
      action: modify
      purpose: "Add visual indicator for conversion_failed items in deficit display"
      signature: |
        // Add conditional icon/badge when deficit item has conversionFailed=true
        // Uses Vuetify v-icon with mdi-alert-circle-outline
        // Tooltip: "Unit conversion failed — quantities may be inaccurate"
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts (PantryDeficitItem.conversionFailed)"
      acceptance_criteria:
        - "Warning icon visible when conversionFailed is true"
        - "Icon not visible when conversionFailed is false or undefined"
        - "Tooltip explains the issue"

    # --- 8. Frontend i18n ---
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue"
      action: modify
      purpose: "Replace hardcoded English strings with i18n translation keys"
      signature: |
        // Replace all hardcoded strings with $t('optimizer.pantry.<key>') calls
        // Keys to add: title, add-item, delete-confirm, always-available,
        //   quantity, unit, expiration, food, no-items, import-on-hand,
        //   import-success, deficit-calculate, deficit-coverage
      depends_on:
        - "Frontend i18n system (Nuxt i18n module)"
      acceptance_criteria:
        - "No hardcoded English strings remain in pantry.vue"
        - "All strings use $t() with optimizer.pantry.* namespace"
        - "English translations file updated with all keys"

    # --- 9. Unit tests ---
    - path: "tests/unit_tests/services_tests/test_pantry_service.py"
      action: modify
      purpose: "Add tests for expiration filtering, import logic, and deduction"
      signature: |
        class ExpirationFilterTests:
            def test_expired_items_excluded_when_flag_set(self): ...
            def test_expired_items_included_when_flag_false(self): ...
            def test_items_without_expiration_always_included(self): ...

        class DeductRecipeTests:
            def test_deduct_reduces_pantry_quantity(self): ...
            def test_deduct_clamps_to_zero(self): ...
            def test_deduct_skips_assume_enough(self): ...
            def test_deduct_skips_untracked_quantity(self): ...
            def test_deduct_skips_incompatible_units(self): ...
            def test_deduct_handles_unit_conversion(self): ...
      depends_on:
        - "mealie/services/optimizer/pantry.py"
      acceptance_criteria:
        - "All new tests pass"
        - "Existing 12 tests still pass unchanged"

    # --- 10. Batch fetch tests ---
    - path: "tests/unit_tests/services_tests/test_recipe_utils.py"
      action: create
      purpose: "Test the batch ingredient fetch helper"
      signature: |
        class GetIngredientsForRecipesTests:
            def test_returns_all_ingredients_for_multiple_recipes(self): ...
            def test_returns_empty_for_empty_input(self): ...
            def test_skips_nonexistent_recipe_ids(self): ...
      depends_on:
        - "mealie/services/optimizer/recipe_utils.py"
      acceptance_criteria:
        - "Tests verify batch fetch returns correct ingredients"
        - "Tests verify empty input handling"

    # --- 11. Integration tests ---
    - path: "tests/integration_tests/user_household_tests/test_pantry_items.py"
      action: modify
      purpose: "Add integration tests for new endpoints"
      signature: |
        # Add test methods:
        def test_deficit_with_exclude_expired(self): ...
        def test_meal_plan_deficit(self): ...
        def test_import_on_hand(self): ...
        def test_import_on_hand_idempotent(self): ...
        def test_deduct_recipe(self): ...
      depends_on:
        - "mealie/routes/optimizer/controller_pantry.py"
      acceptance_criteria:
        - "New endpoints return correct status codes"
        - "Import endpoint is idempotent"
        - "Meal plan deficit returns correct coverage for date range"
        - "Deduct endpoint reduces quantities correctly"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/db/models/optimizer/pantry.py — fully analyzed, PantryItemModel is stable"
    - "mealie/schema/optimizer/pantry.py — fully analyzed, extending with new schemas"
    - "mealie/repos/optimizer/pantry.py — fully analyzed, no changes needed"
    - "mealie/services/optimizer/pantry.py — fully analyzed, extending calculate_deficit + adding methods"
    - "mealie/routes/optimizer/controller_pantry.py — fully analyzed, adding endpoints"
    - "mealie/repos/repository_meals.py — fully analyzed, get_meals_by_date_range is reusable as-is"
    - "mealie/db/models/recipe/ingredient.py — fully analyzed, households_to_ingredient_foods understood"
    - "mealie/db/models/household/household.py — fully analyzed, ingredient_foods_on_hand relationship understood"
    - "tests/unit_tests/services_tests/test_pantry_service.py — fully analyzed, test pattern understood"
    - "tests/integration_tests/user_household_tests/test_pantry_items.py — fully analyzed, test pattern understood"
    - "frontend/app/lib/api/types/optimizer.ts — fully analyzed, will be regenerated"
  known_patterns:
    - "Controller pattern: @controller(router) decorator, cached_property for repo/mixins/service"
    - "Schema pattern: Create -> Save -> Update -> Out hierarchy"
    - "Repository pattern: HouseholdRepositoryGeneric subclass auto-filters by group_id/household_id"
    - "Test pattern: use object.__new__(PantryService) + manual converter setup to test without DB"
    - "Graceful degradation: pantry integration wrapped in try/except"
    - "Route ordering: POST /deficit before /{item_id} to avoid route conflict — apply same for new POST endpoints"
  decisions_made:
    - "Fork-isolated batch fetch: create mealie/services/optimizer/recipe_utils.py instead of modifying RepositoryRecipes — avoids adding to upstream modified files list"
    - "Request schema for deficit: wrap recipe_ids + exclude_expired in PantryDeficitRequest object instead of bare list[UUID4] — this is a breaking change to the request body shape, acceptable since the fork has no external API consumers"
    - "Import uses pre-fetch for conflict avoidance: query existing food_ids before insert rather than ON CONFLICT — simpler with SQLAlchemy ORM and repository pattern"
    - "Deduct skips assume_enough and untracked items: these items have no meaningful quantity to deduct from"
    - "Meal plan deficit deduplicates recipe_ids: a recipe appearing in multiple meal plan entries should only count once in the deficit"
  warnings:
    - "POST /deficit request body changes from list[UUID4] to PantryDeficitRequest — frontend API client must update simultaneously"
    - "ReadPlanEntry has recipe_id: UUID | None — meal plan entries with no recipe must be filtered out"
    - "import_from_on_hand needs access to the Household model's relationship — may need to query the household from the session directly rather than going through HouseholdRepositoryGeneric"
    - "deduct_recipe involves writes — must be careful about transaction boundaries and concurrent access"
    - "Route ordering matters: all new POST endpoints (/deficit/meal-plan, /import-on-hand, /deduct) must be declared before /{item_id} routes"

open_questions:
  - question: "Should POST /deficit remain backward-compatible by accepting both list[UUID4] and PantryDeficitRequest, or is a clean break acceptable?"
    blocking: false
    default_assumption: "Clean break — wrap in PantryDeficitRequest. Fork has no external consumers."
  - question: "Should meal plan deficit deduplicate by recipe_id only, or should repeated recipes multiply their ingredient requirements?"
    blocking: false
    default_assumption: "Deduplicate — deficit answers 'what ingredients do I need for these unique recipes' not 'how many servings total'"
  - question: "Should pantry deduction happen automatically when a recipe is marked as cooked, or only via explicit POST /deduct?"
    blocking: false
    default_assumption: "Explicit POST /deduct only — automatic deduction requires wiring into upstream recipe/meal-plan flows and increases upstream modification footprint"
  - question: "For bulk import, should imported items default to assume_enough=False (quantity-untracked) or should the user choose?"
    blocking: false
    default_assumption: "Default assume_enough=False, quantity=None — simple migration path, user can toggle later"
  - question: "Should the is_staple field UI be included in this spec or deferred further?"
    blocking: false
    default_assumption: "Deferred — no feature currently depends on it, and the UX for differentiating staple vs always-available needs design"

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Codex validated the overall architecture but raised several concerns:

    1. **Fork isolation vs upstream modification**: Adding get_by_ids to RepositoryRecipes
       violates fork isolation. RESOLVED: spec creates optimizer/recipe_utils.py helper
       that queries RecipeModel directly via session, avoiding upstream modification.

    2. **Backward compatibility of POST /deficit**: Changing from list[UUID4] to
       PantryDeficitRequest object breaks existing callers. ACCEPTED: fork has no
       external API consumers; frontend client updates simultaneously.

    3. **ReadPlanEntry.recipe_id can be None**: Meal plan entries may have no recipe.
       RESOLVED: spec explicitly requires filtering out None recipe_ids before
       passing to calculate_deficit.

    4. **Bulk import race conditions**: Unique constraint on (household_id, food_id)
       can throw IntegrityError under concurrent requests. RESOLVED: spec uses
       pre-fetch of existing food_ids + single-transaction insert rather than
       ON CONFLICT. Acceptable for single-user fork.

    5. **Deduction transaction boundaries**: deduct_recipe involves reads + writes
       that must be atomic. Deep-plan should ensure proper transaction handling
       via the existing session/repository pattern.

    Codex also suggested keeping all new logic in optimizer/ subdirectories and
    using session-level queries for batch operations — both incorporated into spec.
```
