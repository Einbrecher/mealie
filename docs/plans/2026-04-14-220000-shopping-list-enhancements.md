# Implementation Plan: Shopping List Enhancements (Stage C)
Source: docs/specs/2026-04-14-210000-shopping-list-enhancements.md
Created: 2026-04-14

<plan_metadata>
  <feature>Shopping List Pantry Integration (C1 verify, C2 deficit banner, C3 deduct/quick-add)</feature>
  <source_doc>docs/specs/2026-04-14-210000-shopping-list-enhancements.md</source_doc>
  <total_phases>5</total_phases>
  <total_tasks>14</total_tasks>
  <critical_path>2.1 → 2.2 → 2.3 → 3.1 → 3.2 → 4.1 → 4.2 → 4.3 → 4.4 → 5.1</critical_path>
  <status>draft</status>
</plan_metadata>

## Overview

This plan adds pantry integration to Mealie's existing shopping list page in three sub-features: (C1) verifying that auto-section assignment already works, (C2) adding a deficit coverage banner showing how many items are covered by pantry, and (C3) offering deduct-from-pantry and quick-add-to-pantry actions when users check off shopping list items. The backend adds two new endpoints to the existing PantryItemController; the frontend adds a new sub-composable, a dialog component, and minimal modifications to the shopping list page and CRUD composable.

## Dependencies & Prerequisites

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
  <verification>Confirmed at mealie/repos/repository_factory.py:317-325 — returns HouseholdRepositoryGeneric[ShoppingListItemOut, ShoppingListItem]</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>Frontend optimizer API client with PantryItemsApi, OptimizerApi classes</description>
  <verification>File exists: frontend/app/lib/api/user/optimizer-pantry.ts (75 lines, routes + 4 API methods confirmed)</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>ShoppingListOut.recipeReferences with recipeId field for deficit calculation</description>
  <verification>Confirmed at frontend/app/lib/api/types/household.ts:685 — recipeReferences?: ShoppingListRecipeRefOut[] with recipeId: string</verification>
</prereq>
<prereq id="P6" type="environment" verified="true">
  <description>Shopping list page with sub-composable pattern (7 sub-composables orchestrated by use-shopping-list-page.ts)</description>
  <verification>File exists: frontend/app/composables/shopping-list-page/use-shopping-list-page.ts (194 lines, imports 7 sub-composables)</verification>
</prereq>
</prerequisites>

---

## Phase 1: C1 — Verify Auto-Section Assignment

<phase id="1" name="Verify Auto-Section Assignment">

### 1.1 Manual Verification of Label Assignment

<task id="1.1" status="pending" depends="" risk="low">
<description>
C1 is a verification-only task. The shopping list already has auto-section assignment via two mechanisms:

**Backend** (mealie/services/household_services/shopping_lists.py:145-152):
`find_matching_label()` resolves a label_id for each new item in three steps:
1. Item already has label_id → use it
2. Item has food with food.label_id → use it
3. Fuzzy match on item.display text via `self.data_matcher.find_food_match()` → use food_search.label_id

**Frontend** (use-shopping-list-sorting.ts):
`updateItemsByLabel()` groups unchecked items by `label.name` into collapsible expansion panels on the shopping list page.

Verify this works end-to-end by testing at localhost:3000 with a running backend (localhost:9000).
</description>

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
<success_criteria>C1 is confirmed working or gaps documented. No code changes produced by this phase.</success_criteria>
</checkpoint>

</phase>

---

## Phase 2: C3 Backend — New Schemas, Service Methods, Endpoints

<phase id="2" name="C3 Backend" depends="1">

### 2.1 Add Request Schemas

<task id="2.1" status="pending" depends="" risk="low">
<description>
Add two new Pydantic request schemas to `mealie/schema/optimizer/pantry.py` for the deduct-by-shopping-items and quick-add-to-pantry endpoints.

**File**: `mealie/schema/optimizer/pantry.py` (currently 144 lines)

Add these schemas **after** the existing `PantryDeductRequest` class (around line 115) and **before** `PantryImportResult`:

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

All schemas extend `MealieModel` which provides the snake_case → camelCase alias generator. No custom validators needed — `shopping_list_item_ids` is a simple list of UUIDs, and `PantryQuickAddItem` requires only `food_id`.
</description>

<subtasks>
- [ ] Read `mealie/schema/optimizer/pantry.py` to confirm current end-of-file structure
- [ ] Add `ShoppingItemDeductRequest` class after `PantryDeductRequest`
- [ ] Add `PantryQuickAddItem` class
- [ ] Add `PantryQuickAddRequest` class
- [ ] Verify imports: `UUID4` from `pydantic` is already imported at the top of the file
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer.pantry import ShoppingItemDeductRequest, PantryQuickAddRequest, PantryQuickAddItem"` succeeds
- Schemas serialize to camelCase: `ShoppingItemDeductRequest(shopping_list_item_ids=[...]).model_dump(by_alias=True)` produces `{"shoppingListItemIds": [...]}`
- `task py:lint` passes
</acceptance>
</task>

### 2.2 Add PantryService Methods

<task id="2.2" status="pending" depends="2.1" risk="medium">
<description>
Add two new methods to `PantryService` in `mealie/services/optimizer/pantry.py` (currently 476 lines):

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

**Cross-domain access**: PantryService needs to read shopping list items via `self.repos.group_shopping_list_item`. This is already available through AllRepositories (confirmed at repository_factory.py:317-325). The service currently accesses `self.repos.pantry_items` — accessing another repo on the same AllRepositories instance is the standard Mealie pattern.

**Import needed**: Add `from mealie.schema.optimizer.pantry import PantryItemSave, ShoppingItemDeductRequest, PantryQuickAddItem` if not already imported. Also need `ShoppingListItem` model or use the repo's get_one method which returns `ShoppingListItemOut`.
</description>

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
These methods are additive — they don't modify existing methods. If something breaks, delete the two new methods. The risk is in the cross-domain repo access pattern; if group_shopping_list_item returns items scoped differently than expected, the deduction logic could operate on wrong data. Mitigate by verifying household_id scoping in the repository.
</rollback>
</task>

### 2.3 Add Controller Endpoints

<task id="2.3" status="pending" depends="2.2" risk="medium">
<description>
Add two new POST endpoints to `PantryItemController` in `mealie/routes/optimizer/controller_pantry.py` (currently 99 lines).

**CRITICAL: Route ordering**. The file has a comment at line 48: "All POST endpoints must be before /{item_id} to avoid route conflict." The new endpoints MUST be placed after the existing POST /deduct (around line 75) and BEFORE the GET "" / POST "" block (around line 78). If placed after /{item_id}, FastAPI will interpret "deduct-shopping-items" and "quick-add" as item_id path parameters.

**Current endpoint order** (for reference):
1. POST /deficit
2. POST /deficit/meal-plan
3. POST /import-on-hand
4. POST /deduct
5. → NEW: POST /deduct-shopping-items (insert here)
6. → NEW: POST /quick-add (insert here)
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
- Implementation: Extract (food_id, quantity, unit_id) tuples from data.items, pass to `self.service.quick_add_from_shopping()` with group_id and household_id from self.

**Import additions**: Add `ShoppingItemDeductRequest`, `PantryQuickAddRequest` to the import from `mealie.schema.optimizer.pantry`.

Follow the existing endpoint pattern — each is a method on the `PantryItemController` class decorated with `@router.post(...)`. Access group_id/household_id via `self.group_id` and `self.household_id` (inherited from BaseCrudController).
</description>

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
If route ordering is wrong, FastAPI silently matches the wrong handler. Symptoms: 422 validation errors when calling the new endpoints (because item_id UUID validation fails on "deduct-shopping-items" string). Fix: reorder methods in the controller class. The controller uses `@controller(router)` which registers routes in method definition order.
</rollback>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task py:lint` passes
- [ ] Backend starts without errors: `task py:postgres`
- [ ] Swagger docs show both new endpoints at correct paths
- [ ] Can call POST /deduct-shopping-items with a valid request body (even if no data exists, should return empty list)
- [ ] Can call POST /quick-add with a valid request body (should create items or return empty if foods exist)
</verification>
<success_criteria>Both new endpoints are functional, appear in Swagger, and follow existing authentication/household-isolation patterns.</success_criteria>
</checkpoint>

</phase>

---

## Phase 3: Frontend Infrastructure — Types, API Client, i18n

<phase id="3" name="Frontend Infrastructure" depends="2">

### 3.1 Add TypeScript Types

<task id="3.1" status="pending" depends="" risk="low">
<description>
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

Field names must be camelCase to match the backend's alias generator output. The `ShoppingItemDeductRequest.shoppingListItemIds` maps to the backend's `shopping_list_item_ids`. Optional fields use `?` with `| null` to match Pydantic's `float | None = None` pattern.
</description>

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
<description>
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

**Imports to add**: `ShoppingItemDeductRequest`, `PantryQuickAddRequest` from `~/lib/api/types/optimizer`. Check what's already imported — the file imports from `~/lib/api/types/optimizer` for existing types like `PantryDeficitRequest`.
</description>

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
- Import types match the interfaces added in task 3.1
- `task ui:lint` passes
</acceptance>
</task>

### 3.3 Add i18n Keys

<task id="3.3" status="pending" depends="" risk="low">
<description>
Add i18n keys for all new user-facing strings to `frontend/app/lang/messages/en-US.json` (currently 1549 lines).

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

Place this new `"shopping"` key after the `"planner"` key (around line 1547), inside the `"optimizer"` object. Pluralization uses the vue-i18n pipe syntax (`singular | plural`).
</description>

<subtasks>
- [ ] Read `frontend/app/lang/messages/en-US.json` around lines 1545-1549 to confirm the end of the optimizer object
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
- [ ] TypeScript types compile: no errors from `npx nuxi typecheck` or IDE
- [ ] API client methods reference correct routes matching backend endpoints
- [ ] i18n keys are valid JSON and nested under optimizer.shopping
</verification>
<success_criteria>All frontend infrastructure (types, API client, i18n) is in place for Phase 4 composable and component work.</success_criteria>
</checkpoint>

</phase>

---

## Phase 4: Frontend Integration — Composable, Banner, Dialog, CRUD Hook

<phase id="4" name="Frontend Integration" depends="3">

### 4.1 Create Shopping List Pantry Composable

<task id="4.1" status="pending" depends="3.2" risk="high">
<description>
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

**PantryCheckoutAction interface** (define in this file):
```typescript
interface PantryCheckoutAction {
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

1. `fetchDeficit()`: Extract `recipeIds` from `shoppingList.value.recipeReferences.map(ref => ref.recipeId)`. Call `api.optimizer.pantry.calculateDeficit({ recipeIds })`. Store result in `deficitReport`. Handle empty recipeReferences (return early, don't call API).

2. `onItemChecked(item: ShoppingListItemOut)`: Called when an item transitions to checked. If `item.foodId` is null, return. Check if food exists in `deficitReport.items` (by foodId match). Build a `PantryCheckoutAction` and add to `pendingActions`. Use **debounce** (300ms) before setting `showPantryDialog = true` — this batches multiple items when "Check All" is used. After debounce, if `pendingActions.length > 0`, show dialog.

3. `executeDeduct(itemIds: string[])`: Call `api.optimizer.pantry.deductShoppingItems({ shoppingListItemIds: itemIds })`. On success, clear those items from `pendingActions`. Refresh deficit data by calling `fetchDeficit()`.

4. `executeQuickAdd(items: Array<{foodId, quantity, unitId}>)`: Call `api.optimizer.pantry.quickAdd({ items })`. On success, clear those items from `pendingActions`. Refresh deficit data.

5. `dismissPantryDialog()`: Set `showPantryDialog = false`, clear `pendingActions`.

**API access**: Use `const api = useUserApi()` (existing composable pattern, see other sub-composables).

**Debounce implementation**: Use `useDebounceFn` from `@vueuse/core` (already a project dependency, used elsewhere). Create a debounced function that checks `pendingActions.length > 0` and sets `showPantryDialog = true`.

**Important**: The composable must be exported as a named export. Return an object spreading state + methods.
</description>

<subtasks>
- [ ] Create the file at `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts`
- [ ] Define `PantryCheckoutAction` interface
- [ ] Implement reactive state (deficitReport, deficitLoading, pendingActions, showPantryDialog)
- [ ] Implement `coverageSummary` computed using `useI18n().t("optimizer.shopping.coverage-banner", { covered, total })`
- [ ] Implement `showCoverageBanner` computed — true only when deficitReport is non-null AND shoppingList has recipeReferences
- [ ] Implement `fetchDeficit()` — extract recipe IDs from recipeReferences, call deficit endpoint
- [ ] Implement `onItemChecked()` with 300ms debounce for batching
- [ ] Implement `executeDeduct()` and `executeQuickAdd()` with deficit refresh
- [ ] Implement `dismissPantryDialog()`
- [ ] Export the composable function and the PantryCheckoutAction interface
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- File exists and exports `useShoppingListPantry` function
- `fetchDeficit()` calls POST /deficit with recipe IDs from shoppingList.recipeReferences
- `coverageSummary` returns i18n-formatted string with covered/total counts
- `showCoverageBanner` is false when deficitReport is null or shoppingList has no recipeReferences
- `onItemChecked()` accumulates actions and debounces dialog display (300ms)
- `executeDeduct()` calls deductShoppingItems API and refreshes deficit
- `executeQuickAdd()` calls quickAdd API and refreshes deficit
- `task ui:lint` passes
</acceptance>

<rollback risk="high">
This is the most complex new file. If the composable has issues, the banner and dialog won't work, but the shopping list page itself is unaffected since this composable is only wired in by task 4.2. If the debounce logic causes issues with "Check All", simplify to immediate dialog display (remove debounce, show dialog on each check — less optimal UX but functional).
</rollback>
</task>

### 4.2 Wire Composable into Shopping List Page

<task id="4.2" status="pending" depends="4.1" risk="medium">
<description>
Modify two files to wire the pantry composable into the shopping list page:

**File 1: `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts`** (194 lines)

Changes:
1. Add import: `import { useShoppingListPantry } from "./sub-composables/use-shopping-list-pantry";`
2. Inside `useShoppingListPage()`, after the existing sub-composable initializations (around line 50-100), add:
   ```typescript
   const pantry = useShoppingListPantry(shoppingList);
   ```
3. Call `pantry.fetchDeficit()` after initial data load. The existing `onMounted` (line 157) calls `startPolling(updateListItemOrder)`. Add `pantry.fetchDeficit()` either in onMounted or as a watcher on `shoppingList` that fires once when it becomes non-null.
4. Add pantry exports to the return object. Spread `...pantry` or add named exports:
   ```typescript
   return {
     // existing exports...
     ...pantry,  // showCoverageBanner, coverageSummary, showPantryDialog, pendingActions, etc.
   };
   ```

**File 2: `frontend/app/pages/shopping-lists/[id].vue`** (412 lines)

Changes:
1. Add pantry-related destructured variables from `useShoppingListPage` (around line 356-394):
   ```typescript
   const {
     // existing destructures...
     showCoverageBanner,
     coverageSummary,
     showPantryDialog,
     pendingActions,
     onItemChecked,
     executeDeduct,
     executeQuickAdd,
     dismissPantryDialog,
   } = useShoppingListPage(listId);
   ```

2. Add the coverage banner in the template. Insert after `BasePageTitle` (ends around line 153) and before the `<!-- Viewer -->` section (line 161):
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

**Upstream file concern**: `[id].vue` is an upstream file. The changes are minimal — one `v-alert` element and additional destructured variables. These are non-breaking additions.
</description>

<subtasks>
- [ ] Read `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` to identify exact insertion points
- [ ] Add import for `useShoppingListPantry`
- [ ] Initialize pantry composable with `shoppingList` ref
- [ ] Add `fetchDeficit()` call after data loads (watch or onMounted)
- [ ] Add pantry exports to return object
- [ ] Read `frontend/app/pages/shopping-lists/[id].vue` to identify template insertion point
- [ ] Add destructured pantry variables
- [ ] Add `v-alert` banner after BasePageTitle, before viewer section
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- Banner appears on shopping list page when list has recipe references and deficit data loads
- Banner shows "X of Y items covered by pantry" with correct numbers
- Banner does NOT appear when list has no recipe references
- Banner does NOT appear while deficit data is loading (no flash)
- Existing shopping list functionality is completely unchanged
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If the banner breaks the page, remove the `v-alert` element and the pantry destructured variables. The composable initialization in use-shopping-list-page.ts is safe even if unused — it just fetches data that nobody reads.
</rollback>
</task>

### 4.3 Create Pantry Action Dialog Component

<task id="4.3" status="pending" depends="4.1" risk="medium">
<description>
Create `frontend/app/components/Domain/ShoppingList/ShoppingListPantryDialog.vue` — a dialog shown after checking off items that offers deduct-from-pantry or quick-add-to-pantry.

**Component pattern**: Follow existing Mealie dialog patterns. The codebase uses `BaseDialog` extensively (found in 10+ pages). Use `v-model` for visibility binding.

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
1. `BaseDialog` wrapper with `v-model` bound to `modelValue`, title from i18n `optimizer.shopping.pantry-action-title`
2. **Section 1 — Items in pantry** (filter actions where `existsInPantry === true`):
   - Subheading: `optimizer.shopping.items-in-pantry`
   - List of items with checkboxes (all checked by default)
   - Each item shows: foodName, quantity, unitName
   - "Deduct from pantry" button → emits `deduct` with selected item IDs
3. **Section 2 — Items NOT in pantry** (filter actions where `existsInPantry === false`):
   - Subheading: `optimizer.shopping.items-not-in-pantry`
   - List of items with checkboxes (all checked by default)
   - Each item shows: foodName, quantity, unitName
   - "Add to pantry" button → emits `quick-add` with selected items
4. **Skip button** → emits `dismiss`

**Local state**: `selectedDeductIds: Ref<string[]>` and `selectedQuickAddItems: Ref<...[]>` for checkbox tracking. Initialize from props on open.

Use Vuetify components: `v-list`, `v-list-item`, `v-checkbox`, `v-btn`. Keep it simple — no complex layouts.

If one section has no items (e.g., all items are in pantry), hide that section entirely. If BOTH sections are empty (no actionable items), don't show the dialog at all — this should be handled by the composable's `onItemChecked`.
</description>

<subtasks>
- [ ] Read an existing BaseDialog usage (e.g., from `frontend/app/pages/shopping-lists/[id].vue` or search for BaseDialog pattern) to confirm the v-model pattern
- [ ] Create the component file
- [ ] Define props and emits with TypeScript
- [ ] Implement two-section layout (deduct items, quick-add items)
- [ ] Add checkbox selection state with "select all" default
- [ ] Wire action buttons to emit events with selected items
- [ ] Add Skip button that emits dismiss
- [ ] Import PantryCheckoutAction type from the composable
- [ ] Use i18n keys from optimizer.shopping namespace
- [ ] Run `task ui:lint`
</subtasks>

<acceptance>
- Dialog opens with items grouped by type (deduct vs. quick-add)
- All items are selected by default
- User can deselect individual items
- "Deduct from pantry" button emits `deduct` with selected item IDs
- "Add to pantry" button emits `quick-add` with selected items (foodId, quantity, unitId)
- "Skip" button emits `dismiss`
- Empty sections are hidden
- `task ui:lint` passes
</acceptance>
</task>

### 4.4 Hook Pantry Action into Checkout Flow

<task id="4.4" status="pending" depends="4.2,4.3" risk="high">
<description>
Wire the pantry dialog into the shopping list checkout flow. This requires changes to two files:

**File 1: `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts`** (261 lines)

The `saveListItem` function (lines 79-102) is called when an item is checked (`@checked="saveListItem"` in the page template) or saved (`@save="saveListItem"`). It currently:
1. Sets `item.updatedAt` timestamp
2. Updates local arrays (unchecked/checked)
3. Calls `shoppingListItemActions.updateItem(item)`
4. Calls `updateListItemOrder()`

**Change needed**: After the existing logic, detect if the item transitioned to `checked=true` and has a `foodId`, then call an `onItemChecked` callback.

The challenge is that `saveListItem` receives the item already in its new state (toggleChecked already flipped `checked`). To detect a check transition (not just "item is checked"), we need to compare against the previous state. The previous state is available in `shoppingList.value.listItems` — find the item by ID and check if it was previously unchecked.

**Implementation approach**:
1. Add an `onItemChecked` parameter to the `useShoppingListCrud` function signature. The composable factory pattern allows this — check how existing parameters are passed (e.g., `shoppingList`, `loadingCounter` are already passed).
2. At the TOP of `saveListItem`, before updating local arrays, capture the previous checked state:
   ```typescript
   const wasChecked = shoppingList.value?.listItems?.find(i => i.id === item.id)?.checked ?? false;
   ```
3. After the existing logic (after `updateListItemOrder()`), add:
   ```typescript
   if (item.checked && !wasChecked && item.foodId) {
     onItemChecked?.(item);  // non-blocking — fire and forget
   }
   ```
4. The `onItemChecked` callback is the `onItemChecked` method from `useShoppingListPantry`.

**File 2: `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts`**

Pass `pantry.onItemChecked` to `useShoppingListCrud` as the new parameter. Check the current `useShoppingListCrud` call to see what parameters it already accepts.

**File 3: `frontend/app/pages/shopping-lists/[id].vue`**

Add the `ShoppingListPantryDialog` component to the template:
```vue
<ShoppingListPantryDialog
  v-model="showPantryDialog"
  :actions="pendingActions"
  @deduct="executeDeduct"
  @quick-add="executeQuickAdd"
  @dismiss="dismissPantryDialog"
/>
```

Place it at the bottom of the template, before `</v-container>`. Import the component.

**CRITICAL**: The check-off must NEVER be blocked or delayed by pantry actions. The `onItemChecked` call is fire-and-forget (no await). The dialog appears AFTER the item is already saved. If the dialog or pantry API fails, the item remains checked.
</description>

<subtasks>
- [ ] Read `use-shopping-list-crud.ts` to confirm the function signature and parameter pattern
- [ ] Read `use-shopping-list-page.ts` to confirm how useShoppingListCrud is called
- [ ] Modify `useShoppingListCrud` to accept an optional `onItemChecked` callback parameter
- [ ] In `saveListItem`, capture previous checked state BEFORE updating local arrays
- [ ] Add the post-check callback invocation (non-blocking)
- [ ] Pass `pantry.onItemChecked` from use-shopping-list-page.ts to useShoppingListCrud
- [ ] Add ShoppingListPantryDialog component to [id].vue template
- [ ] Import ShoppingListPantryDialog in [id].vue
- [ ] Wire dialog events to pantry composable methods
- [ ] Run `task ui:lint`
- [ ] Verify: checking an item shows the dialog (if item has food_id and pantry data exists)
- [ ] Verify: unchecking an item does NOT trigger the dialog
- [ ] Verify: checking an item without food_id does NOT trigger the dialog
- [ ] Verify: "Check All" batches into a single dialog (debounce from task 4.1)
</subtasks>

<acceptance>
- Checking a shopping list item with a food_id triggers the pantry dialog (after 300ms debounce)
- Unchecking an item does NOT trigger the dialog
- Items without food_id never trigger the dialog
- "Check All" shows one dialog with all actionable items (not N dialogs)
- The check-off is never blocked — item is saved immediately, dialog appears asynchronously
- Clicking "Deduct" in the dialog calls the backend and shows success feedback
- Clicking "Add to pantry" in the dialog calls the backend and shows success feedback
- Clicking "Skip" dismisses without action
- The coverage banner refreshes after deduct or quick-add
- `task ui:lint` passes
- Existing check/uncheck/edit/delete flows are completely unchanged
</acceptance>

<rollback risk="high">
This task modifies `use-shopping-list-crud.ts` (upstream-adjacent composable). If the change breaks check-off:
1. Remove the `onItemChecked` callback addition from saveListItem
2. Remove the parameter from useShoppingListCrud
3. Remove the dialog from [id].vue

The core check-off flow (shoppingListItemActions.updateItem) is BEFORE the onItemChecked call, so even a crash in onItemChecked should not prevent items from being checked. But verify this.
</rollback>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes (existing tests still work)
- [ ] Shopping list page loads without errors
- [ ] Coverage banner appears for lists with recipe references
- [ ] Coverage banner is absent for lists without recipe references
- [ ] Checking an item with food_id shows the pantry dialog
- [ ] Unchecking an item does NOT show the dialog
- [ ] "Check All" shows one batched dialog
- [ ] Deduct action updates pantry quantities
- [ ] Quick-add action creates pantry items
- [ ] Skip dismisses the dialog
- [ ] Banner refreshes after pantry actions
- [ ] Existing shopping list CRUD (create, edit, delete, reorder) still works
</verification>
<success_criteria>Full C2+C3 frontend integration is functional. All pantry actions work end-to-end with the backend. No regressions in existing shopping list functionality.</success_criteria>
</checkpoint>

</phase>

---

## Phase 5: Final Validation

<phase id="5" name="Final Validation" depends="4">

### 5.1 End-to-End Smoke Test

<task id="5.1" status="pending" depends="4.4" risk="low">
<description>
Perform a full end-to-end test of all three sub-features (C1, C2, C3) together.

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
- Use "Check All" → verify single batched dialog appears
- Verify banner refreshes after deduct/quick-add
- Uncheck an item → verify NO dialog appears

**Regression checks**:
- Create/edit/delete shopping list items still works
- Reorder items still works
- Recipe reference add/remove still works
- Shopping list copy still works
</description>

<subtasks>
- [ ] Run `task py:lint` — passes
- [ ] Run `task ui:lint` — passes
- [ ] Run `task ui:test` — passes
- [ ] Start full dev environment
- [ ] Test C1: auto-section assignment
- [ ] Test C2: deficit coverage banner
- [ ] Test C3: deduct-on-checkout flow
- [ ] Test C3: quick-add-to-pantry flow
- [ ] Test C3: skip/dismiss flow
- [ ] Test C3: "Check All" batching
- [ ] Regression: CRUD operations unchanged
- [ ] Regression: recipe references unchanged
- [ ] Verify Swagger docs show all new endpoints correctly
</subtasks>

<acceptance>
- All C1/C2/C3 features work as described
- No JavaScript console errors on the shopping list page
- No Python backend errors in terminal output
- All lint and test commands pass
- Swagger docs show correct endpoint documentation
</acceptance>
</task>

### 5.2 Code Quality Review

<task id="5.2" status="pending" depends="5.1" risk="low">
<description>
Review all new and modified files for code quality, consistency, and fork isolation compliance.

**New files** (should all be in optimizer/ directories or Domain/ShoppingList/):
- `mealie/schema/optimizer/pantry.py` — modified (3 new schemas)
- `mealie/services/optimizer/pantry.py` — modified (2 new methods)
- `mealie/routes/optimizer/controller_pantry.py` — modified (2 new endpoints)
- `frontend/app/lib/api/types/optimizer.ts` — modified (3 new interfaces)
- `frontend/app/lib/api/user/optimizer-pantry.ts` — modified (2 new routes + methods)
- `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts` — new file
- `frontend/app/components/Domain/ShoppingList/ShoppingListPantryDialog.vue` — new file
- `frontend/app/lang/messages/en-US.json` — modified (10 new i18n keys)

**Modified upstream files** (keep changes minimal):
- `frontend/app/pages/shopping-lists/[id].vue` — banner + dialog + destructured vars
- `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` — pantry composable wiring
- `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts` — onItemChecked callback

**Review checklist**:
- No hardcoded strings (all user-facing text uses i18n)
- No console.log statements left in production code
- Error handling is graceful (try/catch with silent degradation, like the existing pantry auto-check pattern)
- Pantry actions never block the check-off flow
- TypeScript types match backend schemas
</description>

<subtasks>
- [ ] Review each new/modified file against acceptance criteria
- [ ] Verify fork isolation: all new code in optimizer/ directories (except ShoppingListPantryDialog which is in Domain/ShoppingList/)
- [ ] Verify upstream file changes are minimal and non-breaking
- [ ] Check for hardcoded strings, console.log, missing error handling
- [ ] Update CLAUDE.md "Modified Upstream Files" section if new upstream files were touched
</subtasks>

<acceptance>
- All new code follows existing patterns (MealieModel, BaseCrudController, sub-composable, i18n)
- Fork isolation maintained — CLAUDE.md reflects any new upstream file modifications
- No hardcoded strings, no debug logging, no missing error handling
- `task py:lint` and `task ui:lint` both pass
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] All features work end-to-end
- [ ] All lint and test suites pass
- [ ] Code review complete with no issues
- [ ] CLAUDE.md updated if needed
</verification>
<success_criteria>Stage C (Shopping List Enhancements) is complete and ready for use.</success_criteria>
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
- [ ] C3: Deduct-on-checkout works
- [ ] C3: Quick-add-to-pantry works
- [ ] C3: Check All batching works
- [ ] No regressions in shopping list CRUD
- [ ] No regressions in recipe reference management
</verification>
<acceptance>All three sub-features (C1 verify, C2 deficit banner, C3 deduct/quick-add) are functional. The shopping list page integrates with the pantry system without breaking any existing functionality. New backend endpoints are documented in Swagger. All code follows fork isolation rules.</acceptance>
</final_validation>

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
<dependency name="useUserApi composable" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Used throughout composables — provides access to api.optimizer.pantry methods</verified_via>
  <notes>Standard pattern for API access in Mealie composables.</notes>
</dependency>
<dependency name="PantryItemSave schema" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/schema/optimizer/pantry.py — PantryItemSave extends PantryItemCreate, adds group_id + household_id</verified_via>
  <notes>Used by quick_add_from_shopping to create pantry items with required group/household IDs.</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should the pantry dialog batch actions when "Check All" is used, or show one dialog per item?</question>
  <impact>UX: one dialog per item would be extremely annoying for 15+ items. Batch is clearly better but adds debounce complexity.</impact>
  <default_assumption>Batch: use 300ms debounce in onItemChecked to accumulate items, then show one dialog. This is implemented in task 4.1.</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should the deficit banner refresh after deduct/quick-add actions, or only on page load?</question>
  <impact>Stale banner data if user deducts items but banner still shows old coverage numbers.</impact>
  <default_assumption>Refresh after any pantry mutation. Implemented in task 4.1 — executeDeduct and executeQuickAdd both call fetchDeficit() on completion.</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-14-210000-shopping-list-enhancements.md">
  <question>Should quick-add pre-fill expiration_date or use_priority from any source?</question>
  <impact>Minor UX — users may expect some defaults. But no good source for this data exists on shopping list items.</impact>
  <default_assumption>No pre-fill. Create with defaults (no expiration, use_priority="auto", is_staple=False, assume_enough=False). User can edit later.</default_assumption>
</question>
<question id="Q4" blocking="false">
  <question>Should the pantry dialog show a success toast/snackbar after deduct or quick-add, using the i18n pluralized "Updated X pantry items" / "Added X items to pantry" keys?</question>
  <impact>UX feedback — without a toast, users may not know the action succeeded. The dialog closes but there's no confirmation.</impact>
  <default_assumption>Yes, show a toast using the existing Mealie snackbar/alert pattern. The i18n keys for this (deducted-count, added-count) are already defined in task 3.3.</default_assumption>
</question>
<question id="Q5" blocking="false">
  <question>How should the onItemChecked callback determine if a food "exists in pantry" for the PantryCheckoutAction.existsInPantry flag?</question>
  <impact>Determines whether the dialog shows "deduct" vs. "quick-add" for each item. If deficit data is stale or unavailable, items may be misclassified.</impact>
  <default_assumption>Use the deficitReport: if the food appears in deficitReport.items with covered=true OR has a non-null pantryQuantity, it exists in pantry. If deficitReport is null (never loaded or failed), treat all items as "not in pantry" (offer quick-add). This is conservative and safe.</default_assumption>
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
Codex review unavailable — "The 'gpt-5.2-codex' model is not supported when using Codex with a ChatGPT account." Architecture review based on thorough manual codebase analysis of all referenced files.
</codex_response>

<changes_made>
Independent architectural assessment conducted in lieu of Codex review:

1. **Cross-domain access (PantryService → shopping list items repo)**: Verified this is architecturally clean. AllRepositories is a single unit-of-work providing access to all household-scoped repositories. Other services already access multiple repos on the same instance (e.g., ShoppingListService accesses ingredient_foods, labels, and list_items). No domain boundary violation.

2. **Route ordering verified**: FastAPI processes routes in definition order within a router. The @controller(router) decorator registers methods in class-body order. Placing new POST endpoints before /{item_id} routes is correct and follows the existing pattern (4 existing POST endpoints already precede /{item_id}).

3. **Debounce complexity acknowledged**: The 300ms debounce in onItemChecked is the highest-risk design decision. If it causes timing issues (e.g., dialog appears after user navigates away), the fallback is to remove debounce and show immediate per-item dialogs. Task 4.1 rollback section addresses this.

4. **saveListItem check-transition detection**: The plan captures previous checked state from `shoppingList.value.listItems` before the local array update. This is safe because the local update happens synchronously in the same function call — no race condition. The previous state lookup is O(n) but shopping lists rarely exceed 100 items.

5. **Upstream file impact assessed**: Three upstream-adjacent files are modified (use-shopping-list-crud.ts, use-shopping-list-page.ts, [id].vue). Changes are additive — no existing lines are modified, only new code inserted. Merge conflicts during upstream sync would be limited to import lines and return object spreads.
</changes_made>
