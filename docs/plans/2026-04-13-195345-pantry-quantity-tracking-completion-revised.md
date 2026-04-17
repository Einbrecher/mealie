# Implementation Plan: Pantry Quantity Tracking Completion

Source: docs/plans/2026-04-13-192743-pantry-quantity-tracking-completion.md
Revised: 2026-04-13

<plan_metadata>
  <feature>Pantry Quantity Tracking Completion</feature>
  <source>docs/plans/2026-04-13-192743-pantry-quantity-tracking-completion.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>6</phases>
  <tasks>15</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Complete the pantry quantity tracking feature by: fixing the N+1 recipe fetch (batch helper), adding four new API endpoints (refactored deficit, meal plan deficit, import-on-hand, deduct), extending the service layer with expiration filtering / bulk import / pantry deduction, and updating the frontend with TypeScript types, API client methods, and i18n. All new backend code lives in `optimizer/` subdirectories per fork isolation rules.

**Dependency model:** This plan uses task-level dependencies (DAG), not phase-level gating. Tasks may start as soon as their explicit `depends` are satisfied, regardless of which phase they belong to. Phases are logical groupings for readability only.

## Changes from Original

<revision_summary>
<change type="structural">
  Converted from phase-level dependencies to task-level DAG. Tasks 4.1, 5.1, and 5.3 can now start as soon as their actual inputs are ready (Phase 1/2), rather than waiting for Phase 3 completion. This enables parallelism between backend tests, frontend types, and i18n work.
</change>
<change type="structural">
  Split original Task 3.1 (refactor deficit + add meal plan deficit) into Task 3.1 (refactor deficit only) and Task 3.2 (add meal plan deficit). The refactor is a breaking change that must be verified independently before adding new endpoints.
</change>
<change type="removed">
  Removed original Task 4.1 (batch fetch unit tests). The batch fetch helper is a thin SQL query wrapper — mocking SQLAlchemy's select/execute chain is fragile and tests the mock, not the code. Coverage is provided by integration tests in Task 4.2.
</change>
<change type="removed">
  Deferred original Task 5.3 (conversion failure UI indicator on PantryItemRow). PantryItemRow is an item editor — it does not display deficit results. Adding a `conversionFailed` prop creates dead code with no wiring. This belongs in a future deficit results view.
</change>
<change type="clarity">
  Task 2.2 (import_from_on_hand): Replaced `session.get()` pattern with `select()` query. No `session.get()` calls exist anywhere in this codebase — the `select()` pattern is consistent and avoids GUID type coercion edge cases.
</change>
<change type="clarity">
  Task 2.3 (deduct_recipe): Documented that deduction is non-atomic — the generic `repo.update()` commits per call. This is an accepted tradeoff for a single-user fork. Added documentation requirement.
</change>
<change type="clarity">
  Task 5.1 (TypeScript types): Removed "try auto-generate first" option. No codegen pipeline exists for optimizer types. Go directly to manual interface addition.
</change>
<change type="clarity">
  Task 4.2 (integration tests): Added concrete fixture setup strategies for meal plan entries, on_hand foods, and recipe ingredients — these were identified as hidden complexity by both reviewers.
</change>
<change type="dependency">
  Task 4.1 (unit tests for service methods) now depends on Tasks 2.1/2.3, not Phase 3. Task 5.1 (TypeScript types) now depends on Task 1.2, not Phase 3. Task 5.3 (i18n) has no dependencies.
</change>
</revision_summary>

## Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>Python 3.12 with FastAPI, SQLAlchemy 2.0, Pydantic 2 installed</description>
  <verification>Run `task py:test` — existing pantry tests pass</verification>
</prereq>
<prereq id="P2" type="environment" verified="true">
  <description>Nuxt 4 / Vue 3 / Vuetify 4 frontend dev environment</description>
  <verification>Run `task ui` — frontend starts on localhost:3000</verification>
</prereq>
<prereq id="P3" type="data" verified="true">
  <description>PantryItemModel already has all required DB columns (food_id, quantity, unit_id, assume_enough, is_staple, expiration_date). No new columns or tables are added by this plan — no Alembic migration needed.</description>
  <verification>Read `mealie/db/models/optimizer/pantry.py` — all columns present</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>UnitConverter (pint-based) available at `mealie/services/parser_services/parser_utils/unit_utils.py`</description>
  <verification>Already imported and used in `PantryService.__init__`</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>`RepositoryMeals.get_meals_by_date_range(datetime, datetime)` returns `list[ReadPlanEntry]` with `recipe_id: UUID | None`</description>
  <verification>Read `mealie/repos/repository_meals.py` lines 23-33</verification>
</prereq>
<prereq id="P6" type="data" verified="true">
  <description>`households_to_ingredient_foods` join table exists with unique constraint on `(household_id, food_id)`</description>
  <verification>Read `mealie/db/models/recipe/ingredient.py` lines 21-27</verification>
</prereq>
<prereq id="P7" type="data" verified="true">
  <description>`RepositoryGeneric.create_many()` (line 195) and `update_many()` (line 228) exist in `mealie/repos/repository_generic.py`</description>
  <verification>Read `mealie/repos/repository_generic.py` — both methods present</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend Foundation — Schemas & Batch Fetch Helper

<phase id="1" name="Backend Foundation">

### 1.1 Create Batch Recipe Ingredient Fetcher

<task id="1.1" status="pending" depends="" risk="medium">
<context>
The current deficit endpoint at `mealie/routes/optimizer/controller_pantry.py` loops through recipe_ids and calls `group_repos.recipes.get_one(recipe_id)` per ID — an N+1 query pattern. This task creates a fork-isolated helper that batch-fetches all ingredients in a single SQL query.

**File to create:** `mealie/services/optimizer/recipe_utils.py`

**Key implementation details:**
- Function signature: `get_ingredients_for_recipes(session: Session, group_id: UUID4, recipe_ids: list[UUID4]) -> list[RecipeIngredient]`
- Query: `select(RecipeModel).where(RecipeModel.id.in_(recipe_ids), RecipeModel.group_id == group_id)` — the `group_id` filter is critical for tenant isolation
- Eager loading chain: `selectinload(RecipeModel.recipe_ingredient).selectinload(RecipeIngredientModel.food)` and `.selectinload(RecipeIngredientModel.unit)` — required because `calculate_deficit` accesses `ingredient.food.id` and `ingredient.unit.standard_unit`
- Short-circuit: return `[]` for empty `recipe_ids` before querying
- Silently skip recipe_ids that don't exist (no error)
- Convert SQLAlchemy models to Pydantic `RecipeIngredient` schemas via `RecipeIngredient.model_validate(model)` (the schema has `model_config = ConfigDict(from_attributes=True)`)

**File references:**
- RecipeModel: `mealie/db/models/recipe/recipe.py` — has `recipe_ingredient` relationship (line ~103)
- RecipeIngredientModel: `mealie/db/models/recipe/ingredient.py` — has `food` and `unit` relationships
- RecipeIngredient schema: `mealie/schema/recipe/recipe_ingredient.py` (class near line 330)
</context>

<subtasks>
- [ ] Create `mealie/services/optimizer/recipe_utils.py`
- [ ] Import RecipeModel, RecipeIngredientModel, RecipeIngredient schema, selectinload
- [ ] Implement `get_ingredients_for_recipes` with `group_id` scoping and eager loading
- [ ] Short-circuit on empty `recipe_ids` (return `[]` immediately)
- [ ] Convert ORM instances to Pydantic schemas before returning
- [ ] Verify `mealie/services/optimizer/__init__.py` exports or doesn't block the import
</subtasks>

<acceptance>
- `from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes` succeeds
- Returns `[]` for `recipe_ids=[]` without issuing a SQL query
- Silently skips nonexistent recipe_ids (returns ingredients only for found recipes)
- Returned `RecipeIngredient` objects have populated `.food` and `.unit` attributes (no `None` or lazy-load errors)
- `group_id` filter is present in the WHERE clause (verify by reading the code)
- `task py:lint` passes for the new file
</acceptance>
</task>

### 1.2 Add New Request/Response Schemas

<task id="1.2" status="pending" depends="" risk="low">
<context>
Add four new Pydantic schemas to `mealie/schema/optimizer/pantry.py` for the new endpoints. The file currently has 8 schemas (PantryItemCreate, PantryItemSave, PantryItemUpdate, PantryItemUpdateBulk, PantryItemOut, PantryItemPagination, PantryDeficitItem, PantryDeficitReport). Add new schemas at the end of the file.

**Schemas to add:**

1. `PantryDeficitRequest(MealieModel)` — replaces the current bare `list[UUID4]` parameter
   - `recipe_ids: list[UUID4]`
   - `exclude_expired: bool = False`

2. `PantryMealPlanDeficitRequest(MealieModel)` — for meal plan deficit
   - `start_date: date`
   - `end_date: date`
   - `exclude_expired: bool = False`
   - `@model_validator(mode="after")` to ensure `start_date <= end_date`

3. `PantryImportResult(MealieModel)` — response for import endpoint
   - `imported_count: int`
   - `skipped_count: int`

4. `PantryDeductRequest(MealieModel)` — for deduction endpoint
   - `recipe_id: UUID4`

**Imports needed:** `from datetime import date` and `from pydantic import model_validator` (check if `model_validator` is already imported — `field_validator` may already be there).
</context>

<subtasks>
- [ ] Add `from datetime import date` import (if not present)
- [ ] Add `from pydantic import model_validator` import (check if already imported)
- [ ] Add `PantryDeficitRequest` class
- [ ] Add `PantryMealPlanDeficitRequest` class with date range validator
- [ ] Add `PantryImportResult` class
- [ ] Add `PantryDeductRequest` class
</subtasks>

<acceptance>
- `from mealie.schema.optimizer.pantry import PantryDeficitRequest, PantryMealPlanDeficitRequest, PantryImportResult, PantryDeductRequest` succeeds
- `PantryDeficitRequest(recipe_ids=[])` works with default `exclude_expired=False`
- `PantryMealPlanDeficitRequest(start_date="2026-01-01", end_date="2025-12-31")` raises `ValidationError` (start > end)
- `PantryMealPlanDeficitRequest(start_date="2026-01-01", end_date="2026-01-01")` succeeds (same day valid)
- `PantryImportResult(imported_count=5, skipped_count=2)` works
- `PantryDeductRequest(recipe_id="some-uuid-string")` works
- `task py:lint` passes for the modified file
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `mealie/services/optimizer/recipe_utils.py` exists with `get_ingredients_for_recipes` function
- [ ] `mealie/schema/optimizer/pantry.py` contains all 4 new schema classes
- [ ] Both new imports succeed (test in Python REPL or via `python -c "from mealie.schema.optimizer.pantry import PantryDeficitRequest"`)
- [ ] `task py:lint` — no errors in new/modified files
</verification>
<gate>Both new files/schemas are importable and pass linting</gate>
</checkpoint>

</phase>

---

## Phase 2: Service Layer — Expiration, Import, Deduction

<phase id="2" name="Service Layer">

### 2.1 Add Expiration Filtering to calculate_deficit

<task id="2.1" status="pending" depends="1.2" risk="low">
<context>
Extend the existing `calculate_deficit` method in `mealie/services/optimizer/pantry.py` to accept an `exclude_expired: bool = False` parameter. When True, filter out pantry items with past expiration dates before building the pantry map.

**Current signature** (around line 49):
```python
def calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None) -> PantryDeficitReport:
```

**New signature:**
```python
def calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None, exclude_expired: bool = False) -> PantryDeficitReport:
```

**Implementation:** After fetching/receiving `pantry_items` but before building the `pantry_map` dict, add:
```python
if exclude_expired:
    today = date.today()
    pantry_items = [p for p in pantry_items if p.expiration_date is None or p.expiration_date >= today]
```

**Critical:** Default `False` ensures existing callers (shopping list integration at `mealie/services/household_services/shopping_lists.py:178-184`) are unaffected.
</context>

<subtasks>
- [ ] Add `from datetime import date` import if not present
- [ ] Add `exclude_expired: bool = False` parameter to `calculate_deficit`
- [ ] Add filtering logic after pantry_items are resolved but before pantry_map construction
</subtasks>

<acceptance>
- Calling `calculate_deficit(ingredients, exclude_expired=False)` behaves identically to current implementation (existing unit tests pass unchanged)
- Calling `calculate_deficit(ingredients, exclude_expired=True)` excludes items with `expiration_date < today`
- Items with `expiration_date=None` are always included regardless of flag
- Run `pytest tests/unit_tests/services_tests/test_pantry_service.py -v` — all 12 existing tests pass
</acceptance>
</task>

### 2.2 Add import_from_on_hand Method

<task id="2.2" status="pending" depends="1.2" risk="medium">
<context>
Add `import_from_on_hand` to PantryService in `mealie/services/optimizer/pantry.py`. This reads the household's `ingredient_foods_on_hand` M2M relationship and creates PantryItem records for foods not already tracked.

**Access pattern — use `select()`, NOT `session.get()`:** No `session.get()` calls exist anywhere in this codebase. Use the standard `select()` pattern to avoid GUID type coercion edge cases:
```python
from mealie.db.models.household.household import Household as HouseholdModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

stmt = (
    select(HouseholdModel)
    .where(HouseholdModel.id == self.repos.household_id)
    .options(selectinload(HouseholdModel.ingredient_foods_on_hand))
)
household = self.repos.session.execute(stmt).scalars().one_or_none()
```

**Tenant isolation:** After fetching, verify `household.group_id == self.repos.group_id`. If mismatch (should never happen in authenticated context), return `(0, 0)`.

**Logic:**
1. Get all food_ids currently in pantry: `existing_food_ids = {item.food_id for item in self.pantry_items.get_all()}`
   - `get_all()` on HouseholdRepositoryGeneric already filters by household_id
2. Get on_hand food IDs from household relationship: `on_hand_foods = household.ingredient_foods_on_hand`
3. For each on_hand food not in `existing_food_ids`, create a `PantryItemSave` with:
   - `food_id=food.id`, `name=None`, `quantity=None`, `unit_id=None`
   - `assume_enough=False`, `is_staple=False`, `expiration_date=None`
   - `group_id=self.repos.group_id`, `household_id=self.repos.household_id`
4. Create via repo — check if `self.pantry_items.create_many()` works (it exists in `repository_generic.py` line 195); if it requires a different schema type, fall back to looping `create_one()`
5. Return `(imported_count, skipped_count)`

**Schema reference:** `PantryItemSave` at `mealie/schema/optimizer/pantry.py` — extends `PantryItemCreate`, adds `group_id` and `household_id`.

**Edge cases:**
- Empty on_hand list → return `(0, 0)`
- All on_hand foods already in pantry → return `(0, N)`
- Household not found → return `(0, 0)` with no error
</context>

<subtasks>
- [ ] Add imports: HouseholdModel, select, selectinload, PantryItemSave
- [ ] Implement `import_from_on_hand(self) -> tuple[int, int]`
- [ ] Query household model via `select()` with eager-loaded `ingredient_foods_on_hand`
- [ ] Validate `group_id` matches for tenant isolation
- [ ] Fetch existing pantry food_ids in a single query via `get_all()`
- [ ] Create new PantryItem for each missing food (try `create_many`, fall back to `create_one` loop)
- [ ] Return `(imported_count, skipped_count)`
</subtasks>

<acceptance>
- Creates PantryItems only for foods not already in pantry
- Handles empty on_hand list gracefully (returns `(0, 0)`)
- Each imported item has `quantity=None`, `assume_enough=False`
- `group_id`/`household_id` are set correctly on imported items
- Second call with same data returns `(0, N)` — idempotent
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
If import creates incorrect items, they can be deleted via the existing DELETE /{item_id} endpoint. No schema changes involved.
</rollback>
</task>

### 2.3 Add deduct_recipe Method

<task id="2.3" status="pending" depends="1.2" risk="medium">
<context>
Add `deduct_recipe` to PantryService in `mealie/services/optimizer/pantry.py`. This subtracts recipe ingredient quantities from matching pantry items.

**Signature:** `def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]`

**Atomicity note:** The generic `repo.update()` in `repository_generic.py` commits per call. This means a partial failure (e.g., error on the 3rd of 5 updates) will leave the first 2 committed. This is an accepted tradeoff for this single-user fork — partial deductions are recoverable by manually adjusting quantities. Add a code comment documenting this behavior: `# Note: updates commit per item (repo.update pattern). Partial deduction is recoverable.`

Alternatively, investigate whether `self.pantry_items.update_many()` (exists at line 228 of `repository_generic.py`) provides batch commit behavior. If it does, prefer it.

**Deduction rules:**
1. Skip ingredients with no `food` or `food.id` (no food to match)
2. Build a pantry map: `{food_id: PantryItemOut}` from `self.pantry_items.get_all()`
3. For each ingredient with a matching pantry item:
   - Skip if `pantry_item.assume_enough is True` (don't deduct from "always available")
   - Skip if `pantry_item.quantity is None` (untracked quantity)
   - Attempt unit conversion if units differ:
     - Use `self.converter.can_convert()` to check compatibility
     - If incompatible: **skip** (consistent with deficit calculation rule 7)
     - If compatible: convert recipe quantity to pantry unit, then subtract
   - Clamp: `pantry_item.quantity = max(0.0, pantry_item.quantity - converted_qty)`
4. Persist all changed items via repository update
5. Return list of updated PantryItemOut objects (only items that were actually modified)

**Conversion failure behavior:** Skip items with incompatible units silently — consistent with how `calculate_deficit` handles `conversion_failed` items. The response includes only successfully deducted items.
</context>

<subtasks>
- [ ] Implement `deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]`
- [ ] Build pantry map from repository via `get_all()`
- [ ] Iterate ingredients, match to pantry items by `food_id`
- [ ] Apply skip rules (no food, `assume_enough`, `None` quantity, incompatible units)
- [ ] Convert units where needed using `self.converter`
- [ ] Clamp quantity to 0 (never negative)
- [ ] Persist changes via repo update (add atomicity comment)
- [ ] Return list of items that were actually modified
</subtasks>

<acceptance>
- Deduction reduces pantry quantity correctly for same-unit case (e.g., 5 in pantry - 3 needed = 2)
- Deduction handles unit conversion (e.g., recipe in grams, pantry in kg)
- Quantity never goes below 0 (5 in pantry - 10 needed = 0)
- `assume_enough` items are untouched
- `None`-quantity items are untouched
- Incompatible-unit items are untouched (skipped)
- Returned list contains only items that were actually modified
- `task py:lint` passes
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `calculate_deficit` accepts `exclude_expired` parameter
- [ ] `import_from_on_hand` method exists on PantryService
- [ ] `deduct_recipe` method exists on PantryService
- [ ] `task py:lint` — no errors in modified files
- [ ] `pytest tests/unit_tests/services_tests/test_pantry_service.py -v` — existing 12 tests still pass
</verification>
<gate>All three service methods are implemented and existing tests pass unchanged</gate>
</checkpoint>

</phase>

---

## Phase 3: Controller Endpoints

<phase id="3" name="Controller Endpoints">

### 3.1 Refactor POST /deficit to Use Request Schema + Batch Fetch

<task id="3.1" status="pending" depends="2.1,1.1" risk="high">
<context>
Modify the existing POST /deficit endpoint in `mealie/routes/optimizer/controller_pantry.py` to accept `PantryDeficitRequest` instead of bare `list[UUID4]`, and use the batch fetch helper instead of the N+1 loop.

**This is a breaking change** to the POST /deficit request body shape. The frontend API client (`frontend/app/lib/api/user/optimizer-pantry.ts`) currently sends a bare array. Task 5.2 updates the frontend client, but until then the deficit feature will not work end-to-end. This is acceptable — the fork has no external API consumers.

**Current code** (around lines 44-55):
```python
@router.post("/deficit", response_model=PantryDeficitReport)
def calculate_deficit(self, recipe_ids: list[UUID4]):
    # N+1 loop fetching recipes one at a time
```

**Refactored code:**
```python
@router.post("/deficit", response_model=PantryDeficitReport)
def calculate_deficit(self, data: PantryDeficitRequest) -> PantryDeficitReport:
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, data.recipe_ids)
    return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)
```

**Important:** The existing integration test at `tests/integration_tests/user_household_tests/test_pantry_items.py` that tests POST /deficit sends a bare `[]`. This test WILL fail after this change. Update it simultaneously to send `{"recipe_ids": [], "exclude_expired": false}` (or the camelCase equivalent per Pydantic alias config: `{"recipeIds": [], "excludeExpired": false}`). Check which casing the controller expects by looking at MealieModel's alias_generator.

**Imports to add:** `PantryDeficitRequest` from `mealie.schema.optimizer.pantry`, `get_ingredients_for_recipes` (can be inline import or top-level).

**Route ordering note:** `/deficit` is already declared before `/{item_id}` routes — verify this remains true after editing.
</context>

<subtasks>
- [ ] Add import for `PantryDeficitRequest`
- [ ] Refactor `calculate_deficit` endpoint to accept `PantryDeficitRequest` body
- [ ] Replace N+1 loop with `get_ingredients_for_recipes` call
- [ ] Pass `exclude_expired` through to service
- [ ] Update the existing integration test to use the new request body shape
- [ ] Verify route ordering (POST /deficit still before `/{item_id}`)
</subtasks>

<acceptance>
- POST /deficit with `{"recipeIds": [], "excludeExpired": false}` returns empty report with 100% coverage
- POST /deficit with valid recipe IDs returns deficit report
- `task py:lint` passes
- Existing integration test passes after body shape update
</acceptance>

<rollback risk="high">
If the refactored endpoint breaks, revert controller_pantry.py to restore the bare `list[UUID4]` signature and revert the integration test change. The batch fetch helper (Task 1.1) is independent and can remain.
</rollback>
</task>

### 3.2 Add POST /deficit/meal-plan Endpoint

<task id="3.2" status="pending" depends="3.1" risk="medium">
<context>
Add a new endpoint to `mealie/routes/optimizer/controller_pantry.py` that calculates deficit for all recipes in a meal plan date range.

**Implementation:**
```python
@router.post("/deficit/meal-plan", response_model=PantryDeficitReport)
def calculate_meal_plan_deficit(self, data: PantryMealPlanDeficitRequest) -> PantryDeficitReport:
    from datetime import datetime
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    # get_meals_by_date_range takes datetime objects, not date
    start_dt = datetime.combine(data.start_date, datetime.min.time())
    end_dt = datetime.combine(data.end_date, datetime.max.time())
    meals = self.repos.meals.get_meals_by_date_range(start_dt, end_dt)
    recipe_ids = list({m.recipe_id for m in meals if m.recipe_id is not None})
    all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, recipe_ids)
    return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)
```

**Key details:**
- `self.repos.meals` — verify this accessor exists on the controller. If not, access via `self.repos.meal_plans` or similar. Check the MealPlan repository name in `mealie/repos/all_repositories.py`.
- `ReadPlanEntry.recipe_id` can be `None` — meal plan entries without a recipe are filtered out
- Recipe IDs are deduplicated via `set()` — each unique recipe counts once (deliberate design choice per Q2)
- Date range validation (`start_date <= end_date`) is handled by the `PantryMealPlanDeficitRequest` schema validator

**CRITICAL — Route ordering:** This endpoint MUST be declared BEFORE any `/{item_id}` routes. Place it immediately after the existing `/deficit` endpoint.
</context>

<subtasks>
- [ ] Add import for `PantryMealPlanDeficitRequest`
- [ ] Verify the meal plan repository accessor name (check `all_repositories.py`)
- [ ] Implement `calculate_meal_plan_deficit` endpoint
- [ ] Convert `date` to `datetime` for `get_meals_by_date_range`
- [ ] Filter out `None` recipe_ids, deduplicate via `set()`
- [ ] Place endpoint BEFORE `/{item_id}` routes
</subtasks>

<acceptance>
- POST /deficit/meal-plan with valid date range returns deficit report
- POST /deficit/meal-plan with no recipes in range returns 100% coverage report
- POST /deficit/meal-plan with `start_date > end_date` returns 422 validation error (from schema validator)
- Endpoint requires authentication (inherited from BaseCrudController)
- `task py:lint` passes
</acceptance>
</task>

### 3.3 Add Import and Deduct Endpoints

<task id="3.3" status="pending" depends="2.2,2.3" risk="low">
<context>
Add two new endpoints to `mealie/routes/optimizer/controller_pantry.py`:

**POST /import-on-hand:**
```python
@router.post("/import-on-hand", response_model=PantryImportResult)
def import_from_on_hand(self) -> PantryImportResult:
    imported, skipped = self.service.import_from_on_hand()
    return PantryImportResult(imported_count=imported, skipped_count=skipped)
```

**POST /deduct:**
```python
@router.post("/deduct", response_model=list[PantryItemOut])
def deduct_recipe(self, data: PantryDeductRequest) -> list[PantryItemOut]:
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    ingredients = get_ingredients_for_recipes(self.session, self.group_id, [data.recipe_id])
    return self.service.deduct_recipe(ingredients)
```

**CRITICAL — Route ordering:** Both endpoints MUST be declared BEFORE `/{item_id}` routes. Place them after `/deficit/meal-plan`.

**Imports to add:** `PantryImportResult`, `PantryDeductRequest`, `PantryItemOut` from schema (PantryItemOut may already be imported).
</context>

<subtasks>
- [ ] Add schema imports (`PantryImportResult`, `PantryDeductRequest`)
- [ ] Add `import_from_on_hand` endpoint before `/{item_id}` routes
- [ ] Add `deduct_recipe` endpoint before `/{item_id}` routes
- [ ] Deduct endpoint uses batch fetch for the single recipe_id
</subtasks>

<acceptance>
- POST /import-on-hand returns `{"importedCount": N, "skippedCount": M}`
- POST /import-on-hand is idempotent (second call returns `importedCount=0`)
- POST /deduct with valid recipe_id returns list of updated pantry items
- POST /deduct with nonexistent recipe_id returns empty list (no error)
- All endpoints require authentication (inherited from BaseCrudController)
- Route ordering: `/import-on-hand` and `/deduct` resolve before `/{item_id}`
- `task py:lint` passes
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] All 4 endpoints respond correctly (test via integration tests or `curl`)
- [ ] Route ordering: `/deficit`, `/deficit/meal-plan`, `/import-on-hand`, `/deduct` all resolve before `/{item_id}`
- [ ] `task py:lint` — no errors
- [ ] Updated integration test for POST /deficit passes with new body shape
</verification>
<gate>All endpoints return correct status codes and response shapes</gate>
</checkpoint>

</phase>

---

## Phase 4: Backend Tests

<phase id="4" name="Backend Tests">

### 4.1 Unit Tests for Expiration Filtering and Deduction

<task id="4.1" status="pending" depends="2.1,2.3" risk="low">
<context>
Extend `tests/unit_tests/services_tests/test_pantry_service.py` with new test classes for expiration filtering and deduction.

**Test instantiation pattern** (from existing file, around lines 80-84):
```python
service = object.__new__(PantryService)
service.converter = UnitConverter()
```
For deduction tests, also mock `service.pantry_items` with a mock repo that tracks updates.

**Factory update needed:** The existing `_make_pantry_item` helper does NOT accept an `expiration_date` parameter (verified in codebase). Add it:
```python
def _make_pantry_item(food, quantity=1.0, unit=None, assume_enough=False, expiration_date=None):
    # ... existing code ...
    item.expiration_date = expiration_date
    return item
```

**Expiration filtering tests (3 tests):**
1. `test_expired_items_excluded_when_flag_set` — Pantry item with `expiration_date` in past, `exclude_expired=True` → item excluded from coverage
2. `test_expired_items_included_when_flag_false` — Same item, `exclude_expired=False` → item included
3. `test_items_without_expiration_always_included` — Item with `expiration_date=None` always included regardless of flag

**Deduction tests (6 tests):**
1. `test_deduct_reduces_pantry_quantity` — 5 in pantry, recipe needs 3 → pantry becomes 2
2. `test_deduct_clamps_to_zero` — 2 in pantry, recipe needs 5 → pantry becomes 0
3. `test_deduct_skips_assume_enough` — `assume_enough=True` → quantity unchanged
4. `test_deduct_skips_untracked_quantity` — `quantity=None` → unchanged
5. `test_deduct_skips_incompatible_units` — Incompatible units → unchanged
6. `test_deduct_handles_unit_conversion` — Recipe in grams, pantry in kg → correctly converts and deducts

**Mocking strategy for deduction tests:** Create a mock for `service.pantry_items` that:
- `.get_all()` returns a predefined list of `PantryItemOut` objects
- `.update(id, item)` records the call (store in a list for later assertion)
Use `unittest.mock.MagicMock` or a simple dataclass stub.
</context>

<subtasks>
- [ ] Add `expiration_date` parameter to `_make_pantry_item` factory
- [ ] Add `ExpirationFilterTests` class with 3 tests
- [ ] Add `DeductRecipeTests` class with 6 tests
- [ ] Mock `service.pantry_items` for deduction tests (needs `.get_all()` and `.update()`)
</subtasks>

<acceptance>
- All new tests pass: `pytest tests/unit_tests/services_tests/test_pantry_service.py -v`
- Existing 12 tests still pass unchanged
- Deduction tests verify both quantity changes and skip conditions
</acceptance>
</task>

### 4.2 Integration Tests for New Endpoints

<task id="4.2" status="pending" depends="3.1,3.2,3.3" risk="medium">
<context>
Extend `tests/integration_tests/user_household_tests/test_pantry_items.py` with integration tests for the new endpoints.

**URL constants to add:**
```python
MEAL_PLAN_DEFICIT_URL = f"{PANTRY_URL}/deficit/meal-plan"
IMPORT_ON_HAND_URL = f"{PANTRY_URL}/import-on-hand"
DEDUCT_URL = f"{PANTRY_URL}/deduct"
```

**Fixture setup strategies** (critical — under-specified in original plan):

For `test_meal_plan_deficit`:
- Create a recipe with ingredients via the recipe API: POST to `/api/recipes` with ingredient data
- Create a meal plan entry via the meal plan API: POST to `/api/households/mealplans` with the recipe_id and a date in range
- Create matching pantry items via the pantry API
- Then POST to `/deficit/meal-plan` with the date range

For `test_import_on_hand`:
- The `ingredient_foods_on_hand` M2M is managed via the household food endpoint. Check how upstream tests populate `on_hand` status — look in `tests/integration_tests/` for files testing food/ingredient on_hand toggles.
- If no upstream API exists for toggling on_hand, use direct DB manipulation via the test's session: insert into `households_to_ingredient_foods` table.
- Alternative: check if `PUT /api/households/ingredient-foods/{food_id}` has an `on_hand` toggle.

For `test_deduct_recipe`:
- Create a recipe with quantified ingredients
- Create pantry items matching those ingredients with known quantities
- POST to `/deduct` with the recipe_id
- Verify pantry quantities decreased correctly

**Tests to add:**

1. `test_deficit_with_exclude_expired` — Create pantry item with past expiration, verify excluded when `excludeExpired: true`
2. `test_meal_plan_deficit` — Create meal plan entries + recipes, verify deficit report
3. `test_meal_plan_deficit_empty_range` — Date range with no meals → 100% coverage
4. `test_import_on_hand` — Mark foods as on_hand, import → verify count
5. `test_import_on_hand_idempotent` — Import twice → second time `importedCount=0`
6. `test_deduct_recipe` — Create pantry items + recipe, deduct → verify reduced quantities

**Note:** The existing `test_deficit_calculation` test should already have been updated in Task 3.1 to use the new request body shape.
</context>

<subtasks>
- [ ] Add URL constants for new endpoints
- [ ] Investigate how to set on_hand foods in test fixtures (check upstream tests or direct DB manipulation)
- [ ] Add test for `exclude_expired` flag
- [ ] Add tests for meal plan deficit (requires recipe + meal plan entry fixtures)
- [ ] Add tests for import-on-hand (requires on_hand food fixtures)
- [ ] Add test for import idempotency
- [ ] Add test for deduct endpoint
</subtasks>

<acceptance>
- All new tests pass: `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v`
- Previously existing tests still pass
- No 500 errors from any endpoint
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `pytest tests/unit_tests/services_tests/test_pantry_service.py -v` — all pass (existing + new)
- [ ] `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v` — all pass
- [ ] `task py:lint` — no errors
</verification>
<gate>All backend tests pass, including both new and existing tests</gate>
</checkpoint>

</phase>

---

## Phase 5: Frontend — Types, API Client, i18n

<phase id="5" name="Frontend">

### 5.1 Add TypeScript Interfaces for New Schemas

<task id="5.1" status="pending" depends="1.2" risk="low">
<context>
Manually add TypeScript interfaces to `frontend/app/lib/api/types/optimizer.ts` for the 4 new Pydantic schemas. No auto-generation pipeline exists for optimizer types — go directly to manual addition.

**Interfaces to add** (following the existing camelCase convention in this file — e.g., `foodId`, `isStaple`, `assumeEnough`):

```typescript
export interface PantryDeficitRequest {
  recipeIds: string[];
  excludeExpired?: boolean;
}

export interface PantryMealPlanDeficitRequest {
  startDate: string;  // ISO date string YYYY-MM-DD
  endDate: string;    // ISO date string YYYY-MM-DD
  excludeExpired?: boolean;
}

export interface PantryImportResult {
  importedCount: number;
  skippedCount: number;
}

export interface PantryDeductRequest {
  recipeId: string;
}
```

**Convention reference:** Pydantic's `MealieModel` uses `alias_generator=to_camel` which produces camelCase JSON keys. The TypeScript interfaces must match these camelCase aliases.
</context>

<subtasks>
- [ ] Add all 4 new interfaces to `optimizer.ts`
- [ ] Verify naming matches camelCase convention used by other interfaces in the file
- [ ] Run `task ui:lint` — verify no errors
</subtasks>

<acceptance>
- All 4 new interfaces exist in `optimizer.ts`
- Field names are camelCase (matching Pydantic alias output)
- `task ui:lint` passes for this file
</acceptance>
</task>

### 5.2 Update API Client Methods

<task id="5.2" status="pending" depends="5.1" risk="low">
<context>
Update `frontend/app/lib/api/user/optimizer-pantry.ts` to add methods for the new endpoints and update the existing `calculateDeficit` method.

**Current state** (verified in codebase):
- Class `PantryItemsApi` extends `BaseCRUDAPI<PantryItemCreate, PantryItemOut, PantryItemUpdate>`
- Has custom method `calculateDeficit(recipeIds: string[])` that POSTs a bare array
- Route constants object with `pantryItems`, `pantryItemsId(id)`, `pantryDeficit`

**Changes needed:**

1. **Update `calculateDeficit`** — change parameter from `recipeIds: string[]` to `data: PantryDeficitRequest`
2. **Add route constants:**
   ```typescript
   pantryMealPlanDeficit: `${prefix}/deficit/meal-plan`,
   pantryImportOnHand: `${prefix}/import-on-hand`,
   pantryDeduct: `${prefix}/deduct`,
   ```
3. **Add methods:**
   ```typescript
   async calculateMealPlanDeficit(data: PantryMealPlanDeficitRequest) {
     return await this.requests.post<PantryDeficitReport>(routes.pantryMealPlanDeficit, data);
   }
   async importFromOnHand() {
     return await this.requests.post<PantryImportResult>(routes.pantryImportOnHand, {});
   }
   async deductRecipe(data: PantryDeductRequest) {
     return await this.requests.post<PantryItemOut[]>(routes.pantryDeduct, data);
   }
   ```

4. **Update callers of `calculateDeficit`:** Search the frontend codebase for calls to `calculateDeficit(` and update them to pass a `PantryDeficitRequest` object instead of a bare array. The pantry page (`pantry.vue`) is the most likely caller.

**Import types:** Add imports for `PantryDeficitRequest`, `PantryMealPlanDeficitRequest`, `PantryImportResult`, `PantryDeductRequest` from `../types/optimizer`.
</context>

<subtasks>
- [ ] Add route constants for new endpoints
- [ ] Update `calculateDeficit` signature to accept `PantryDeficitRequest`
- [ ] Add `calculateMealPlanDeficit` method
- [ ] Add `importFromOnHand` method
- [ ] Add `deductRecipe` method
- [ ] Add type imports from `../types/optimizer`
- [ ] Search for and update all callers of `calculateDeficit` in the frontend
</subtasks>

<acceptance>
- All methods compile without TypeScript errors
- Route paths match backend endpoint paths
- Return types match backend response schemas
- All callers of `calculateDeficit` updated to use new signature
- `task ui:lint` passes
</acceptance>
</task>

### 5.3 Frontend i18n for Pantry Page

<task id="5.3" status="pending" depends="" risk="medium">
<context>
Replace all hardcoded English strings in `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` with i18n translation keys. This task has no backend dependencies and can run in parallel with any other task.

**i18n system:** The project uses vue-i18n via Nuxt i18n module. Translations are in `frontend/app/lang/messages/en-US.json` as a nested JSON object. Pages use `$t('key.subkey')` in templates or `const { t } = useI18n()` in `<script setup>`.

**Step 1 — Read the file to identify all hardcoded strings.** Do NOT rely on line numbers from the plan — they may have drifted. Instead, search for quoted strings in the template that are user-visible English text. Look for patterns like:
- String literals in template text content
- String props like `title="..."`, `label="..."`, `placeholder="..."`
- Dialog text content

**Step 2 — Check for reusable keys.** Before adding new keys, check `en-US.json` for existing general-purpose keys:
- `general.cancel`, `general.add`, `general.delete` may already exist — reuse them

**Step 3 — Add translation keys.** Add an `optimizer.pantry` block to `frontend/app/lang/messages/en-US.json`:
```json
"optimizer": {
  "pantry": {
    "title": "Pantry",
    "add-item": "Add Item",
    "no-items": "No pantry items yet",
    "no-items-description": "Add items to your pantry to track quantities and calculate deficits",
    ...
  }
}
```

**Step 4 — Replace strings in pantry.vue.** Use `$t('optimizer.pantry.title')` in templates or `t('optimizer.pantry.title')` in script.

**IMPORTANT:** Only modify `en-US.json`. Other locale files are community-maintained.
</context>

<subtasks>
- [ ] Read `pantry.vue` to identify all hardcoded English strings (don't trust line numbers)
- [ ] Check `en-US.json` for existing reusable keys (`general.cancel`, `general.add`, `general.delete`)
- [ ] Add `optimizer.pantry.*` keys to `en-US.json` (or add to existing `optimizer` block if present)
- [ ] Set up i18n composable in pantry.vue script section (if not already present)
- [ ] Replace all hardcoded strings with `$t()` calls
- [ ] Verify no hardcoded English user-visible strings remain (exclude technical values: prop names, CSS classes, icon identifiers, v-model attributes)
</subtasks>

<acceptance>
- No hardcoded English user-visible strings remain in `pantry.vue`
- All strings use `$t()` with `optimizer.pantry.*` or `general.*` namespace
- `en-US.json` contains all required keys with English values
- Page renders identically to before (English text unchanged visually)
- `task ui:lint` passes
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] TypeScript types compile: `task ui:lint` passes
- [ ] API client methods match backend endpoints
- [ ] Pantry page renders correctly with i18n
- [ ] No hardcoded strings remain in pantry.vue
- [ ] Start frontend dev server (`task ui`) and manually verify pantry page loads
</verification>
<gate>Frontend compiles, lints clean, and pantry page renders correctly</gate>
</checkpoint>

</phase>

---

## Phase 6: End-to-End Validation

<phase id="6" name="End-to-End Validation">

### 6.1 Full Test Suite Run

<task id="6.1" status="pending" depends="4.1,4.2,5.2,5.3" risk="low">
<context>
Run the complete test suite and lint checks to verify no regressions.

**Commands to run in sequence:**
```bash
task py:lint
task ui:lint
pytest tests/unit_tests/services_tests/test_pantry_service.py -v
pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v
```

If any test fails, diagnose and fix before proceeding. Do not skip failures.
</context>

<subtasks>
- [ ] Run Python linting — `task py:lint`
- [ ] Run frontend linting — `task ui:lint`
- [ ] Run pantry unit tests — `pytest tests/unit_tests/services_tests/test_pantry_service.py -v`
- [ ] Run pantry integration tests — `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v`
- [ ] Fix any failures before proceeding
</subtasks>

<acceptance>
- All lint checks pass with zero errors
- All unit tests pass
- All integration tests pass
- No regressions in existing functionality
</acceptance>
</task>

### 6.2 End-to-End Verification

<task id="6.2" status="pending" depends="6.1" risk="low">
<context>
Start the dev servers and verify the feature works end-to-end. This is a mix of automated verification (curl/API calls) and manual UI checks.

**Automated verification (agent-executable):**
1. Start services: `task dev:services` then `task py:postgres`
2. Test POST /deficit via curl:
   ```bash
   curl -s -X POST http://localhost:9000/api/optimizer/pantry/deficit \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"recipeIds": [], "excludeExpired": false}'
   ```
3. Test POST /import-on-hand via curl:
   ```bash
   curl -s -X POST http://localhost:9000/api/optimizer/pantry/import-on-hand \
     -H "Authorization: Bearer $TOKEN"
   ```
4. Test POST /deduct via curl (with a known recipe_id)
5. Verify no 500 errors in backend logs

**Manual verification (requires human or browser):**
1. Start frontend: `task ui`
2. Navigate to pantry page in browser
3. Verify pantry CRUD still works
4. Verify page text displays correctly (i18n rendered)
5. Check browser console for errors
</context>

<subtasks>
- [ ] Start dev services and backend
- [ ] Test deficit endpoint via curl
- [ ] Test import-on-hand endpoint via curl
- [ ] Test deduct endpoint via curl
- [ ] Start frontend and verify pantry page loads (if browser available)
- [ ] Check for console/backend errors
</subtasks>

<acceptance>
- All API endpoints return expected response shapes (no 500 errors)
- Pantry page loads without errors
- CRUD operations work
- No regressions in existing functionality
</acceptance>
</task>

</phase>

---

## Risk Mitigation

<risks>
<risk id="R1" likelihood="medium" impact="high">
  <description>POST /deficit body shape change breaks frontend before Task 5.2 updates the API client</description>
  <mitigation>Tasks 3.1 and 5.2 should be completed in the same working session. Do not deploy backend changes without corresponding frontend updates.</mitigation>
  <detection>Frontend deficit calculation returns 422 errors. Integration test for deficit updated in Task 3.1 catches backend-side issues.</detection>
</risk>
<risk id="R2" likelihood="low" impact="medium">
  <description>Batch recipe fetch (selectinload chain) does not eager-load deeply enough, causing lazy-load errors in calculate_deficit</description>
  <mitigation>Task 1.1 specifies the full selectinload chain. Verify by accessing .food.id and .unit.standard_unit on returned objects in a test.</mitigation>
  <detection>AttributeError or DetachedInstanceError when calculate_deficit accesses ingredient food/unit attributes</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>import_from_on_hand creates duplicate pantry items if concurrent requests bypass the pre-fetch check</description>
  <mitigation>Acceptable for single-user fork. The pre-fetch conflict avoidance is sufficient for non-concurrent usage. If needed later, add a unique constraint on (household_id, food_id) to the pantry table.</mitigation>
  <detection>Multiple pantry items for the same food_id visible in the UI</detection>
</risk>
<risk id="R4" likelihood="medium" impact="low">
  <description>Partial deduction committed if deduct_recipe fails midway (non-atomic updates)</description>
  <mitigation>Documented in code. User can manually adjust quantities. For future improvement, investigate update_many batch commit behavior.</mitigation>
  <detection>Pantry quantities don't match expected values after deduction</detection>
</risk>
<risk id="R5" likelihood="low" impact="low">
  <description>Meal plan repository accessor name differs from expected (self.repos.meals vs self.repos.meal_plans)</description>
  <mitigation>Task 3.2 includes a subtask to verify the accessor name in all_repositories.py before implementing</mitigation>
  <detection>AttributeError at runtime when accessing the meals repository</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] All unit tests pass: `pytest tests/unit_tests/services_tests/test_pantry_service.py -v`
- [ ] All integration tests pass: `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v`
- [ ] Python linting passes: `task py:lint`
- [ ] Frontend linting passes: `task ui:lint`
- [ ] End-to-end verification completed (automated + manual)
- [ ] No regressions in existing pantry CRUD functionality
- [ ] All new files are in `optimizer/` subdirectories (fork isolation maintained)
- [ ] CLAUDE.md "Modified Upstream Files" list has not grown
</verification>
<acceptance>All 4 new endpoints work correctly, expiration filtering is functional, pantry page is internationalized, and all tests pass.</acceptance>
</final_validation>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should POST /deficit remain backward-compatible by accepting both list[UUID4] and PantryDeficitRequest, or is a clean break acceptable?</question>
  <default_assumption>Clean break — wrap in PantryDeficitRequest. Fork has no external consumers. Frontend updates in Task 5.2.</default_assumption>
  <impact>If backward compatibility needed, must add Union type handling in controller; if clean break, frontend must update simultaneously.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should meal plan deficit deduplicate by recipe_id only, or should repeated recipes multiply their ingredient requirements?</question>
  <default_assumption>Deduplicate — deficit answers "what ingredients do I need for these unique recipes." A recipe appearing 3 times in the meal plan still only counts once.</default_assumption>
  <impact>Deduplication answers "what unique ingredients do I need?" — multiplication answers "how much total do I need for N servings?" If users expect multiplication, the endpoint behavior will be surprising.</impact>
</question>
<question id="Q3" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should pantry deduction happen automatically when a recipe is marked as cooked, or only via explicit POST /deduct?</question>
  <default_assumption>Explicit POST /deduct only — avoids upstream modifications to recipe/meal-plan flows.</default_assumption>
  <impact>Automatic deduction requires wiring into upstream code, increasing the modified-upstream-files footprint.</impact>
</question>
<question id="Q4" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>For bulk import, should imported items default to assume_enough=False (quantity-untracked) or should the user choose?</question>
  <default_assumption>Default assume_enough=False, quantity=None — simple migration path, user can toggle later.</default_assumption>
  <impact>User choice adds UI complexity to the import flow; default keeps it to a single button click.</impact>
</question>
<question id="Q5" blocking="false" owner="agent" inherited_from="docs/plans/2026-04-13-192743-pantry-quantity-tracking-completion.md">
  <question>What should happen on unit conversion failure during deduct: skip the item silently, or include it in a failure list in the response?</question>
  <default_assumption>Skip silently — consistent with deficit calculation behavior. The returned list only includes successfully deducted items; caller can diff to detect skips.</default_assumption>
  <impact>Silent skip is simpler but gives no feedback. Failure list would require adding a response schema change (e.g., DeductResult with deducted + skipped lists).</impact>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
<resolved original_question="Should the is_staple field UI be included in this spec or deferred further?">
  <resolution>Deferred per spec — no feature currently depends on is_staple, and UX design for staple vs always-available is undecided. Not included in this plan.</resolution>
</resolved>
</resolved_from_source>

<resolved_from_source source="docs/plans/2026-04-13-192743-pantry-quantity-tracking-completion.md">
<resolved original_question="Should batch fetch unit tests use mock session or integration-style tests?">
  <resolution>Eliminated during revision. Batch fetch unit tests (original Task 4.1) removed entirely — mocking SQLAlchemy session queries is fragile and tests the mock, not the code. The batch fetch helper is covered by integration tests for POST /deficit and POST /deduct in Task 4.2.</resolution>
</resolved>
<resolved original_question="Should conversion failure UI be added to PantryItemRow?">
  <resolution>Deferred during revision. PantryItemRow is an item editor, not a deficit results display. Adding a conversionFailed prop creates dead code with no wiring. This belongs in a future task that builds a deficit results view component.</resolution>
</resolved>
</resolved_from_source>
