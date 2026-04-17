# Implementation Plan: Shopping List Enhancements (Stage C)

Source: docs/plans/2026-04-14-220000-shopping-list-enhancements.md
Revised: 2026-04-14

<plan_metadata>
  <feature>Shopping List Pantry Integration (C1 verify, C2 deficit banner, C3 deduct/quick-add)</feature>
  <source>docs/plans/2026-04-14-220000-shopping-list-enhancements.md</source>
  <revision_scope>heavy</revision_scope>
  <phases>5</phases>
  <tasks>14</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

This plan adds pantry integration to Mealie's existing shopping list page in three sub-features: (C1) verifying that auto-section assignment already works, (C2) adding a deficit coverage banner showing how many items are covered by pantry, and (C3) offering deduct-from-pantry and quick-add-to-pantry actions when users check off shopping list items. The backend adds two new endpoints to the existing PantryItemController; the frontend adds a new sub-composable, a dialog component, and minimal modifications to the shopping list page and CRUD composable.

## Changes from Original

<revision_summary>
<change type="structural">
  Removed artificial Phase 2→Phase 3 dependency. TypeScript types (3.1) and i18n keys (3.3) have no runtime dependency on backend endpoints. Phase 3 can now execute in parallel with Phase 2, shortening the critical path.
</change>
<change type="structural">
  Split compound Task 4.2 (old plan) into Task 4.2 (wire composable into orchestrator) and Task 4.3 (add banner to page template). These modify different files and have different risk profiles.
</change>
<change type="structural">
  Split compound Task 4.4 (old plan) into Task 4.5 (hook checkout callbacks into both saveListItem AND checkAllItems) and Task 4.6 (add dialog to page template and wire events). This isolates the high-risk upstream composable modification from the safe template addition.
</change>
<change type="dependency">
  Fixed critical design gap: `checkAllItems()` (use-shopping-list-crud.ts:38-49) does NOT call `saveListItem()` — it directly mutates items and calls `updateUncheckedListItems()`. Task 4.5 now hooks BOTH `saveListItem` (for individual checks) AND `checkAllItems` (for batch checks). The debounce-only approach from the original plan would have silently failed for "Check All".
</change>
<change type="structural">
  Moved dialog component from `frontend/app/components/Domain/ShoppingList/ShoppingListPantryDialog.vue` (upstream directory) to `frontend/app/components/optimizer/ShoppingListPantryDialog.vue` per CLAUDE.md fork isolation rules.
</change>
<change type="clarity">
  Added `__all__` list update to Task 2.1 — the original plan omitted updating `mealie/schema/optimizer/pantry.py`'s `__all__` list (lines 16-29), which would cause `from mealie.schema.optimizer.pantry import *` to miss the new schemas.
</change>
<change type="clarity">
  Added explicit error handling guidance to composable (Task 4.1) and checkout hook (Task 4.5): all pantry API calls use try/catch with silent degradation, matching the existing pantry auto-check pattern at shopping_lists.py:178-184.
</change>
<change type="removed">
  Merged Task 5.2 (code quality review) into Task 5.1 (E2E smoke test). The code quality review was a checklist redundant with the Phase 5 checkpoint.
</change>
<change type="clarity">
  Added CLAUDE.md update subtask to Task 5.1 for the three new upstream file modifications.
</change>
</revision_summary>

## Prerequisites

<prerequisites>
<prereq id="P1" type="service" verified="true">
  <description>PantryService with CRUD, deficit, deduct_recipe, check_shopping_items, import_from_on_hand</description>
  <verification>File exists: mealie/services/optimizer/pantry.py (476 lines, all methods confirmed)</verification>
</prereq>
<prereq id="P2" type="service" verified="true">
  <description>PantryItemController with /deficit, /deficit/meal-plan, /import-on-hand, /deduct endpoints</description>
  <verification>File exists: mealie/routes/optimizer/controller_pantry.py (99 lines, 9 endpoints confirmed)</verification>
</prereq>
<prereq id="P3" type="data" verified="true">
  <description>AllRepositories.group_shopping_list_item property for reading ShoppingListItem records</description>
  <verification>Confirmed at mealie/repos/repository_factory.py:317-325 — returns HouseholdRepositoryGeneric[ShoppingListItemOut, ShoppingListItem]. Household-scoped — returns items filtered by group_id + household_id.</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>Frontend optimizer API client with PantryItemsApi, OptimizerApi classes accessible via useUserApi().optimizer.pantry</description>
  <verification>File exists: frontend/app/lib/api/user/optimizer-pantry.ts (75 lines). Access chain verified: useUserApi() → UserApi.optimizer → OptimizerApi.pantry → PantryItemsApi.</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>ShoppingListOut.recipeReferences with recipeId field for deficit calculation</description>
  <verification>Confirmed at frontend/app/lib/api/types/household.ts:685 — recipeReferences?: ShoppingListRecipeRefOut[] with recipeId: string</verification>
</prereq>
<prereq id="P6" type="environment" verified="true">
  <description>Shopping list page with sub-composable pattern (7 sub-composables orchestrated by use-shopping-list-page.ts)</description>
  <verification>File exists: frontend/app/composables/shopping-list-page/use-shopping-list-page.ts (194 lines, imports 7 sub-composables, returns spread object with ...state, ...labels, ...crud, ...recipes)</verification>
</prereq>
</prerequisites>

---

## Phase 1: C1 — Verify Auto-Section Assignment

<phase id="1" name="Verify Auto-Section Assignment">

### 1.1 Manual Verification of Label Assignment

<task id="1.1" status="pending" depends="" risk="low">
<context>
C1 is a verification-only task. The shopping list already has auto-section assignment via two mechanisms:

**Backend** (mealie/services/household_services/shopping_lists.py:145-152):
`find_matching_label()` resolves a label_id for each new item in three steps:
1. Item already has label_id → use it
2. Item has food with food.label_id → use it
3. Fuzzy match on item.display text via `self.data_matcher.find_food_match()` → use food_search.label_id

**Frontend** (use-shopping-list-sorting.ts):
`updateItemsByLabel()` groups unchecked items by `label.name` into collapsible expansion panels on the shopping list page.

Verify this works end-to-end by testing at localhost:3000 with a running backend (localhost:9000).
</context>

<subtasks>
- [ ] Start dev environment: `task dev:services`, `task py:migrate`, `task py:postgres`, `task ui`
- [ ] Create a shopping list and add a recipe that has foods with assigned labels
- [ ] Verify items appear grouped under label sections (e.g., "Produce", "Dairy")
- [ ] Verify items without food.label_id appear in an ungrouped/"No Label" section
- [ ] Add a manual item (type text, no food link) and verify fuzzy match attempts label assignment
- [ ] Document any gaps found (if labels are not assigned, check if foods have label_id set)
</subtasks>

<acceptance>
- Items added from recipes with food.label_id appear under the correct label section
- Items without any label fall into the default/ungrouped section
- No code changes needed — this is verification only
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] Auto-section assignment works for recipe-sourced items with food.label_id
- [ ] Ungrouped items render correctly
- [ ] No regressions in shopping list create/edit/delete flow
</verification>
<gate>C1 is confirmed working or gaps documented. No code changes produced by this phase.</gate>
</checkpoint>

</phase>

---

## Phase 2: C3 Backend — New Schemas, Service Methods, Endpoints

<phase id="2" name="C3 Backend">

### 2.1 Add Request Schemas

<task id="2.1" status="pending" depends="" risk="low">
<context>
Add two new Pydantic request schemas to `mealie/schema/optimizer/pantry.py` (currently 144 lines) for the deduct-by-shopping-items and quick-add-to-pantry endpoints.

**File**: `mealie/schema/optimizer/pantry.py`

The file has an `__all__` list at lines 16-29 that controls wildcard exports. New schemas must be added to both the `__all__` list AND as class definitions.

Add the three new schema names to `__all__` (after `"PantryDeductRequest"`):
```python
"ShoppingItemDeductRequest",
"PantryQuickAddItem",
"PantryQuickAddRequest",
```

Add class definitions **after** the existing `PantryDeductRequest` class (around line 115) and **before** `PantryImportResult`:

```python
class ShoppingItemDeductRequest(MealieModel):
    """Deduct pantry quantities based on checked-off shopping list items."""
    shopping_list_item_ids: list[UUID4]

class PantryQuickAddItem(MealieModel):
    """Single item to quick-add to pantry from shopping list."""
    food_id: UUID4
    quantity: float | None = None
    unit_id: UUID4 | None = None

class PantryQuickAddRequest(MealieModel):
    """Bulk-create pantry items from shopping list data."""
    items: list[PantryQuickAddItem]
```

All schemas extend `MealieModel` which provides the snake_case → camelCase alias generator. No custom validators needed.
</context>

<subtasks>
- [ ] Read `mealie/schema/optimizer/pantry.py` to confirm current `__all__` list and class locations
- [ ] Add three new schema names to the `__all__` list after `"PantryDeductRequest"`
- [ ] Add `ShoppingItemDeductRequest` class after `PantryDeductRequest`
- [ ] Add `PantryQuickAddItem` class
- [ ] Add `PantryQuickAddRequest` class
- [ ] Verify imports: `UUID4` from `pydantic` is already imported at the top of the file
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer.pantry import ShoppingItemDeductRequest, PantryQuickAddRequest, PantryQuickAddItem"` succeeds
- `python -c "from mealie.schema.optimizer.pantry import *; print(ShoppingItemDeductRequest)"` succeeds (verifies `__all__` update)
- Schemas serialize to camelCase: `ShoppingItemDeductRequest(shopping_list_item_ids=[...]).model_dump(by_alias=True)` produces `{"shoppingListItemIds": [...]}`
- `task py:lint` passes
</acceptance>
</task>

### 2.2 Add PantryService Methods

<task id="2.2" status="pending" depends="2.1" risk="medium">
<context>
Add two new methods to `PantryService` in `mealie/services/optimizer/pantry.py` (currently 476 lines).

**Method 1: `deduct_shopping_items()`** — follows the exact pattern of `deduct_recipe()` (lines 288-367) but resolves food/quantity/unit from ShoppingListItem records instead of RecipeIngredient objects.

Implementation approach:
1. Fetch shopping list items by ID using `self.repos.group_shopping_list_item.get_one(item_id)` for each ID
2. Build pantry_map via `self.get_pantry_map()` (existing method, returns dict[UUID4, PantryItemOut] keyed by food_id)
3. For each shopping list item with a food_id:
   - Skip if food_id not in pantry_map
   - Skip if pantry item has `assume_enough=True`
   - Skip if pantry item quantity is None (untracked)
   - Skip if shopping list item quantity is None
   - Apply unit conversion using `self.converter` (same as deduct_recipe)
   - Track in `running_qty` dict, compute `max(0.0, round(current - converted, 4))`
4. Persist all modified items via `self.pantry_items.update(item.id, {"quantity": running_qty[food_id]})`
5. Return list of updated PantryItemOut

**Method 2: `quick_add_from_shopping()`** — creates pantry items from shopping list data, skipping duplicates.

Implementation approach:
1. Get existing pantry_map via `self.get_pantry_map()`
2. For each (food_id, quantity, unit_id) tuple:
   - Skip if food_id already in pantry_map (idempotent)
   - Create `PantryItemSave(food_id=food_id, quantity=quantity, unit_id=unit_id, group_id=group_id, household_id=household_id, is_staple=False, assume_enough=False)`
   - Persist via `self.pantry_items.create(item_save)`
3. Return list of created PantryItemOut

**Cross-domain access**: PantryService accesses `self.repos.group_shopping_list_item` (AllRepositories, confirmed at repository_factory.py:317-325). This follows the standard Mealie pattern — other services (e.g., ShoppingListService) already access multiple repos on the same AllRepositories instance.

**Imports needed**: Add `PantryItemSave` if not already imported (check existing imports). The `ShoppingListItemOut` type comes from the repo's `get_one` return type — no explicit import needed.
</context>

<subtasks>
- [ ] Read `mealie/services/optimizer/pantry.py` lines 288-367 to reference the deduct_recipe pattern
- [ ] Read the imports section (top of file) to confirm what's already imported
- [ ] Add `deduct_shopping_items()` method after `deduct_recipe()` (after line 367)
- [ ] Add `quick_add_from_shopping()` method after `deduct_shopping_items()`
- [ ] Verify that `self.repos.group_shopping_list_item` is accessible (it's a cached_property on AllRepositories)
- [ ] Ensure `PantryItemSave` is imported (check if it's in the existing imports)
- [ ] Run `task py:lint` to verify no lint errors
</subtasks>

<acceptance>
- `deduct_shopping_items` method exists, accepts `shopping_list_item_ids: list[UUID4]`, returns `list[PantryItemOut]`
- `quick_add_from_shopping` method exists, accepts items list + group_id + household_id, returns `list[PantryItemOut]`
- `deduct_shopping_items` follows the running_qty + persist-at-end pattern from deduct_recipe
- `quick_add_from_shopping` skips foods already in pantry (idempotent)
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
These methods are additive — they don't modify existing methods. If something breaks, delete the two new methods. The cross-domain repo access is safe (confirmed by repository pattern analysis) but verify household_id scoping by checking that `self.repos.group_shopping_list_item` is initialized with the same session context as `self.pantry_items`.
</rollback>
</task>

### 2.3 Add Controller Endpoints

<task id="2.3" status="pending" depends="2.2" risk="medium">
<context>
Add two new POST endpoints to `PantryItemController` in `mealie/routes/optimizer/controller_pantry.py` (currently 99 lines).

**CRITICAL: Route ordering**. The file has a comment at line 48: "All POST endpoints must be before /{item_id} to avoid route conflict." FastAPI processes routes in definition order within a router, and the `@controller(router)` decorator registers methods in class-body order. The new endpoints MUST be placed after the existing POST /deduct (around line 75) and BEFORE the GET "" / POST "" block (around line 78). If placed after /{item_id}, FastAPI will interpret "deduct-shopping-items" and "quick-add" as item_id path parameters.

**Current endpoint order** (for reference):
1. POST /deficit (line ~50)
2. POST /deficit/meal-plan (line ~58)
3. POST /import-on-hand (line ~65)
4. POST /deduct (line ~72)
5. → INSERT: POST /deduct-shopping-items
6. → INSERT: POST /quick-add
7. GET "" (get_all)
8. POST "" (create_one, 201)
9. GET /{item_id}
10. PUT /{item_id}
11. DELETE /{item_id}

**Endpoint 1**: `POST /deduct-shopping-items`
- Request body: `ShoppingItemDeductRequest` (has `shopping_list_item_ids: list[UUID4]`)
- Response: `list[PantryItemOut]`
- Implementation: `return self.service.deduct_shopping_items(data.shopping_list_item_ids)`

**Endpoint 2**: `POST /quick-add`
- Request body: `PantryQuickAddRequest` (has `items: list[PantryQuickAddItem]`)
- Response: `list[PantryItemOut]`
- Status code: 201
- Implementation: Extract (food_id, quantity, unit_id) tuples from data.items, pass to `self.service.quick_add_from_shopping()` with group_id and household_id from `self.group_id` and `self.household_id` (inherited from BaseCrudController).

**Import additions**: Add `ShoppingItemDeductRequest`, `PantryQuickAddRequest` to the import from `mealie.schema.optimizer.pantry`.
</context>

<subtasks>
- [ ] Read `mealie/routes/optimizer/controller_pantry.py` to confirm current structure and import locations
- [ ] Add `ShoppingItemDeductRequest`, `PantryQuickAddRequest` to the schema import line
- [ ] Add `deduct_shopping_items` endpoint method AFTER the existing `deduct_recipe` endpoint and BEFORE `get_all`
- [ ] Add `quick_add` endpoint method after `deduct_shopping_items` and BEFORE `get_all`
- [ ] Verify route ordering: all POST-with-path endpoints precede /{item_id} routes
- [ ] Run `task py:lint`
</subtasks>

<acceptance>
- `POST /households/optimizer/pantry/deduct-shopping-items` appears in Swagger docs at localhost:9000/docs
- `POST /households/optimizer/pantry/quick-add` appears in Swagger docs (with 201 status)
- Both endpoints are listed BEFORE the `/{item_id}` endpoints in Swagger
- Both endpoints require authentication (inherited from BaseCrudController)
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
If route ordering is wrong, FastAPI silently matches the wrong handler. Symptoms: 422 validation errors when calling the new endpoints (because item_id UUID validation fails on "deduct-shopping-items" string). Fix: reorder methods in the controller class.
</rollback>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task py:lint` passes
- [ ] Backend starts without errors: `task py:postgres`
- [ ] Swagger docs show both new endpoints at correct paths under /households/optimizer/pantry/
- [ ] Can call POST /deduct-shopping-items with a valid request body (even if no data exists, should return empty list)
- [ ] Can call POST /quick-add with a valid request body (should create items or return empty if foods exist)
</verification>
<gate>Both new endpoints are functional, appear in Swagger, and follow existing authentication/household-isolation patterns.</gate>
</checkpoint>

</phase>

---

## Phase 3: Frontend Infrastructure — Types, API Client, i18n

**Note**: Phase 3 has NO dependency on Phase 2. Tasks 3.1 and 3.3 can execute in parallel with Phase 2. Only Task 3.2 depends on Task 3.1 (for the type imports).

<phase id="3" name="Frontend Infrastructure" depends="">

### 3.1 Add TypeScript Types

<task id="3.1" status="pending" depends="" risk="low">
<context>
Add TypeScript interfaces for the two new request schemas to `frontend/app/lib/api/types/optimizer.ts` (currently 124 lines).

Add these interfaces at the end of the file, after the existing `PantryDeductRequest` interface:

```typescript
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
```

Field names must be camelCase to match the backend's alias generator output. `ShoppingItemDeductRequest.shoppingListItemIds` maps to the backend's `shopping_list_item_ids`. Optional fields use `?` with `| null` to match Pydantic's `float | None = None` pattern.
</context>

<subtasks>
- [ ] Read `frontend/app/lib/api/types/optimizer.ts` to confirm current end-of-file structure
- [ ] Add `ShoppingItemDeductRequest` interface
- [ ] Add `PantryQuickAddItem` interface
- [ ] Add `PantryQuickAddRequest` interface
- [ ] Run `task ui:lint` to verify
</subtasks>

<acceptance>
- All three interfaces are exported from the file
- Field names match backend camelCase aliases exactly
- `task ui:lint` passes
</acceptance>
</task>

### 3.2 Add API Client Methods

<task id="3.2" status="pending" depends="3.1" risk="low">
<context>
Add two new API methods and their routes to `frontend/app/lib/api/user/optimizer-pantry.ts` (currently 75 lines).

**Routes to add** (in the `routes` object, after the existing `pantryDeduct` route):
```typescript
pantryDeductShoppingItems: `${prefix}/households/optimizer/pantry/deduct-shopping-items`,
pantryQuickAdd: `${prefix}/households/optimizer/pantry/quick-add`,
```

**Methods to add** (in the `PantryItemsApi` class, after the existing `deductRecipe` method):
```typescript
async deductShoppingItems(data: ShoppingItemDeductRequest) {
  return await this.requests.post<PantryItemOut[]>(routes.pantryDeductShoppingItems, data);
}

async quickAdd(data: PantryQuickAddRequest) {
  return await this.requests.post<PantryItemOut[]>(routes.pantryQuickAdd, data);
}
```

**Imports to add**: `ShoppingItemDeductRequest`, `PantryQuickAddRequest` from `~/lib/api/types/optimizer`. The file already imports from this path for existing types like `PantryDeficitRequest`.
</context>

<subtasks>
- [ ] Read `frontend/app/lib/api/user/optimizer-pantry.ts` to confirm current structure
- [ ] Add two new route entries to the `routes` object
- [ ] Add `deductShoppingItems()` method to `PantryItemsApi` class
- [ ] Add `quickAdd()` method to `PantryItemsApi` class
- [ ] Add new type imports from `~/lib/api/types/optimizer`
- [ ] Run `task ui:lint` to verify
</subtasks>

<acceptance>
- Both methods exist on `PantryItemsApi`
- Routes point to correct backend paths
- Import types match the interfaces added in Task 3.1
- `task ui:lint` passes
</acceptance>
</task>

### 3.3 Add i18n Keys

<task id="3.3" status="pending" depends="" risk="low">
<context>
Add i18n keys for all new user-facing strings to `frontend/app/lang/messages/en-US.json`.

Add a `"shopping"` key under the existing `"optimizer"` object (which currently has `"pantry"`, `"config"`, and `"planner"` sub-keys). The `"optimizer"` key is at approximately line 1484.

```json
"shopping": {
  "coverage-banner": "{covered} of {total} items covered by pantry",
  "coverage-percent": "({percent}% coverage)",
  "deduct-from-pantry": "Deduct from pantry",
  "add-to-pantry": "Add to pantry",
  "pantry-action-title": "Update Pantry",
  "items-in-pantry": "Items already in pantry (deduct purchased amount):",
  "items-not-in-pantry": "Items not in pantry (add to track inventory):",
  "skip": "Skip",
  "deducted-count": "Updated {count} pantry item | Updated {count} pantry items",
  "added-count": "Added {count} item to pantry | Added {count} items to pantry"
}
```

Place this new `"shopping"` key after the `"planner"` key, inside the `"optimizer"` object. Pluralization uses the vue-i18n pipe syntax (`singular | plural`).
</context>

<subtasks>
- [ ] Read `frontend/app/lang/messages/en-US.json` around the end of the optimizer object to confirm insertion point
- [ ] Add the `"shopping"` sub-key with all 10 i18n entries
- [ ] Verify JSON is valid (no trailing commas, proper nesting)
- [ ] Run `task ui:lint` to verify
</subtasks>

<acceptance>
- `optimizer.shopping.coverage-banner` and all 9 other keys exist in en-US.json
- Keys are under `optimizer.shopping` namespace (not `shopping-list` or top-level)
- Pluralization strings use pipe syntax
- JSON is valid — `task ui:lint` passes
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `task ui:lint` passes
- [ ] TypeScript types compile without errors
- [ ] API client methods reference correct routes matching backend endpoints
- [ ] i18n keys are valid JSON and nested under optimizer.shopping
</verification>
<gate>All frontend infrastructure (types, API client, i18n) is in place for Phase 4 composable and component work.</gate>
</checkpoint>

</phase>

---

## Phase 4: Frontend Integration — Composable, Banner, Dialog, Checkout Hooks

<phase id="4" name="Frontend Integration" depends="2,3">

### 4.1 Create Shopping List Pantry Composable

<task id="4.1" status="pending" depends="3.2" risk="high">
<context>
Create `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts` — the central composable encapsulating all pantry integration for the shopping list page.

**Pattern**: Follow the existing sub-composable pattern (see `use-shopping-list-crud.ts`, `use-shopping-list-labels.ts`). Each composable is a function that receives shared refs and returns state + methods.

**Function signature**:
```typescript
export function useShoppingListPantry(
  shoppingList: Ref<ShoppingListOut | null>,
)
```

**State to manage**:
- `deficitReport: Ref<PantryDeficitReport | null>` — aggregated deficit data
- `deficitLoading: Ref<boolean>` — loading state for deficit fetch
- `coverageSummary: ComputedRef<string>` — formatted "X of Y items covered" string using i18n
- `showCoverageBanner: ComputedRef<boolean>` — false if no deficit data or no recipe references
- `pendingActions: Ref<PantryCheckoutAction[]>` — items pending pantry action after checkout
- `showPantryDialog: Ref<boolean>` — dialog visibility

**PantryCheckoutAction interface** (define and export in this file):
```typescript
export interface PantryCheckoutAction {
  itemId: string;
  foodId: string;
  foodName: string;
  quantity: number;
  unitId: string | null;
  unitName: string | null;
  existsInPantry: boolean;  // true → deduct, false → quick-add
}
```

**Methods to implement**:

1. `fetchDeficit()`: Extract `recipeIds` from `shoppingList.value.recipeReferences.map(ref => ref.recipeId)`. Call `api.optimizer.pantry.calculateDeficit({ recipeIds })` (where `api = useUserApi()`). Store result in `deficitReport`. Handle empty/null/undefined recipeReferences (return early, don't call API).

2. `onItemChecked(item: ShoppingListItemOut)`: Called when a single item transitions to checked. If `item.foodId` is null, return. Build a `PantryCheckoutAction` from the item and deficit data (if food appears in `deficitReport.items` with a pantry match, `existsInPantry = true`). Add to `pendingActions`. Use **debounce** (300ms via `useDebounceFn` from `@vueuse/core`) before setting `showPantryDialog = true` — this batches rapid individual checks.

3. `onItemsChecked(items: ShoppingListItemOut[])`: Called by checkAllItems with ALL newly-checked items at once. Filter to items with `foodId`. Build `PantryCheckoutAction[]`. Set `pendingActions` directly. Show dialog immediately (no debounce — items are already collected).

4. `executeDeduct(itemIds: string[])`: Call `api.optimizer.pantry.deductShoppingItems({ shoppingListItemIds: itemIds })`. On success, clear those items from `pendingActions`, show success toast, refresh deficit. On failure, silently close dialog (log error but don't block UI).

5. `executeQuickAdd(items: Array<{foodId, quantity, unitId}>)`: Call `api.optimizer.pantry.quickAdd({ items })`. On success, clear items from `pendingActions`, show success toast, refresh deficit. On failure, silently close dialog.

6. `dismissPantryDialog()`: Set `showPantryDialog = false`, clear `pendingActions`.

**Error handling pattern**: All API calls in try/catch. On catch, log to console.error but do NOT show error dialogs or block UI. The pantry integration is a convenience feature — it must never break the core shopping list flow. This matches the existing pantry auto-check pattern at shopping_lists.py:178-184.

**API access**: Use `const api = useUserApi()` (standard composable pattern).

**i18n access**: Use `const { t } = useI18n()` for coverageSummary formatting.

**Debounce**: Use `useDebounceFn` from `@vueuse/core` (already a project dependency — `useLocalStorage` and `useOnline` are imported from it in use-shopping-list-item-actions.ts).
</context>

<subtasks>
- [ ] Create the file at `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts`
- [ ] Define and export `PantryCheckoutAction` interface
- [ ] Implement reactive state (deficitReport, deficitLoading, pendingActions, showPantryDialog)
- [ ] Implement `coverageSummary` computed using `t("optimizer.shopping.coverage-banner", { covered, total })`
- [ ] Implement `showCoverageBanner` computed — true only when deficitReport is non-null AND shoppingList has recipeReferences with length > 0
- [ ] Implement `fetchDeficit()` — extract recipe IDs from recipeReferences, call deficit endpoint, handle empty/null case
- [ ] Implement `onItemChecked()` for single-item checkout with 300ms debounce
- [ ] Implement `onItemsChecked()` for batch checkout (Check All) without debounce
- [ ] Implement `executeDeduct()` and `executeQuickAdd()` with try/catch, toast, and deficit refresh
- [ ] Implement `dismissPantryDialog()`
- [ ] Export the composable function
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- File exists and exports `useShoppingListPantry` function and `PantryCheckoutAction` interface
- `fetchDeficit()` calls POST /deficit with recipe IDs from shoppingList.recipeReferences
- `coverageSummary` returns i18n-formatted string with covered/total counts
- `showCoverageBanner` is false when deficitReport is null or shoppingList has no recipeReferences
- `onItemChecked()` accumulates single-item actions and debounces dialog display (300ms)
- `onItemsChecked()` handles batch items and shows dialog immediately (no debounce)
- All API calls wrapped in try/catch with silent degradation
- `task ui:lint` passes
</acceptance>

<rollback risk="high">
This is the most complex new file. If the composable has issues, the banner and dialog won't work, but the shopping list page itself is unaffected since this composable is only wired in by Task 4.2. If the debounce logic causes timing issues, simplify `onItemChecked` to use the same immediate approach as `onItemsChecked` (less optimal UX but functional).
</rollback>
</task>

### 4.2 Wire Composable into Page Orchestrator

<task id="4.2" status="pending" depends="4.1" risk="medium">
<context>
Modify `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` (194 lines) to initialize and expose the pantry composable.

**Current structure** (relevant lines):
- Line 7: imports useShoppingListCrud
- Line 13: `export function useShoppingListPage(listId: string)`
- Line 61-69: `const crud = useShoppingListCrud(shoppingList, loadingCounter, listItems, shoppingListItemActions, refresh, sortCheckedItems, updateListItemOrder)`
- Line 157-159: `onMounted(() => { startPolling(updateListItemOrder); })`
- Line 165-193: return object with `...state, ...labels, ...crud, ...recipes` spreads

**Changes**:

1. Add import (after line 8):
```typescript
import { useShoppingListPantry } from "./sub-composables/use-shopping-list-pantry";
```

2. Initialize composable (after the `crud` initialization, around line 69):
```typescript
const pantry = useShoppingListPantry(shoppingList);
```

3. Call `fetchDeficit()` on mount. Add to the existing `onMounted` block (line 157):
```typescript
onMounted(() => {
  startPolling(updateListItemOrder);
  pantry.fetchDeficit();
});
```

4. Spread pantry into return object (line 170, add after `...recipes`):
```typescript
return {
  // existing...
  ...pantry,
  // existing specialized functions...
};
```

**Note**: Task 4.5 will modify this file again to pass pantry callbacks to useShoppingListCrud. That is a separate concern.
</context>

<subtasks>
- [ ] Read `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` to confirm exact insertion points
- [ ] Add import for `useShoppingListPantry`
- [ ] Initialize pantry composable with `shoppingList` ref (after crud init)
- [ ] Add `pantry.fetchDeficit()` to onMounted
- [ ] Spread `...pantry` into return object
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- `useShoppingListPantry` is imported and initialized
- `fetchDeficit()` is called on mount
- All pantry state/methods are available via `useShoppingListPage()` return value (showCoverageBanner, coverageSummary, showPantryDialog, pendingActions, onItemChecked, onItemsChecked, executeDeduct, executeQuickAdd, dismissPantryDialog)
- Existing shopping list functionality is completely unchanged
- `task ui:lint` passes
</acceptance>
</task>

### 4.3 Add Coverage Banner to Shopping List Page

<task id="4.3" status="pending" depends="4.2" risk="low">
<context>
Modify `frontend/app/pages/shopping-lists/[id].vue` (412 lines) to display the pantry coverage banner.

**Current structure** (relevant lines):
- Line 354: `const id = route.params.id as string;`
- Line 356: `const shoppingListPage = useShoppingListPage(id);`
- Line 361-394: destructured variables from shoppingListPage

**Changes**:

1. Add pantry destructured variables (extend the existing destructure block at lines 361-394):
```typescript
const {
  // existing destructures...
  showCoverageBanner,
  coverageSummary,
} = shoppingListPage;
```

2. Add the coverage banner in the template. Insert after the `BasePageTitle` block (ends around line 153) and before the `<!-- Viewer -->` section (line 161):
```vue
<v-alert
  v-if="showCoverageBanner"
  type="info"
  variant="tonal"
  density="compact"
  class="mb-4"
>
  {{ coverageSummary }}
</v-alert>
```

**Upstream file concern**: `[id].vue` is an upstream file. Changes are minimal — additional destructured variables and one `v-alert` element. These are non-breaking additions.
</context>

<subtasks>
- [ ] Read `frontend/app/pages/shopping-lists/[id].vue` around lines 150-165 to confirm template insertion point
- [ ] Add `showCoverageBanner` and `coverageSummary` to the destructure block
- [ ] Add `v-alert` banner after BasePageTitle, before the viewer section
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- Banner appears on shopping list page when list has recipe references and deficit data loads
- Banner shows "X of Y items covered by pantry" with correct numbers
- Banner does NOT appear when list has no recipe references
- Banner does NOT appear while deficit data is loading (no flash — `showCoverageBanner` is false until deficitReport loads)
- Existing page layout is unchanged when banner is hidden
- `task ui:lint` passes
</acceptance>
</task>

### 4.4 Create Pantry Action Dialog Component

<task id="4.4" status="pending" depends="4.1" risk="medium">
<context>
Create `frontend/app/components/optimizer/ShoppingListPantryDialog.vue` — a dialog shown after checking off items that offers deduct-from-pantry or quick-add-to-pantry.

**IMPORTANT**: This file goes in `frontend/app/components/optimizer/` (NOT `Domain/ShoppingList/`) per CLAUDE.md fork isolation rules.

**Component pattern**: Use `BaseDialog` with `v-model` for visibility (standard Mealie pattern, used in 10+ pages including `[id].vue` itself).

**Props**:
```typescript
interface Props {
  modelValue: boolean;               // v-model for dialog visibility
  actions: PantryCheckoutAction[];   // items to act on
}
```

**Emits**:
```typescript
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "deduct", itemIds: string[]): void;
  (e: "quick-add", items: Array<{ foodId: string; quantity: number; unitId: string | null }>): void;
  (e: "dismiss"): void;
}>();
```

**Template structure**:
1. `BaseDialog` wrapper with `v-model`, title from i18n `optimizer.shopping.pantry-action-title`
2. **Section 1 — Items in pantry** (filter actions where `existsInPantry === true`):
   - Subheading: `optimizer.shopping.items-in-pantry`
   - List of items with checkboxes (all checked by default)
   - Each item shows: foodName, quantity, unitName
   - "Deduct from pantry" button → emits `deduct` with selected item IDs
3. **Section 2 — Items NOT in pantry** (filter actions where `existsInPantry === false`):
   - Subheading: `optimizer.shopping.items-not-in-pantry`
   - List of items with checkboxes (all checked by default)
   - "Add to pantry" button → emits `quick-add` with selected items
4. **Skip button** → emits `dismiss`

**Local state**: `selectedDeductIds: Ref<string[]>` and `selectedQuickAddItems: Ref<...[]>` for checkbox tracking. Initialize from props when dialog opens (watch `modelValue`).

If one section has no items, hide that section entirely. If BOTH sections are empty (no actionable items), don't show the dialog — this is handled by the composable's `onItemChecked`/`onItemsChecked`.

**Import**: `import type { PantryCheckoutAction } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-pantry";`

Use Vuetify components: `v-list`, `v-list-item`, `v-checkbox`, `v-btn`. Use i18n keys from `optimizer.shopping` namespace for all user-facing text.
</context>

<subtasks>
- [ ] Search for an existing BaseDialog usage (e.g., `grep -r "BaseDialog" --include="*.vue" -l`) to confirm the v-model pattern
- [ ] Create the component file at `frontend/app/components/optimizer/ShoppingListPantryDialog.vue`
- [ ] Define props and emits with TypeScript
- [ ] Implement two-section layout (deduct items, quick-add items)
- [ ] Add checkbox selection state with "select all" default, initialized on dialog open
- [ ] Wire action buttons to emit events with selected items
- [ ] Add Skip button that emits dismiss
- [ ] Import PantryCheckoutAction type from the composable
- [ ] Use i18n keys from optimizer.shopping namespace for ALL text
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- File exists at `frontend/app/components/optimizer/ShoppingListPantryDialog.vue`
- Dialog opens with items grouped by type (deduct vs. quick-add)
- All items are selected by default
- User can deselect individual items
- "Deduct from pantry" button emits `deduct` with selected item IDs only
- "Add to pantry" button emits `quick-add` with selected items only
- "Skip" button emits `dismiss`
- Empty sections are hidden
- No hardcoded strings — all text uses i18n
- `task ui:lint` passes
</acceptance>
</task>

### 4.5 Hook Checkout Callbacks into Shopping List CRUD

<task id="4.5" status="pending" depends="4.2" risk="high">
<context>
Hook pantry callbacks into BOTH checkout paths: `saveListItem` (individual check) and `checkAllItems` (batch check). This requires changes to two files.

**CRITICAL DESIGN NOTE**: `checkAllItems()` (use-shopping-list-crud.ts:38-49) does NOT call `saveListItem()`. It directly mutates `item.checked = true` on each item and calls `updateUncheckedListItems()`. A hook in `saveListItem()` alone would silently fail for "Check All". Both paths must be hooked.

**File 1: `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts`** (261 lines)

Current function signature (line 8-16):
```typescript
export function useShoppingListCrud(
  shoppingList: Ref<ShoppingListOut | null>,
  loadingCounter: Ref<number>,
  listItems: { unchecked: ShoppingListItemOut[]; checked: ShoppingListItemOut[] },
  shoppingListItemActions: any,
  refresh: () => void,
  sortCheckedItems: (a: ShoppingListItemOut, b: ShoppingListItemOut) => number,
  updateListItemOrder: () => void,
)
```

**Change 1a** — Add two optional callback parameters to the function signature:
```typescript
export function useShoppingListCrud(
  // ...existing 7 params...
  onItemChecked?: (item: ShoppingListItemOut) => void,
  onItemsChecked?: (items: ShoppingListItemOut[]) => void,
)
```

**Change 1b** — In `saveListItem` (line 79-102), detect check transition and call callback. The item arrives already in its new state (toggleChecked already flipped `checked`). Detect the transition by comparing against the previous state in `shoppingList.value.listItems`.

At the TOP of `saveListItem`, before the forEach at line 88, capture previous state:
```typescript
const wasChecked = shoppingList.value.listItems?.find(i => i.id === item.id)?.checked ?? false;
```

At the END of `saveListItem`, after `updateListItemOrder()` (line 101), add:
```typescript
if (item.checked && !wasChecked && item.foodId && onItemChecked) {
  onItemChecked(item);  // non-blocking — fire and forget
}
```

**Change 1c** — In `checkAllItems` (line 38-49), collect newly-checked items and call batch callback. Currently:
```typescript
function checkAllItems() {
  let hasChanged = false;
  shoppingList.value?.listItems?.forEach((item) => {
    if (!item.checked) {
      hasChanged = true;
      item.checked = true;
    }
  });
  if (hasChanged) {
    updateUncheckedListItems();
  }
}
```

Change to:
```typescript
function checkAllItems() {
  const newlyChecked: ShoppingListItemOut[] = [];
  shoppingList.value?.listItems?.forEach((item) => {
    if (!item.checked) {
      item.checked = true;
      newlyChecked.push(item);
    }
  });
  if (newlyChecked.length > 0) {
    updateUncheckedListItems();
    if (onItemsChecked) {
      const withFood = newlyChecked.filter(i => i.foodId);
      if (withFood.length > 0) {
        onItemsChecked(withFood);
      }
    }
  }
}
```

**File 2: `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts`**

Pass pantry callbacks to `useShoppingListCrud`. The current call (line 61-69):
```typescript
const crud = useShoppingListCrud(
  shoppingList, loadingCounter, listItems, shoppingListItemActions,
  refresh, sortCheckedItems, updateListItemOrder,
);
```

Change to:
```typescript
const crud = useShoppingListCrud(
  shoppingList, loadingCounter, listItems, shoppingListItemActions,
  refresh, sortCheckedItems, updateListItemOrder,
  pantry.onItemChecked,
  pantry.onItemsChecked,
);
```

**ORDERING NOTE**: `pantry` must be initialized BEFORE `crud` in use-shopping-list-page.ts. Task 4.2 places pantry init after crud. You must reorder: move the `const pantry = useShoppingListPantry(shoppingList);` line BEFORE the `const crud = useShoppingListCrud(...)` call.
</context>

<subtasks>
- [ ] Read `use-shopping-list-crud.ts` to confirm function signature and saveListItem/checkAllItems locations
- [ ] Add `onItemChecked` and `onItemsChecked` optional callback parameters to useShoppingListCrud
- [ ] In `saveListItem`: capture previous checked state, add post-check callback (non-blocking)
- [ ] In `checkAllItems`: collect newly-checked items, filter by foodId, call onItemsChecked
- [ ] Read `use-shopping-list-page.ts` to confirm current useShoppingListCrud call
- [ ] Move `pantry` initialization BEFORE `crud` initialization
- [ ] Pass `pantry.onItemChecked` and `pantry.onItemsChecked` to useShoppingListCrud
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- Checking a single item with foodId calls `onItemChecked` (verify with console.log temporarily)
- Unchecking an item does NOT call `onItemChecked`
- Items without foodId do NOT trigger `onItemChecked`
- "Check All" calls `onItemsChecked` with all newly-checked items that have foodId
- The check-off is never blocked — item is saved BEFORE the callback fires
- `checkAllItems` behavior unchanged when no callback provided (backward compatible)
- `task ui:lint` passes
</acceptance>

<rollback risk="high">
This task modifies an upstream-adjacent composable. If the change breaks check-off:
1. Remove the `onItemChecked`/`onItemsChecked` callback parameters
2. Revert `checkAllItems` to original (replace `newlyChecked` array with `hasChanged` boolean)
3. Revert `saveListItem` (remove wasChecked check and callback)
4. In use-shopping-list-page.ts, remove the callback arguments from useShoppingListCrud call

The core check-off flow (shoppingListItemActions.updateItem) executes BEFORE the callbacks, so even a crash in the callback should not prevent items from being checked.
</rollback>
</task>

### 4.6 Add Pantry Dialog to Shopping List Page

<task id="4.6" status="pending" depends="4.4,4.5" risk="low">
<context>
Add the `ShoppingListPantryDialog` component to `frontend/app/pages/shopping-lists/[id].vue` and wire its events to the pantry composable methods.

**Changes to [id].vue**:

1. Add pantry destructured variables (extend the existing destructure block, which was partially updated in Task 4.3):
```typescript
const {
  // existing + 4.3 additions...
  showPantryDialog,
  pendingActions,
  executeDeduct,
  executeQuickAdd,
  dismissPantryDialog,
} = shoppingListPage;
```

2. Add the dialog component at the bottom of the template, before `</v-container>`:
```vue
<ShoppingListPantryDialog
  v-model="showPantryDialog"
  :actions="pendingActions"
  @deduct="executeDeduct"
  @quick-add="executeQuickAdd"
  @dismiss="dismissPantryDialog"
/>
```

3. The component auto-imports via Nuxt's component auto-discovery (files in `components/` are auto-imported). Since the file is at `components/optimizer/ShoppingListPantryDialog.vue`, it's available as `<OptimizerShoppingListPantryDialog>` or can be imported explicitly. Check Nuxt's component resolution — if the `optimizer/` prefix is needed, use `<OptimizerShoppingListPantryDialog>` in the template instead.

**Upstream file concern**: This is the second modification to `[id].vue` (first was the banner in Task 4.3). The dialog is a non-breaking addition at the end of the template.
</context>

<subtasks>
- [ ] Add remaining pantry destructured variables to `[id].vue`
- [ ] Verify Nuxt component auto-import naming for `components/optimizer/ShoppingListPantryDialog.vue` (check if prefix is needed)
- [ ] Add dialog component at the bottom of the template
- [ ] Wire v-model, :actions prop, and @deduct/@quick-add/@dismiss events
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- Dialog component renders without errors
- Checking a shopping list item with foodId triggers the pantry dialog (after 300ms debounce for single items)
- "Check All" triggers one dialog with all actionable items (batch, no debounce)
- Unchecking an item does NOT trigger the dialog
- Items without foodId never trigger the dialog
- Clicking "Deduct" calls executeDeduct, shows success toast, refreshes banner
- Clicking "Add to pantry" calls executeQuickAdd, shows success toast, refreshes banner
- Clicking "Skip" dismisses without action
- `task ui:lint` passes
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes (existing tests still work)
- [ ] Shopping list page loads without errors
- [ ] Coverage banner appears for lists with recipe references
- [ ] Coverage banner is absent for lists without recipe references
- [ ] Checking an item with foodId shows the pantry dialog (single item, debounced)
- [ ] "Check All" shows one batched dialog with all actionable items
- [ ] Unchecking an item does NOT show the dialog
- [ ] Deduct action updates pantry quantities
- [ ] Quick-add action creates pantry items
- [ ] Skip dismisses the dialog
- [ ] Banner refreshes after pantry actions
- [ ] Existing shopping list CRUD (create, edit, delete, reorder) still works
</verification>
<gate>Full C2+C3 frontend integration is functional. All pantry actions work end-to-end with the backend. No regressions in existing shopping list functionality.</gate>
</checkpoint>

</phase>

---

## Phase 5: Final Validation

<phase id="5" name="Final Validation" depends="4">

### 5.1 End-to-End Smoke Test and Code Review

<task id="5.1" status="pending" depends="4.6" risk="low">
<context>
Perform a full end-to-end test of all three sub-features (C1, C2, C3) together, followed by a code quality review of all new and modified files.

**Test setup**:
1. Start dev environment: `task dev:services`, `task py:migrate`, `task py:postgres`, `task ui`
2. Ensure pantry has a few items with quantities (create via /optimizer/pantry page)
3. Create a shopping list by adding a recipe that uses some pantry foods

**C1 test** (auto-section):
- Verify items are grouped by label sections
- Verify ungrouped items appear in default section

**C2 test** (deficit banner):
- Verify coverage banner appears with correct "X of Y items covered" count
- Verify banner disappears if all recipe references are removed

**C3 test** (deduct/quick-add):
- Check off an item that has a matching pantry food → dialog offers "Deduct"
- Click "Deduct" → verify pantry quantity decreases
- Check off an item NOT in pantry → dialog offers "Add to pantry"
- Click "Add to pantry" → verify new pantry item created
- Click "Skip" → verify no pantry changes
- Use "Check All" → verify single batched dialog appears (not N individual dialogs)
- Verify banner refreshes after deduct/quick-add
- Uncheck an item → verify NO dialog appears

**Regression checks**:
- Create/edit/delete shopping list items still works
- Reorder items still works
- Recipe reference add/remove still works
- Shopping list copy still works

**Code review checklist**:
- No hardcoded strings (all user-facing text uses i18n)
- No console.log statements left in production code (console.error is OK for error handling)
- Error handling is graceful (try/catch with silent degradation)
- Pantry actions never block the check-off flow
- TypeScript types match backend schemas
- All new files in optimizer/ directories (verify ShoppingListPantryDialog.vue is NOT in Domain/ShoppingList/)
- Fork isolation maintained

**CLAUDE.md update**: Add three new upstream file modifications to the "Modified Upstream Files" section:
- `frontend/app/pages/shopping-lists/[id].vue` — pantry coverage banner + dialog
- `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` — pantry composable wiring
- `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts` — pantry checkout callbacks
</context>

<subtasks>
- [ ] Run `task py:lint` — passes
- [ ] Run `task ui:lint` — passes
- [ ] Run `task ui:test` — passes
- [ ] Start full dev environment
- [ ] Test C1: auto-section assignment
- [ ] Test C2: deficit coverage banner (appears/disappears correctly)
- [ ] Test C3: single-item deduct flow
- [ ] Test C3: single-item quick-add flow
- [ ] Test C3: skip/dismiss flow
- [ ] Test C3: "Check All" shows single batched dialog
- [ ] Regression: CRUD operations unchanged
- [ ] Regression: recipe references unchanged
- [ ] Verify Swagger docs show all new endpoints correctly
- [ ] Review all new/modified files against code review checklist
- [ ] Update CLAUDE.md "Modified Upstream Files" section with three new entries
</subtasks>

<acceptance>
- All C1/C2/C3 features work as described
- No JavaScript console errors on the shopping list page
- No Python backend errors in terminal output
- All lint and test commands pass
- Swagger docs show correct endpoint documentation
- CLAUDE.md reflects all upstream file modifications
- No hardcoded strings, no debug logging in production code
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] All features work end-to-end
- [ ] All lint and test suites pass
- [ ] Code review complete with no issues
- [ ] CLAUDE.md updated with new upstream file entries
</verification>
<gate>Stage C (Shopping List Enhancements) is complete and ready for use.</gate>
</checkpoint>

</phase>

---

## Final Validation

<final_validation>
<verification>
- [ ] `task py:lint` passes
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Swagger docs show all new endpoints
- [ ] C1: Auto-section assignment verified
- [ ] C2: Deficit coverage banner works
- [ ] C3: Deduct-on-checkout works (single item)
- [ ] C3: Quick-add-to-pantry works (single item)
- [ ] C3: Check All batching works (one dialog for all items)
- [ ] No regressions in shopping list CRUD
- [ ] No regressions in recipe reference management
- [ ] Fork isolation rules followed — all new code in optimizer/ dirs
</verification>
<acceptance>All three sub-features (C1 verify, C2 deficit banner, C3 deduct/quick-add) are functional. The shopping list page integrates with the pantry system without breaking any existing functionality. New backend endpoints are documented in Swagger. All code follows fork isolation rules. CLAUDE.md is updated.</acceptance>
</final_validation>

---

## Risk Mitigation

<risks>
<risk id="R1" likelihood="medium" impact="high">
  <description>checkAllItems batch callback fires with stale or incomplete item data because items are mutated in-place before the callback</description>
  <mitigation>The callback in checkAllItems is called AFTER updateUncheckedListItems, which persists items to the API. Items passed to onItemsChecked are already in their final state. The composable reads foodId/quantity/unitId from the items, which are set during bulk_create_items and do not change during check-off.</mitigation>
  <detection>Dialog shows wrong items or missing food names. Verify by logging the items array in onItemsChecked during testing.</detection>
</risk>
<risk id="R2" likelihood="low" impact="high">
  <description>Route ordering error causes FastAPI to match "deduct-shopping-items" or "quick-add" as /{item_id} parameter, resulting in silent 422 errors</description>
  <mitigation>Task 2.3 explicitly documents the required ordering. The existing file already has 4 POST endpoints before /{item_id} as a proven pattern.</mitigation>
  <detection>422 validation errors when calling the new endpoints. Verify in Swagger docs — if endpoints appear after /{item_id}, reorder the methods in the controller class.</detection>
</risk>
<risk id="R3" likelihood="medium" impact="medium">
  <description>Debounce timing in onItemChecked causes dialog to appear after user has navigated away or started editing another item</description>
  <mitigation>300ms is short enough that users are unlikely to navigate away. The dialog is non-blocking (if dismissed or ignored, no harm done). Fallback: remove debounce entirely and show dialog immediately on each single check.</mitigation>
  <detection>Dialog appears unexpectedly or after navigation. User reports seeing stale dialogs.</detection>
</risk>
<risk id="R4" likelihood="low" impact="medium">
  <description>Deficit banner shows recipe-level coverage, not shopping-list-item-level coverage, which may confuse users when item quantities have been adjusted</description>
  <mitigation>This is a known simplification documented in the spec. The banner shows "X of Y items covered by pantry" based on recipe ingredient coverage, not individual item quantities. Accurate enough for the summary use case.</mitigation>
  <detection>User reports mismatch between banner numbers and actual pantry state after manual quantity adjustments.</detection>
</risk>
<risk id="R5" likelihood="low" impact="low">
  <description>Nuxt component auto-import uses "OptimizerShoppingListPantryDialog" prefix for components in optimizer/ subdirectory</description>
  <mitigation>Task 4.6 includes a subtask to verify the auto-import naming. If the prefix is needed, use it in the template. Alternatively, add an explicit import statement.</mitigation>
  <detection>Component not found error at runtime. Check browser console for resolution errors.</detection>
</risk>
</risks>

---

## Dependency Verification Log

<dependency_log>
<dependency name="AllRepositories.group_shopping_list_item" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/repos/repository_factory.py:317-325 — property exists, returns HouseholdRepositoryGeneric[ShoppingListItemOut, ShoppingListItem]</verified_via>
  <notes>Household-scoped — returns items filtered by group_id + household_id. PantryService can access via self.repos.group_shopping_list_item.</notes>
</dependency>
<dependency name="PantryService.get_pantry_map()" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/services/optimizer/pantry.py — method exists, returns dict[UUID4, PantryItemOut] keyed by food_id</verified_via>
  <notes>Used by both deduct_recipe (existing) and deduct_shopping_items (new). Tested pattern.</notes>
</dependency>
<dependency name="PantryService.converter (UnitConverter)" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/services/optimizer/pantry.py:__init__ — self.converter = UnitConverter()</verified_via>
  <notes>Used for unit conversion in deduct_recipe. Same converter used for deduct_shopping_items.</notes>
</dependency>
<dependency name="ShoppingListOut.recipeReferences" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read frontend/app/lib/api/types/household.ts:685 — recipeReferences?: ShoppingListRecipeRefOut[] with recipeId: string</verified_via>
  <notes>Optional field. Composable must handle null/undefined/empty array gracefully.</notes>
</dependency>
<dependency name="ShoppingListItemOut fields (foodId, quantity, unitId)" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read frontend/app/lib/api/types/household.ts:573-595 — all three fields exist (optional)</verified_via>
  <notes>All optional — composable/service must handle null values.</notes>
</dependency>
<dependency name="BaseDialog component" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Grep found BaseDialog used in 10+ .vue files including shopping-lists/[id].vue</verified_via>
  <notes>Standard Mealie dialog pattern. Uses v-model for visibility.</notes>
</dependency>
<dependency name="useDebounceFn from @vueuse/core" verified="true">
  <version>N/A (project dependency)</version>
  <verified_via>@vueuse/core is in package.json; useLocalStorage and useOnline already imported from it in use-shopping-list-item-actions.ts</verified_via>
  <notes>useDebounceFn is part of the same package. No additional install needed.</notes>
</dependency>
<dependency name="useUserApi → optimizer.pantry access chain" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Verified: useUserApi() → UserApi.optimizer → OptimizerApi.pantry → PantryItemsApi. Full chain confirmed in client-user.ts.</verified_via>
  <notes>Standard pattern for API access in Mealie composables.</notes>
</dependency>
<dependency name="PantryItemSave schema" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/schema/optimizer/pantry.py — PantryItemSave extends PantryItemCreate, adds group_id + household_id</verified_via>
  <notes>PantryItemCreate has model_validator requiring food_id OR name. PantryQuickAddItem.food_id is required (non-optional), so validator passes.</notes>
</dependency>
<dependency name="checkAllItems direct mutation pattern" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read use-shopping-list-crud.ts:38-49 — forEach mutates item.checked=true, calls updateUncheckedListItems(), does NOT call saveListItem()</verified_via>
  <notes>This is why Task 4.5 hooks BOTH saveListItem and checkAllItems. The original plan missed this path.</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should the pantry dialog batch actions when "Check All" is used, or show one dialog per item?</question>
  <default_assumption>Batch: the revised plan adds `onItemsChecked()` (batch callback in checkAllItems) that collects all items and shows one dialog immediately, with no debounce. Single-item checks use `onItemChecked()` with 300ms debounce.</default_assumption>
  <impact>Resolved by design — batch for Check All, debounced for single items.</impact>
</question>
<question id="Q2" blocking="false" owner="agent" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should the deficit banner refresh after deduct/quick-add actions, or only on page load?</question>
  <default_assumption>Refresh after any pantry mutation. executeDeduct and executeQuickAdd both call fetchDeficit() on completion.</default_assumption>
  <impact>Implemented in Task 4.1 composable design.</impact>
</question>
<question id="Q3" blocking="false" owner="human" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should quick-add pre-fill expiration_date or use_priority from any source?</question>
  <default_assumption>No pre-fill. Create with defaults (no expiration, use_priority="auto", is_staple=False, assume_enough=False). User can edit later.</default_assumption>
  <impact>Minor UX — no good data source exists on shopping list items for these fields.</impact>
</question>
<question id="Q4" blocking="false" owner="agent">
  <question>Should the pantry dialog show a success toast/snackbar after deduct or quick-add?</question>
  <default_assumption>Yes, show a toast using the existing Mealie snackbar pattern. Use the i18n keys deducted-count and added-count for pluralized feedback.</default_assumption>
  <impact>Implemented in Task 4.1 composable (executeDeduct/executeQuickAdd show toast on success).</impact>
</question>
<question id="Q5" blocking="false" owner="agent">
  <question>How should the onItemChecked callback determine if a food "exists in pantry" for the PantryCheckoutAction.existsInPantry flag?</question>
  <default_assumption>Use deficitReport: if the food appears in deficitReport.items with a pantry match (non-null pantryQuantity), existsInPantry=true. If deficitReport is null (never loaded or failed), treat all items as "not in pantry" (offer quick-add). This is conservative and safe.</default_assumption>
  <impact>Determines dialog section assignment. Conservative approach avoids accidental deductions.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
<resolved original_question="Does AllRepositories expose a shopping list items repository for PantryService to query?">
  <resolution>Yes — confirmed at repository_factory.py:317-325. AllRepositories.group_shopping_list_item returns HouseholdRepositoryGeneric[ShoppingListItemOut, ShoppingListItem]. PantryService accesses it via self.repos.group_shopping_list_item.</resolution>
</resolved>
</resolved_from_source>

---

## Plan Review Notes

<codex_response>
Codex review unavailable — "The 'gpt-5.2-codex' model is not supported when using Codex with a ChatGPT account." Structural review conducted via independent Claude agent analysis with codebase verification.
</codex_response>
