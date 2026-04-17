# Implementation Plan: Pantry Quantity Tracking Completion

Source: docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md
Created: 2026-04-13

<plan_metadata>
  <feature>Pantry Quantity Tracking Completion</feature>
  <source_doc>docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md</source_doc>
  <total_phases>6</total_phases>
  <total_tasks>16</total_tasks>
  <critical_path>1.1 → 2.1 → 3.1 → 3.2 → 4.3 → 5.1 → 5.2</critical_path>
  <status>reviewed</status>
</plan_metadata>

## Overview

Complete the pantry quantity tracking feature by addressing the N+1 recipe fetch (batch helper), adding four new API endpoints (refactored deficit, meal plan deficit, import-on-hand, deduct), extending the service layer with expiration filtering / bulk import / pantry deduction, and updating the frontend with TypeScript types, API client methods, conversion failure UI, and i18n. All new backend code lives in `optimizer/` subdirectories per fork isolation rules.

## Dependencies & Prerequisites

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
  <description>PantryItemModel already has all required DB columns (food_id, quantity, unit_id, assume_enough, is_staple, expiration_date). No Alembic migration needed.</description>
  <verification>Read mealie/db/models/optimizer/pantry.py — all columns present</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>UnitConverter (pint-based) available at mealie/services/parser_services/parser_utils/unit_utils.py</description>
  <verification>Already imported and used in PantryService.__init__</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>RepositoryMeals.get_meals_by_date_range(datetime, datetime) returns list[ReadPlanEntry] with recipe_id: UUID | None</description>
  <verification>Read mealie/repos/repository_meals.py lines 23-33</verification>
</prereq>
<prereq id="P6" type="data" verified="true">
  <description>households_to_ingredient_foods join table exists with unique constraint on (household_id, food_id)</description>
  <verification>Read mealie/db/models/recipe/ingredient.py lines 21-27</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend Foundation — Schemas & Batch Fetch Helper

<phase id="1" name="Backend Foundation">

### 1.1 Create Batch Recipe Ingredient Fetcher

<task id="1.1" status="pending" depends="" risk="medium">
<description>
Create a new file `mealie/services/optimizer/recipe_utils.py` containing a function that batch-fetches all ingredients for a list of recipe IDs in a single SQL query, replacing the current N+1 pattern in the deficit endpoint.

**Current problem** (controller_pantry.py lines 47-53): The deficit endpoint loops through recipe_ids and calls `group_repos.recipes.get_one(recipe_id)` per ID — an N+1 query.

**Implementation details:**
- Function signature: `get_ingredients_for_recipes(session: Session, group_id: UUID4, recipe_ids: list[UUID4]) -> list[RecipeIngredient]`
- Use `select(RecipeModel).where(RecipeModel.id.in_(recipe_ids), RecipeModel.group_id == group_id)` — the `group_id` filter is **critical** for tenant isolation (Codex review finding)
- Must eagerly load the full ingredient subgraph: `selectinload(RecipeModel.recipe_ingredient).selectinload(RecipeIngredientModel.food)` and `.selectinload(RecipeIngredientModel.unit)` to avoid lazy-load N+1 when `calculate_deficit` accesses `ingredient.food.id` and `ingredient.unit.standard_unit`
- Return empty list for empty `recipe_ids` input (short-circuit before querying)
- Silently skip recipe_ids that don't exist (no error)
- Convert SQLAlchemy models to Pydantic `RecipeIngredient` schemas before returning

**File references:**
- RecipeModel: `mealie/db/models/recipe/recipe.py` — has `recipe_ingredient` relationship (line 103)
- RecipeIngredientModel: `mealie/db/models/recipe/ingredient.py` — has `food` and `unit` relationships
- RecipeIngredient schema: `mealie/schema/recipe/recipe_ingredient.py` line 330
</description>

<subtasks>
- [ ] Create `mealie/services/optimizer/recipe_utils.py`
- [ ] Import RecipeModel, RecipeIngredientModel, RecipeIngredient schema, selectinload
- [ ] Implement `get_ingredients_for_recipes` with group_id scoping and eager loading
- [ ] Short-circuit on empty recipe_ids
- [ ] Add `__init__.py` update if needed for optimizer services package
</subtasks>

<acceptance>
- Single SQL query (verify via SQLAlchemy echo or count) instead of N get_one calls
- Returns empty list for `recipe_ids=[]`
- Silently skips nonexistent recipe_ids
- Returned RecipeIngredient objects have populated `.food` and `.unit` attributes
- group_id filter is present in the WHERE clause
</acceptance>
</task>

### 1.2 Add New Request/Response Schemas

<task id="1.2" status="pending" depends="" risk="low">
<description>
Add four new Pydantic schemas to `mealie/schema/optimizer/pantry.py` for the new endpoints. These wrap request bodies properly instead of using bare types.

**Schemas to add:**

1. `PantryDeficitRequest(MealieModel)` — replaces the current bare `list[UUID4]` parameter
   - `recipe_ids: list[UUID4]`
   - `exclude_expired: bool = False` (defaults False for backward compatibility)

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

**File reference:** `mealie/schema/optimizer/pantry.py` — currently has 8 schemas (lines 1-104). Add the new schemas at the end of the file, before any `__all__` if present.

**Import needed:** `from datetime import date` and `from pydantic import model_validator`
</description>

<subtasks>
- [ ] Add `from datetime import date` import
- [ ] Add `from pydantic import model_validator` import (check if already imported)
- [ ] Add PantryDeficitRequest class
- [ ] Add PantryMealPlanDeficitRequest class with date range validator
- [ ] Add PantryImportResult class
- [ ] Add PantryDeductRequest class
</subtasks>

<acceptance>
- All four schemas instantiate without error
- `PantryDeficitRequest(recipe_ids=[])` works with default `exclude_expired=False`
- `PantryMealPlanDeficitRequest(start_date=date(2026,1,1), end_date=date(2025,12,31))` raises ValidationError
- `PantryMealPlanDeficitRequest(start_date=date(2026,1,1), end_date=date(2026,1,1))` succeeds (same day is valid)
- `PantryImportResult(imported_count=5, skipped_count=2)` works
- `PantryDeductRequest(recipe_id=uuid4())` works
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `mealie/services/optimizer/recipe_utils.py` exists with `get_ingredients_for_recipes` function
- [ ] `mealie/schema/optimizer/pantry.py` contains all 4 new schema classes
- [ ] `from mealie.schema.optimizer.pantry import PantryDeficitRequest, PantryMealPlanDeficitRequest, PantryImportResult, PantryDeductRequest` succeeds
- [ ] `from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes` succeeds
- [ ] Run `task py:lint` — no errors in new/modified files
</verification>
<success_criteria>Both new files/schemas are importable and pass linting</success_criteria>
</checkpoint>

</phase>

---

## Phase 2: Service Layer — Expiration, Import, Deduction

<phase id="2" name="Service Layer" depends="1">

### 2.1 Add Expiration Filtering to calculate_deficit

<task id="2.1" status="pending" depends="1.2" risk="low">
<description>
Extend the existing `calculate_deficit` method in `mealie/services/optimizer/pantry.py` (line 49) to accept an `exclude_expired: bool = False` parameter. When True, filter out pantry items where `expiration_date is not None and expiration_date < date.today()` before building the pantry map.

**Current signature** (line 49):
```python
def calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None) -> PantryDeficitReport:
```

**New signature:**
```python
def calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None, exclude_expired: bool = False) -> PantryDeficitReport:
```

**Implementation:** After fetching/receiving `pantry_items` but before building the `pantry_map` dict, add a filter step:
```python
if exclude_expired:
    today = date.today()
    pantry_items = [p for p in pantry_items if p.expiration_date is None or p.expiration_date >= today]
```

**Critical:** Default `False` ensures existing callers (shopping list integration at `mealie/services/household_services/shopping_lists.py:178-184`) are unaffected.
</description>

<subtasks>
- [ ] Add `from datetime import date` import if not present
- [ ] Add `exclude_expired: bool = False` parameter to `calculate_deficit`
- [ ] Add filtering logic after pantry_items are resolved but before pantry_map construction
</subtasks>

<acceptance>
- Calling `calculate_deficit(ingredients, exclude_expired=False)` behaves identically to current implementation
- Calling `calculate_deficit(ingredients, exclude_expired=True)` excludes items with `expiration_date < today`
- Items with `expiration_date=None` are always included regardless of flag
- Existing unit tests still pass unchanged
</acceptance>
</task>

### 2.2 Add import_from_on_hand Method

<task id="2.2" status="pending" depends="1.2" risk="medium">
<description>
Add a new method `import_from_on_hand` to PantryService in `mealie/services/optimizer/pantry.py` that reads the household's `ingredient_foods_on_hand` M2M relationship and creates PantryItem records for foods not already tracked.

**Access pattern** (validated with Codex): Query the HouseholdModel directly via session:
```python
from mealie.db.models.household.household import Household as HouseholdModel
from sqlalchemy.orm import selectinload

household = self.repos.session.get(
    HouseholdModel,
    self.repos.household_id,
    options=[selectinload(HouseholdModel.ingredient_foods_on_hand)]
)
```

**Important:** Also verify `household.group_id == self.repos.group_id` for tenant isolation (Codex review finding).

**Logic:**
1. Get all food_ids currently in pantry: `existing_food_ids = {item.food_id for item in self.pantry_items.get_all()}`
   - Note: `get_all()` on HouseholdRepositoryGeneric already filters by household_id
2. Get on_hand food IDs from household relationship
3. For each on_hand food_id not in existing_food_ids, create a PantryItemSave with:
   - `food_id=food.id`, `name=None`, `quantity=None`, `unit_id=None`
   - `assume_enough=False`, `is_staple=False`, `expiration_date=None`
   - `group_id=self.repos.group_id`, `household_id=self.repos.household_id`
4. Bulk create via repo (use `create_many` if available, or loop `create_one`)
5. Return `(imported_count, skipped_count)`

**Schema reference:** PantryItemSave at `mealie/schema/optimizer/pantry.py` lines 44-46 — extends PantryItemCreate, adds group_id and household_id.

**Edge cases:**
- Empty on_hand list → return (0, 0)
- All on_hand foods already in pantry → return (0, N)
- Household not found → raise or return (0, 0) — should not happen in authenticated context
</description>

<subtasks>
- [ ] Add imports: HouseholdModel, selectinload, PantryItemSave
- [ ] Implement `import_from_on_hand(self) -> tuple[int, int]`
- [ ] Query household model with eager-loaded ingredient_foods_on_hand
- [ ] Validate group_id matches for tenant isolation
- [ ] Fetch existing pantry food_ids in a single query
- [ ] Create new PantryItem for each missing food
- [ ] Return (imported_count, skipped_count)
</subtasks>

<acceptance>
- Creates PantryItems only for foods not already in pantry
- Handles empty on_hand list gracefully (returns 0, 0)
- Each imported item has quantity=None, assume_enough=False
- group_id/household_id are set correctly on imported items
- Second call with same data returns (0, N) — idempotent
</acceptance>

<rollback risk="medium">
If import creates incorrect items, they can be deleted via the existing DELETE /{item_id} endpoint. No schema changes involved.
</rollback>
</task>

### 2.3 Add deduct_recipe Method

<task id="2.3" status="pending" depends="1.2" risk="medium">
<description>
Add a new method `deduct_recipe` to PantryService in `mealie/services/optimizer/pantry.py` that subtracts recipe ingredient quantities from matching pantry items.

**Signature:** `def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]`

**Transaction handling** (Codex review): All updates must be atomic — either all deductions succeed or none persist. Use the existing session transaction pattern. Collect all updates, then persist together:

```python
updates: list[PantryItemOut] = []
# ... compute all deductions ...
for item in updates:
    self.pantry_items.update(item.id, item)  # uses repo's session
# Session commit handled by controller/middleware
```

**Deduction rules:**
1. Skip ingredients with no `food` or `food.id` (no food to match)
2. Build a pantry map: `{food_id: PantryItemOut}` from `self.pantry_items.get_all()`
3. For each ingredient with a matching pantry item:
   - Skip if `pantry_item.assume_enough is True` (don't deduct from "always available")
   - Skip if `pantry_item.quantity is None` (untracked quantity)
   - Attempt unit conversion if units differ:
     - Get pantry unit's `standard_unit` and recipe unit's `standard_unit`
     - Use `self.converter.can_convert()` to check compatibility
     - If incompatible: **skip** (don't deduct — consistent with deficit rule 7)
     - If compatible: convert recipe quantity to pantry unit, then subtract
   - Clamp: `pantry_item.quantity = max(0.0, pantry_item.quantity - converted_qty)`
4. Persist all changed items via repository update
5. Return list of updated PantryItemOut objects

**Conversion failure behavior** (Codex suggestion): Skip items with incompatible units silently — consistent with how calculate_deficit handles conversion_failed items. The response includes only successfully deducted items, allowing the caller to diff against expectations.
</description>

<subtasks>
- [ ] Implement `deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]`
- [ ] Build pantry map from repository
- [ ] Iterate ingredients, match to pantry items by food_id
- [ ] Apply skip rules (no food, assume_enough, None quantity, incompatible units)
- [ ] Convert units where needed using self.converter
- [ ] Clamp quantity to 0 (never negative)
- [ ] Persist changes atomically via repository update
- [ ] Return list of updated items
</subtasks>

<acceptance>
- Deduction reduces pantry quantity correctly for same-unit case
- Deduction handles unit conversion (e.g., recipe in grams, pantry in kg)
- Quantity never goes below 0
- assume_enough items are untouched
- None-quantity items are untouched
- Incompatible-unit items are untouched (skipped)
- Returned list contains only items that were actually modified
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `calculate_deficit` accepts `exclude_expired` parameter
- [ ] `import_from_on_hand` method exists on PantryService
- [ ] `deduct_recipe` method exists on PantryService
- [ ] Run `task py:lint` — no errors in modified files
- [ ] Existing unit tests (`tests/unit_tests/services_tests/test_pantry_service.py`) still pass
</verification>
<success_criteria>All three service methods are implemented and existing tests pass unchanged</success_criteria>
</checkpoint>

</phase>

---

## Phase 3: Controller Endpoints

<phase id="3" name="Controller Endpoints" depends="2">

### 3.1 Refactor Deficit Endpoint + Add Meal Plan Deficit

<task id="3.1" status="pending" depends="2.1,1.1" risk="medium">
<description>
Modify `mealie/routes/optimizer/controller_pantry.py` to:

1. **Refactor POST /deficit** (lines 44-55): Change request body from bare `list[UUID4]` to `PantryDeficitRequest`. Use the new batch fetch helper instead of N+1 loop.

2. **Add POST /deficit/meal-plan**: New endpoint that extracts recipe_ids from meal plan entries in a date range, then delegates to `calculate_deficit`.

**CRITICAL — Route ordering:** Both `/deficit` and `/deficit/meal-plan` must be declared BEFORE any `/{item_id}` routes. Currently `/deficit` is at line 44, before the `/{item_id}` routes. The new `/deficit/meal-plan` must also be before `/{item_id}`.

**Refactored deficit endpoint:**
```python
@router.post("/deficit", response_model=PantryDeficitReport)
def calculate_deficit(self, data: PantryDeficitRequest) -> PantryDeficitReport:
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, data.recipe_ids)
    return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)
```

**Meal plan deficit endpoint:**
```python
@router.post("/deficit/meal-plan", response_model=PantryDeficitReport)
def calculate_meal_plan_deficit(self, data: PantryMealPlanDeficitRequest) -> PantryDeficitReport:
    from datetime import datetime
    # get_meals_by_date_range takes datetime objects
    start_dt = datetime.combine(data.start_date, datetime.min.time())
    end_dt = datetime.combine(data.end_date, datetime.max.time())
    meals = self.repos.meals.get_meals_by_date_range(start_dt, end_dt)
    recipe_ids = list({m.recipe_id for m in meals if m.recipe_id is not None})
    
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, recipe_ids)
    return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)
```

**Note on deduplication:** `recipe_ids` are deduplicated via set — each unique recipe counts once. This is a deliberate design choice (see Q2 in open questions).

**Imports to add:** `PantryDeficitRequest`, `PantryMealPlanDeficitRequest` from schema, and `get_ingredients_for_recipes` from recipe_utils.
</description>

<subtasks>
- [ ] Add schema imports (PantryDeficitRequest, PantryMealPlanDeficitRequest)
- [ ] Refactor `calculate_deficit` endpoint to accept PantryDeficitRequest body
- [ ] Replace N+1 loop with `get_ingredients_for_recipes` call
- [ ] Pass `exclude_expired` through to service
- [ ] Add `calculate_meal_plan_deficit` endpoint before `/{item_id}` routes
- [ ] Convert date to datetime for `get_meals_by_date_range`
- [ ] Filter out None recipe_ids from meal plan entries
- [ ] Deduplicate recipe_ids
</subtasks>

<acceptance>
- POST /deficit with `{"recipe_ids": [...], "exclude_expired": false}` returns deficit report
- POST /deficit with `{"recipe_ids": []}` returns empty report with 100% coverage
- POST /deficit/meal-plan with valid date range returns deficit report
- POST /deficit/meal-plan with no recipes in range returns 100% coverage report
- POST /deficit/meal-plan with start_date > end_date returns 422 validation error
- Both endpoints require authentication (inherited from BaseCrudController)
</acceptance>

<rollback risk="medium">
The POST /deficit body shape is a breaking change (from list[UUID4] to object). If frontend is not updated simultaneously, the deficit feature will break. Ensure Phase 5 (frontend) updates the API client before testing end-to-end.
</rollback>
</task>

### 3.2 Add Import and Deduct Endpoints

<task id="3.2" status="pending" depends="2.2,2.3" risk="low">
<description>
Add two new endpoints to `mealie/routes/optimizer/controller_pantry.py`:

1. **POST /import-on-hand** — Triggers bulk import of on_hand foods as pantry items
2. **POST /deduct** — Deducts recipe ingredient quantities from pantry

**CRITICAL — Route ordering:** Both endpoints must be declared BEFORE `/{item_id}` routes.

**Import endpoint:**
```python
@router.post("/import-on-hand", response_model=PantryImportResult)
def import_from_on_hand(self) -> PantryImportResult:
    imported, skipped = self.service.import_from_on_hand()
    return PantryImportResult(imported_count=imported, skipped_count=skipped)
```

**Deduct endpoint:**
```python
@router.post("/deduct", response_model=list[PantryItemOut])
def deduct_recipe(self, data: PantryDeductRequest) -> list[PantryItemOut]:
    from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes
    ingredients = get_ingredients_for_recipes(self.session, self.group_id, [data.recipe_id])
    return self.service.deduct_recipe(ingredients)
```

**Imports to add:** `PantryImportResult`, `PantryDeductRequest` from schema.
</description>

<subtasks>
- [ ] Add schema imports (PantryImportResult, PantryDeductRequest)
- [ ] Add `import_from_on_hand` endpoint before `/{item_id}` routes
- [ ] Add `deduct_recipe` endpoint before `/{item_id}` routes
- [ ] Deduct endpoint uses batch fetch for the single recipe_id
</subtasks>

<acceptance>
- POST /import-on-hand returns `{"imported_count": N, "skipped_count": M}`
- POST /import-on-hand is idempotent (second call returns imported_count=0)
- POST /deduct with valid recipe_id returns list of updated pantry items
- POST /deduct with nonexistent recipe_id returns empty list (no error)
- All endpoints require authentication
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] All 4 new/refactored endpoints respond correctly via manual curl or test client
- [ ] Route ordering: `/deficit`, `/deficit/meal-plan`, `/import-on-hand`, `/deduct` all resolve before `/{item_id}`
- [ ] Run `task py:lint` — no errors
- [ ] Existing integration tests still pass (they may need update if they test POST /deficit body shape)
</verification>
<success_criteria>All endpoints return correct status codes and response shapes</success_criteria>
</checkpoint>

</phase>

---

## Phase 4: Backend Tests

<phase id="4" name="Backend Tests" depends="3">

### 4.1 Unit Tests for Batch Fetch Helper

<task id="4.1" status="pending" depends="1.1" risk="low">
<description>
Create `tests/unit_tests/services_tests/test_recipe_utils.py` with tests for the batch ingredient fetcher. Since this helper requires a real SQLAlchemy session, these tests may need to mock the session or use the existing test database pattern.

**Test pattern reference:** Look at how `tests/unit_tests/services_tests/test_pantry_service.py` tests without DB (lines 80-84: `object.__new__` pattern). However, `get_ingredients_for_recipes` is a standalone function taking a session, so tests will likely need a mock session or can be integration-style.

**Alternative:** If mocking the session is too complex, these tests can be folded into the integration test file instead. Use judgment based on complexity.

**Tests to write:**
1. `test_returns_all_ingredients_for_multiple_recipes` — Mock session to return 2 recipes with ingredients, verify flattened list
2. `test_returns_empty_for_empty_input` — Empty recipe_ids → empty list, no session query
3. `test_skips_nonexistent_recipe_ids` — Session returns fewer recipes than IDs provided → no error, returns only found ingredients
</description>

<subtasks>
- [ ] Create `tests/unit_tests/services_tests/test_recipe_utils.py`
- [ ] Implement test for multiple recipes
- [ ] Implement test for empty input
- [ ] Implement test for nonexistent recipe IDs
</subtasks>

<acceptance>
- All tests pass via `pytest tests/unit_tests/services_tests/test_recipe_utils.py`
- Tests verify correct behavior without requiring a running database (mock session) OR are clearly labeled as integration-style
</acceptance>
</task>

### 4.2 Unit Tests for Expiration Filtering and Deduction

<task id="4.2" status="pending" depends="2.1,2.3" risk="low">
<description>
Extend `tests/unit_tests/services_tests/test_pantry_service.py` with new test classes for expiration filtering and deduction.

**Test instantiation pattern** (lines 80-84 of existing file):
```python
service = object.__new__(PantryService)
service.converter = UnitConverter()
```
For deduction tests, also mock `service.pantry_items` with a mock repo that tracks updates.

**Expiration filtering tests (add to existing file):**
1. `test_expired_items_excluded_when_flag_set` — Pantry item with expiration_date in past, exclude_expired=True → item excluded from coverage
2. `test_expired_items_included_when_flag_false` — Same item, exclude_expired=False → item included
3. `test_items_without_expiration_always_included` — Item with expiration_date=None always included regardless of flag

**Deduction tests (add to existing file):**
1. `test_deduct_reduces_pantry_quantity` — 5 in pantry, recipe needs 3 → pantry becomes 2
2. `test_deduct_clamps_to_zero` — 2 in pantry, recipe needs 5 → pantry becomes 0
3. `test_deduct_skips_assume_enough` — assume_enough=True → quantity unchanged
4. `test_deduct_skips_untracked_quantity` — quantity=None → unchanged
5. `test_deduct_skips_incompatible_units` — Incompatible units → unchanged
6. `test_deduct_handles_unit_conversion` — Recipe in grams, pantry in kg → correctly converts and deducts

**Helper factory reference:** Use existing `_make_ingredient`, `_make_pantry_item` factories (lines 15-66).
- `_make_pantry_item` may need an `expiration_date` parameter added if not already present
</description>

<subtasks>
- [ ] Add `expiration_date` parameter to `_make_pantry_item` factory if needed
- [ ] Add ExpirationFilterTests class with 3 tests
- [ ] Add DeductRecipeTests class with 6 tests
- [ ] Mock `service.pantry_items` for deduction tests (needs `.get_all()` and `.update()`)
</subtasks>

<acceptance>
- All new tests pass: `pytest tests/unit_tests/services_tests/test_pantry_service.py -v`
- Existing 12 tests still pass unchanged
- Deduction tests verify both quantity changes and skip conditions
</acceptance>
</task>

### 4.3 Integration Tests for New Endpoints

<task id="4.3" status="pending" depends="3.1,3.2" risk="low">
<description>
Extend `tests/integration_tests/user_household_tests/test_pantry_items.py` with integration tests for the new endpoints.

**URL constants to add:**
```python
MEAL_PLAN_DEFICIT_URL = f"{PANTRY_URL}/deficit/meal-plan"
IMPORT_ON_HAND_URL = f"{PANTRY_URL}/import-on-hand"
DEDUCT_URL = f"{PANTRY_URL}/deduct"
```

**Test pattern** (from existing file): Use `api_client.post(URL, json=payload, headers=unique_user.token)` and assert on `response.status_code` and `response.json()`.

**IMPORTANT:** The existing `test_deficit_calculation` test (sends bare list to POST /deficit) must be updated to send `{"recipeIds": [], "excludeExpired": false}` instead of bare `[]`.

**Tests to add:**

1. `test_deficit_with_request_schema` — POST /deficit with PantryDeficitRequest body shape (update existing test)
2. `test_deficit_with_exclude_expired` — Create pantry item with past expiration, verify excluded when excludeExpired=true
3. `test_meal_plan_deficit` — Create meal plan entries with recipes, verify deficit covers those recipes
4. `test_meal_plan_deficit_empty_range` — Date range with no meals → 100% coverage
5. `test_import_on_hand` — Mark foods as on_hand, import → verify count
6. `test_import_on_hand_idempotent` — Import twice → second time imported_count=0
7. `test_deduct_recipe` — Create pantry items + recipe, deduct → verify reduced quantities
</description>

<subtasks>
- [ ] Add URL constants for new endpoints
- [ ] Update existing deficit test for new request body shape
- [ ] Add test for exclude_expired flag
- [ ] Add tests for meal plan deficit (requires creating meal plan entries and recipes as test fixtures)
- [ ] Add tests for import-on-hand (requires setting up on_hand foods via the existing ingredient_foods API)
- [ ] Add test for import idempotency
- [ ] Add test for deduct endpoint
</subtasks>

<acceptance>
- All new tests pass: `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v`
- Existing tests pass (with updated deficit body shape)
- No 500 errors from any endpoint
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `pytest tests/unit_tests/services_tests/test_pantry_service.py -v` — all pass (existing + new)
- [ ] `pytest tests/unit_tests/services_tests/test_recipe_utils.py -v` — all pass
- [ ] `pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v` — all pass
- [ ] `task py:lint` — no errors
</verification>
<success_criteria>All backend tests pass, including both new and existing tests</success_criteria>
</checkpoint>

</phase>

---

## Phase 5: Frontend — Types, API Client, UI

<phase id="5" name="Frontend" depends="3">

### 5.1 Update TypeScript Types

<task id="5.1" status="pending" depends="1.2" risk="low">
<description>
Update `frontend/app/lib/api/types/optimizer.ts` with TypeScript interfaces for the 4 new Pydantic schemas.

**Option A (preferred):** Run `task dev:generate` which executes `dev/code-generation/main.py` to auto-generate types from the OpenAPI spec. If this picks up the optimizer schemas, use the generated output.

**Option B (fallback):** If `task dev:generate` doesn't generate optimizer types (likely since they may not be in the generation config), manually add the interfaces following the existing camelCase convention.

**Interfaces to add/verify:**
```typescript
export interface PantryDeficitRequest {
  recipeIds: string[];
  excludeExpired?: boolean;
}

export interface PantryMealPlanDeficitRequest {
  startDate: string;  // ISO date string
  endDate: string;    // ISO date string
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

**Convention reference:** Existing interfaces in this file use camelCase (e.g., `foodId`, `isStaple`, `assumeEnough`). Pydantic's `model_config` with `alias_generator=to_camel` produces these.
</description>

<subtasks>
- [ ] Try `task dev:generate` first — check if optimizer types are updated
- [ ] If not auto-generated, manually add the 4 new interfaces
- [ ] Verify naming matches camelCase convention
</subtasks>

<acceptance>
- All 4 new interfaces exist in optimizer.ts
- Field names are camelCase
- `task ui:lint` passes for this file
</acceptance>
</task>

### 5.2 Update API Client Methods

<task id="5.2" status="pending" depends="5.1" risk="low">
<description>
Update `frontend/app/lib/api/user/optimizer-pantry.ts` to add methods for the new endpoints and update the existing `calculateDeficit` method.

**Current file structure:**
- Class `PantryItemsApi extends BaseCRUDAPI<PantryItemCreate, PantryItemOut, PantryItemUpdate>`
- Has custom method `calculateDeficit(recipeIds: string[])` that POSTs bare array
- Route constants: `pantryItems`, `pantryItemsId(id)`, `pantryDeficit`

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

**Import types:** Add imports for the new interfaces from `../types/optimizer`.
</description>

<subtasks>
- [ ] Add route constants for new endpoints
- [ ] Update `calculateDeficit` to accept PantryDeficitRequest
- [ ] Add `calculateMealPlanDeficit` method
- [ ] Add `importFromOnHand` method
- [ ] Add `deductRecipe` method
- [ ] Add type imports
</subtasks>

<acceptance>
- All methods compile without TypeScript errors
- Route paths match backend endpoint paths
- Return types match backend response schemas
- `task ui:lint` passes
</acceptance>
</task>

### 5.3 Add Conversion Failure UI Indicator

<task id="5.3" status="pending" depends="5.1" risk="low">
<description>
Modify `frontend/app/components/optimizer/PantryItemRow.vue` to show a visual warning when a deficit item has `conversionFailed=true`.

**Note:** The PantryItemRow component currently displays pantry items for editing — it does NOT currently display deficit results. The conversion failure indicator should be added as a prop-driven visual cue that can be activated when the parent page passes deficit data.

**Implementation approach:**
1. Add an optional prop `conversionFailed: boolean` (default false) to the component
2. When true, show a Vuetify warning icon: `<v-icon color="warning" size="small">mdi-alert-circle-outline</v-icon>`
3. Wrap in a `<v-tooltip>` with text: "Unit conversion failed — quantities may be inaccurate"
4. Position the icon near the quantity field

**Vuetify pattern reference:** Look at how other components in the codebase use `v-tooltip` + `v-icon` for inline warnings.
</description>

<subtasks>
- [ ] Add `conversionFailed` prop (optional, default false)
- [ ] Add conditional v-icon with warning color
- [ ] Wrap in v-tooltip with explanatory text
- [ ] Position near quantity field
</subtasks>

<acceptance>
- Warning icon visible when conversionFailed prop is true
- Icon not visible when prop is false or not provided
- Tooltip displays on hover
- Does not break existing component rendering
</acceptance>
</task>

### 5.4 Frontend i18n for Pantry Page

<task id="5.4" status="pending" depends="" risk="medium">
<description>
Replace all hardcoded English strings in `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` with i18n translation keys.

**i18n system:** The project uses vue-i18n via Nuxt i18n module. Translations are in `frontend/app/lang/messages/en-US.json` as a nested JSON object. Pages use `$t('key.subkey')` in templates or `i18n.t('key.subkey')` in script.

**Strings to replace (from file analysis):**
| Line | Current String | i18n Key |
|------|---------------|----------|
| 6 | "Pantry" | `optimizer.pantry.title` |
| 12 | "Add Item" | `optimizer.pantry.add-item` |
| 22 | "No pantry items yet" | `optimizer.pantry.no-items` |
| 23 | "Add items to your pantry..." | `optimizer.pantry.no-items-description` |
| 42 | "Add Pantry Item" | `optimizer.pantry.add-pantry-item` |
| 50 | "Food" | `optimizer.pantry.food` |
| 58 | "Quantity" | `optimizer.pantry.quantity` |
| 69 | "Unit" | `optimizer.pantry.unit` |
| 77 | "Always available..." | `optimizer.pantry.always-available` |
| 85 | "Expiration Date" | `optimizer.pantry.expiration-date` |
| 93/117 | "Cancel" | `general.cancel` (reuse existing) |
| 100 | "Add" | `general.add` (reuse existing) |
| 109 | "Delete Pantry Item" | `optimizer.pantry.delete-pantry-item` |
| 111 | "Are you sure..." | `optimizer.pantry.delete-confirm` |
| 118 | "Delete" | `general.delete` (reuse existing) |

**Steps:**
1. Add the `optimizer.pantry` key block to `frontend/app/lang/messages/en-US.json`
2. Import and use `useI18n()` composable in the page script (or use `$t()` in template)
3. Replace each hardcoded string with `$t('...')` call
4. Check if `general.cancel`, `general.add`, `general.delete` already exist in en-US.json — reuse if so

**IMPORTANT:** Only modify en-US.json for translations. Other locale files are community-maintained.
</description>

<subtasks>
- [ ] Add `optimizer.pantry.*` keys to `frontend/app/lang/messages/en-US.json`
- [ ] Check if `general.cancel`, `general.add`, `general.delete` exist (reuse if so)
- [ ] Import i18n composable in pantry.vue script section
- [ ] Replace all hardcoded strings with `$t()` calls
- [ ] Verify no hardcoded English strings remain
</subtasks>

<acceptance>
- No hardcoded English strings remain in pantry.vue (except technical attribute values)
- All strings use `$t()` with `optimizer.pantry.*` or `general.*` namespace
- en-US.json contains all required keys with English values
- Page renders identically to before (English text unchanged visually)
- `task ui:lint` passes
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] TypeScript types compile: `task ui:lint` passes
- [ ] API client methods match backend endpoints
- [ ] Conversion failure icon appears in PantryItemRow when prop is true
- [ ] Pantry page renders correctly with i18n
- [ ] No hardcoded strings remain in pantry.vue
- [ ] Start frontend dev server (`task ui`) and manually verify pantry page loads
</verification>
<success_criteria>Frontend compiles, lints clean, and pantry page renders correctly with all new features</success_criteria>
</checkpoint>

</phase>

---

## Phase 6: End-to-End Validation

<phase id="6" name="End-to-End Validation" depends="4,5">

### 6.1 Full Test Suite Run

<task id="6.1" status="pending" depends="4.3,5.4" risk="low">
<description>
Run the complete test suite and lint checks to verify no regressions.

**Commands:**
```bash
task py:lint        # Python linting
task ui:lint        # Frontend linting
pytest tests/unit_tests/services_tests/test_pantry_service.py -v
pytest tests/unit_tests/services_tests/test_recipe_utils.py -v
pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v
```
</description>

<subtasks>
- [ ] Run Python linting
- [ ] Run frontend linting
- [ ] Run all pantry-related unit tests
- [ ] Run all pantry-related integration tests
- [ ] Verify no regressions in unrelated tests (run broader test suite if time permits)
</subtasks>

<acceptance>
- All lint checks pass with zero errors
- All unit tests pass
- All integration tests pass
- No regressions in existing functionality
</acceptance>
</task>

### 6.2 Manual Smoke Test

<task id="6.2" status="pending" depends="6.1" risk="low">
<description>
Start the dev servers and manually verify the feature works end-to-end.

**Steps:**
1. `task dev:services` — Start PostgreSQL
2. `task py:postgres` — Start backend (localhost:9000)
3. `task ui` — Start frontend (localhost:3000)
4. Navigate to pantry page
5. Verify: Add pantry item works
6. Verify: Pantry page displays with translated strings (if locale is en-US, text should look the same)
7. Verify: If a pantry item has expired, it shows in the list
8. Test POST /deficit via curl or the UI if wired up
9. Test POST /import-on-hand via curl
10. Test POST /deduct via curl
</description>

<subtasks>
- [ ] Start dev servers
- [ ] Verify pantry CRUD still works
- [ ] Verify pantry page renders correctly
- [ ] Test deficit endpoint with new request body
- [ ] Test import-on-hand endpoint
- [ ] Test deduct endpoint
</subtasks>

<acceptance>
- Pantry page loads without errors
- CRUD operations work
- New endpoints return expected responses
- No console errors in browser or backend logs
</acceptance>
</task>

</phase>

---

## Final Validation

<final_validation>
<verification>
- [ ] All unit tests pass (`pytest tests/unit_tests/services_tests/test_pantry_service.py tests/unit_tests/services_tests/test_recipe_utils.py -v`)
- [ ] All integration tests pass (`pytest tests/integration_tests/user_household_tests/test_pantry_items.py -v`)
- [ ] Python linting passes (`task py:lint`)
- [ ] Frontend linting passes (`task ui:lint`)
- [ ] Manual smoke test completed
- [ ] No regressions in existing pantry CRUD functionality
- [ ] All new files are in optimizer/ subdirectories (fork isolation maintained)
- [ ] CLAUDE.md "Modified Upstream Files" list has not grown
</verification>
<acceptance>
All 4 new endpoints work correctly, expiration filtering is functional, frontend displays conversion warnings, pantry page is internationalized, and all tests pass.
</acceptance>
</final_validation>

---

## Dependency Verification Log

<dependency_log>
<dependency name="SQLAlchemy selectinload" verified="true">
  <version>2.0.49</version>
  <verified_via>Used extensively in codebase (e.g., PantryItemOut.loader_options classmethod)</verified_via>
  <notes>selectinload preferred over joinedload for collection relationships to avoid cartesian product</notes>
</dependency>
<dependency name="Pydantic model_validator" verified="true">
  <version>2.12.5</version>
  <verified_via>Pydantic v2 API — model_validator(mode="after") is the v2 replacement for root_validator</verified_via>
  <notes>Ensure mode="after" for validators that access parsed fields</notes>
</dependency>
<dependency name="UnitConverter" verified="true">
  <version>Custom (pint-based)</version>
  <verified_via>Read mealie/services/parser_services/parser_utils/unit_utils.py</verified_via>
  <notes>convert() returns tuple[float, Unit], can_convert() returns bool. Both accept str|Unit.</notes>
</dependency>
<dependency name="RepositoryMeals.get_meals_by_date_range" verified="true">
  <version>N/A</version>
  <verified_via>Read mealie/repos/repository_meals.py lines 23-33</verified_via>
  <notes>Takes datetime objects (not date). Must convert date→datetime at call site. Returns list[ReadPlanEntry] with recipe_id: UUID|None.</notes>
</dependency>
<dependency name="HouseholdModel.ingredient_foods_on_hand" verified="true">
  <version>N/A</version>
  <verified_via>Read mealie/db/models/household/household.py lines 72-76</verified_via>
  <notes>M2M via households_to_ingredient_foods table. Returns list[IngredientFoodModel]. Unique constraint on (household_id, food_id).</notes>
</dependency>
<dependency name="BaseCRUDAPI (frontend)" verified="true">
  <version>N/A</version>
  <verified_via>Read frontend/app/lib/api/user/optimizer-pantry.ts and recipe-foods.ts</verified_via>
  <notes>Standard pattern: extend BaseCRUDAPI, set baseRoute/itemRoute, add custom methods via this.requests.post/get/put/delete</notes>
</dependency>
<dependency name="vue-i18n / $t()" verified="true">
  <version>Nuxt i18n module</version>
  <verified_via>Searched for $t( in frontend codebase — used in shopping lists, meal plans, etc.</verified_via>
  <notes>English messages in frontend/app/lang/messages/en-US.json. Composable: useI18n() or useGlobalI18n().</notes>
</dependency>
<dependency name="Vuetify v-tooltip + v-icon" verified="true">
  <version>4.0.5</version>
  <verified_via>Used in existing components throughout frontend</verified_via>
  <notes>mdi-alert-circle-outline is available in Material Design Icons (bundled with Vuetify)</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should POST /deficit remain backward-compatible by accepting both list[UUID4] and PantryDeficitRequest, or is a clean break acceptable?</question>
  <impact>If backward compatibility needed, must add Union type handling in controller; if clean break, frontend must update simultaneously</impact>
  <default_assumption>Clean break — wrap in PantryDeficitRequest. Fork has no external consumers. Frontend updates in Phase 5.</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should meal plan deficit deduplicate by recipe_id only, or should repeated recipes multiply their ingredient requirements?</question>
  <impact>Deduplication answers "what unique ingredients do I need?" — multiplication answers "how much total do I need for N servings?"</impact>
  <default_assumption>Deduplicate — deficit answers 'what ingredients do I need for these unique recipes.' Codex flagged this as potentially surprising but the spec explicitly chose deduplication.</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>Should pantry deduction happen automatically when a recipe is marked as cooked, or only via explicit POST /deduct?</question>
  <impact>Automatic deduction requires wiring into upstream recipe/meal-plan flows, increasing upstream modification footprint</impact>
  <default_assumption>Explicit POST /deduct only — avoids upstream modifications</default_assumption>
</question>
<question id="Q4" blocking="false" inherited_from="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
  <question>For bulk import, should imported items default to assume_enough=False (quantity-untracked) or should the user choose?</question>
  <impact>User choice adds UI complexity; default keeps import simple</impact>
  <default_assumption>Default assume_enough=False, quantity=None — simple migration path, user can toggle later</default_assumption>
</question>
<question id="Q5" blocking="false">
  <question>What should happen on unit conversion failure during deduct: skip the item silently, or include it in a failure list in the response?</question>
  <impact>Silent skip is simpler but gives no feedback. Failure list adds a response schema change.</impact>
  <default_assumption>Skip silently — consistent with deficit calculation behavior. The returned list only includes successfully deducted items; caller can diff to detect skips. Codex agreed this is acceptable for the fork's single-user context.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-13-184302-pantry-quantity-tracking-completion.md">
<resolved original_question="Should the is_staple field UI be included in this spec or deferred further?">
  <resolution>Deferred per spec — no feature currently depends on is_staple, and UX design for staple vs always-available is undecided. Not included in this plan.</resolution>
</resolved>
</resolved_from_source>

---

## Plan Review Notes

<codex_response>
**Findings**
- High: The session-level recipe fetch and household on-hand fetch must enforce group/household scoping; the plan doesn't mention filtering by `group_id`/`household_id`, which risks cross-tenant leakage (see current scoping in `mealie/routes/optimizer/controller_pantry.py:45`, household model in `mealie/db/models/household/household.py:29`).
- High: Deduplicating meal-plan `recipe_id`s will under-count if a recipe appears multiple times in the plan; this is a behavioral choice that may not match user intent (see `mealie/schema/meal_plan/new_meal.py:62`).
- Medium: `deduct_recipe` doing per-item repo updates will commit per item; failures can leave partial state unless you wrap updates in a single transaction or use `update_many` (see commit behavior in `mealie/repos/repository_generic.py:210`).
- Medium: Batch recipe fetch should eagerly load ingredient food/unit to avoid lazy-load churn or detached access in `calculate_deficit` (see `mealie/services/optimizer/pantry.py:49` and relationships in `mealie/db/models/recipe/ingredient.py:344`).
- Low: Deduct conversion-failure behavior is unspecified; it should be consistent with the deficit rules and surfaced in the response or errors (see `mealie/services/optimizer/pantry.py:49`).

**Answers**
1) The `session.execute(select(RecipeModel)...selectinload(...))` approach is fine; add `RecipeModel.group_id == group_id`, handle empty `recipe_ids`, and selectinload `recipe_ingredient.food` and `recipe_ingredient.unit`. Use `.unique().scalars().all()` if you add any joinedloads later.
2) A helper in `mealie/services/optimizer/` is aligned with fork isolation, but keep it "service-layer" style: accept session + ids, return models or schemas consistently with `PantryService` expectations.
3) Keep commits out of the controller. Either use `repo.update_many` or wrap the service call in `with session.begin():` and do all updates before commit.
4) `session.get(HouseholdModel, household_id)` is ok if you also validate `group_id`, and use `selectinload(HouseholdModel.ingredient_foods_on_hand)` to avoid lazy-load; otherwise consider using `repos.households._query()` to keep existing scoping patterns.
5) Task atomicity is mostly ok, but frontend work and multi-endpoint backend work are larger than single-step; plan for 2–3 sub-tasks each.
6) Hidden complexity: import-on-hand merge rules (create vs update, defaults, duplicates), deduct conversion/rounding/concurrency, and frontend API type changes plus failure UI/i18n.
</codex_response>

<changes_made>
Based on Codex feedback, the following changes were incorporated into this plan:

1. **Group/household scoping (High):** Task 1.1 (batch fetch) now explicitly includes `RecipeModel.group_id == group_id` in the WHERE clause. Task 2.2 (import) now validates `household.group_id == self.repos.group_id` after session.get.

2. **Meal plan deduplication (High):** Retained deduplication per spec decision but added explicit documentation in Task 3.1 explaining the trade-off. Added as open question Q2 for visibility.

3. **Transaction atomicity (Medium):** Task 2.3 (deduct_recipe) now specifies collecting all updates before persisting, with session commit handled by controller/middleware — not per-item commits.

4. **Eager loading depth (Medium):** Task 1.1 now specifies selectinload for both `recipe_ingredient.food` and `recipe_ingredient.unit` to prevent lazy-load N+1 in downstream calculate_deficit.

5. **Deduct conversion failure behavior (Low):** Task 2.3 now explicitly specifies: skip items with incompatible units silently (consistent with deficit rule 7). Added as new open question Q5.

6. **Task granularity (Medium):** Split controller work into two tasks (3.1 deficit endpoints, 3.2 import/deduct endpoints). Frontend work already had 4 separate tasks. Added detailed subtask checklists throughout.
</changes_made>
