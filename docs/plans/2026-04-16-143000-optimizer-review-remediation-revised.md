# Implementation Plan: Optimizer Review Remediation (17 Findings)

Source: docs/plans/2026-04-16-120100-optimizer-review-remediation.md
Revised: 2026-04-16

<plan_metadata>
  <feature>Optimizer Review Remediation</feature>
  <source>docs/plans/2026-04-16-120100-optimizer-review-remediation.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>7</phases>
  <tasks>12</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Fix all 17 findings from the optimizer implementation review: 1 critical N+1 query, 4 high-severity issues (orphaned unit guard, recipe projection query cost, time parsing, silent exception swallowing), 7 medium issues (deficit aggregation, nav i18n, planner diff detection, typing, shopping item validation, overlap score clarity), and 5 low-severity items. Work spans backend pantry service, recipe projection, shopping list integration, frontend scoring engine, and planner composable.

## Changes from Original

<revision_summary>
<change type="structural">
  Split Task 2.1 into two tasks (2.1 and 2.2). Original 2.1 combined 4 unrelated changes (UnitConverter singleton, _deduct_items extraction, orphaned FK guard, N+1 fix) with different risk profiles. New 2.1 handles singleton + N+1 batch fetch (behavior-preserving performance fix). New 2.2 handles _deduct_items extraction + orphaned FK guard (behavior-changing refactor). Original 2.2 (deficit aggregation) becomes 2.3. Original 2.3 (check_shopping_items immutability) becomes 2.4.
</change>
<change type="dependency">
  Fixed Phase 2 dependency chain: all tasks are now strictly sequential (2.1→2.2→2.3→2.4) since they all modify the same file (pantry.py). Original plan had 2.2 and 2.3 with `depends=""` which would allow parallel execution and edit conflicts.
</change>
<change type="dependency">
  Fixed Phase 5 dependency chain: 5.1→5.2 was already correct, but 5.3 (overlap score comment) also touches scoring-engine.ts. Folded 5.3 into 5.1 since it's a 2-line comment addition — not worth a separate task for the same file.
</change>
<change type="dependency">
  Fixed Phase 6 dependency chain: 6.1→6.2 now explicit since both modify use-optimizer-planner.ts.
</change>
<change type="clarity">
  Task 4.1: Filled in the relationship model class names (RecipeIngredientModel, Category, Tag) that the original plan left as "you need to identify." Added exact import paths.
</change>
<change type="clarity">
  Task 6.2: Replaced vague "Read the actual implementation to determine..." with the actual hasUnsavedChanges code and exact fix. Added cross-slot movement edge case analysis.
</change>
<change type="removed">
  Removed Q1-Q3 from open questions section — all three were already resolved with default assumptions in the original plan's `<resolved_from_source>` section. Keeping them as "open" confused reviewers.
</change>
<change type="clarity">
  Added explicit test commands (`task py:lint`, `task ui:test`, specific file paths) to all acceptance criteria per Codex recommendation that criteria should be command-verifiable.
</change>
</revision_summary>

**Note**: This is the ONLY meta-section. All other feedback is integrated inline.

## Prerequisites

<prerequisites>
<prereq id="P1" type="library" verified="true">
  <description>pint UnitRegistry — used by UnitConverter for unit conversion. Must be safe for module-level singleton (read-only after init).</description>
  <verification>Verified: `mealie/services/parser_services/parser_utils/unit_utils.py` line 22 shows `self.ureg = UnitRegistry()`. UnitRegistry is read-only after construction in this codebase (only `.can_convert()` and `.convert()` called).</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>Pydantic v2 `model_copy()` method on BaseModel subclasses</description>
  <verification>Verified: ShoppingListItemCreate inherits from MealieModel → BaseModel. Pydantic v2 provides `.model_copy()` on all BaseModel subclasses.</verification>
</prereq>
<prereq id="P3" type="environment" verified="true">
  <description>SQLAlchemy `load_only()` for column restriction with relationship loading</description>
  <verification>Verified: SQLAlchemy 2.x supports `load_only()` combined with `selectinload()` — loads only specified columns on the main entity while still eager-loading relationships.</verification>
</prereq>
<prereq id="P4" type="data" verified="true">
  <description>i18n key `optimizer.pantry.title` exists</description>
  <verification>Verified: `frontend/app/lang/messages/en-US.json` line 1486 contains `"title": "Pantry"` under `optimizer.pantry`.</verification>
</prereq>
<prereq id="P5" type="library" verified="true">
  <description>`collections.abc.Sequence` for get_many type hint</description>
  <verification>Stdlib, always available. Already imported as `Iterable` from `collections.abc` in repository_generic.py line 4.</verification>
</prereq>
<prereq id="P6" type="data" verified="true">
  <description>Recipe model relationship target classes for load_only() optimization</description>
  <verification>Verified from `mealie/db/models/recipe/recipe.py` lines 98-138: `recipe_ingredient` → `RecipeIngredientModel` (from `mealie/db/models/recipe/ingredient.py`), `recipe_category` → `Category` (from `mealie/db/models/recipe/category.py`), `tags` → `Tag` (from `mealie/db/models/recipe/tag.py`).</verification>
</prereq>
</prerequisites>

## Phase 1: Base Repository — `get_many()` Batch Fetch

<phase id="1" name="Base Repository Enhancement">

### 1.1 Add `get_many()` to `RepositoryGeneric`

<task id="1.1" status="pending" depends="" risk="medium">
<context>
File: `mealie/repos/repository_generic.py`

Add a generic batch-fetch method to `RepositoryGeneric`. This method retrieves multiple records by primary key (or named column) using a single SQL `IN()` query with tenant scoping. Needed because `deduct_shopping_items()` currently calls `get_one()` in a loop (N+1 query — Finding #1, critical severity).

Note: `multi_query()` (line 122) does NOT support batch-by-ID lookups — it uses `filter_by()` for equality matching on key-value pairs, not `IN()` queries. A new method is required.

Insert after the existing `get_one()` method (ends at line 179), before `create()` (line 181).

The implementation follows the exact same query pattern as `get_one()`:
- Uses `self.primary_key` (not hardcoded `'id'`) for genericity
- Uses `_filter_builder()` for automatic group/household tenant scoping
- Uses `_query()` so schema `loader_options()` still apply
- Uses `eff_schema.model_validate()` for Pydantic validation

Contract: order is NOT guaranteed to match input order. Missing IDs silently return fewer results (no error). Empty input returns `[]` without a DB query.

Risk note: this modifies a base class inherited by ALL repositories. The method is purely additive (new method, no changes to existing methods) and follows the same query pattern as `get_one()`.
</context>

<subtasks>
- [ ] Add `Sequence` to the `collections.abc` import at line 4: change `from collections.abc import Iterable` to `from collections.abc import Iterable, Sequence`
- [ ] Add `get_many()` method to `RepositoryGeneric` class after `get_one()` (after line 179), using this implementation:

```python
def get_many(
    self,
    values: Sequence[str | int | UUID4],
    key: str | None = None,
    override_schema: type | None = None,
) -> list[Schema]:
    """Batch-fetch multiple records by primary key or named column.
    Uses SQL IN() with tenant scoping from _filter_builder().
    Returns empty list for empty input. Order is NOT guaranteed to match input.
    Missing IDs are silently excluded from results (no error)."""
    if not values:
        return []

    key = key or self.primary_key
    eff_schema = override_schema or self.schema
    col = getattr(self.model, key)
    q = self._query(override_schema=eff_schema).filter(col.in_(values)).filter_by(**self._filter_builder())
    results = self.session.execute(q).unique().scalars().all()
    return [eff_schema.model_validate(x) for x in results]
```
</subtasks>

<acceptance>
- `get_many([])` returns `[]` without executing a query
- `get_many([valid_id])` returns a list with one validated Schema instance
- `get_many([valid_id, missing_id])` returns only the found item (no error for missing)
- Tenant scoping is applied (group_id/household_id filtering via `_filter_builder`)
- `task py:lint` passes with no errors in `repository_generic.py`
</acceptance>

<rollback risk="medium">
Remove the `get_many()` method and revert the import change. No existing code depends on it yet.
</rollback>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `get_many()` method exists on `RepositoryGeneric` class
- [ ] `Sequence` is imported from `collections.abc`
- [ ] `task py:lint` passes
- [ ] Method signature matches spec (Sequence input, optional key, optional override_schema)
</verification>
<gate>New `get_many()` method compiles and passes linting. No existing code is modified — only additive.</gate>
</checkpoint>

</phase>

## Phase 2: Backend Pantry Service — Deduction & Deficit Fixes

All tasks in this phase modify `mealie/services/optimizer/pantry.py` and MUST execute sequentially: 2.1 → 2.2 → 2.3 → 2.4.

<phase id="2" name="Pantry Service Fixes" depends="1">

### 2.1 UnitConverter singleton + N+1 batch fetch fix

<task id="2.1" status="pending" depends="1.1" risk="medium">
<context>
File: `mealie/services/optimizer/pantry.py`

Two independent performance fixes that don't change behavior:

**Fix A — Module-level UnitConverter singleton** (Finding #14): Replace per-instance `self.converter = UnitConverter()` (line 26) with a module-level singleton. Currently each `PantryService` request creates a new `pint.UnitRegistry` which parses unit definition files. Safe because UnitRegistry is read-only after init.

- After the imports (~line 17), add: `_unit_converter = UnitConverter()`
- In `__init__` (line 26), change to: `self.converter = _unit_converter`

**Fix B — N+1 query in `deduct_shopping_items()`** (Finding #1, critical): Replace the `get_one()` loop (lines 400-401) with a single `get_many()` batch fetch.

Current code (line 400-401):
```python
for item_id in shopping_list_item_ids:
    item = self.repos.group_shopping_list_item.get_one(item_id)
```

Replace the loop structure with:
```python
items = self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)
for item in items:
    if not item.food_id:
        continue
    # ... rest of existing per-item logic unchanged ...
```

The rest of the `deduct_shopping_items()` method body (lines 404-458) stays the same — it just iterates over fetched items instead of fetching inside the loop. Remove the `if item is None: continue` guard (line 402-403) since `get_many()` only returns found items.
</context>

<subtasks>
- [ ] Add module-level `_unit_converter = UnitConverter()` after imports (~line 17)
- [ ] Change `__init__` line 26 from `self.converter = UnitConverter()` to `self.converter = _unit_converter`
- [ ] In `deduct_shopping_items()`: replace `for item_id in shopping_list_item_ids:` + `get_one(item_id)` loop (lines 400-403) with `items = self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)` + `for item in items:`
- [ ] Remove the `if item is None: continue` guard since `get_many()` only returns found items
- [ ] Adjust attribute access: the items from `get_many()` are Pydantic models (same as `get_one()` returns), so `item.food_id`, `item.quantity`, `item.unit_id`, `item.unit` all work identically
</subtasks>

<acceptance>
- `deduct_shopping_items()` makes exactly ONE database query for shopping list items (via `get_many`), not N
- Behavior is identical: same items are deducted, same quantities, same unit conversion logic
- `UnitConverter()` is instantiated exactly once at module level
- `task py:lint` passes
</acceptance>
</task>

### 2.2 Extract `_deduct_items()` shared helper + orphaned unit FK guard

<task id="2.2" status="pending" depends="2.1" risk="high">
<context>
File: `mealie/services/optimizer/pantry.py`

**After Task 2.1 has been applied**, `deduct_recipe()` (lines 302-381) and `deduct_shopping_items()` (lines 383-458) share ~80% of their logic (running_qty tracking, unit conversion, persist-at-end pattern). Extract a shared `_deduct_items()` private method.

**Step 1: Create `_deduct_items()` private method.** Each caller normalizes its input into a list of 4-tuples: `(food_id, quantity, unit_object_or_None, original_unit_id)`. The helper contains the running_qty tracking, unit conversion logic, and persist-at-end pattern.

The `original_unit_id` field enables the orphaned unit FK guard (Finding #2): when both the source `unit_id` and pantry `unit_id` resolve to `None`, check if the *original* `unit_id` was non-None. If so, the unit FK failed to load (orphaned FK) — skip deduction rather than treating as "both unitless = compatible."

Implementation for `_deduct_items()`:
```python
def _deduct_items(
    self,
    food_qty_units: list[tuple[UUID4, float, object | None, UUID4 | None]],
    pantry_map: dict[UUID4, PantryItemOut],
) -> list[PantryItemOut]:
    """Shared deduction logic.
    Each tuple: (food_id, quantity, resolved_unit_object, original_unit_id_from_record).
    """
    running_qty: dict[UUID4, float] = {
        fid: p.quantity for fid, p in pantry_map.items() if p.quantity is not None
    }
    modified_ids: set[UUID4] = set()

    for food_id, qty, unit_obj, original_unit_id in food_qty_units:
        pantry_item = pantry_map.get(food_id)
        if pantry_item is None or pantry_item.assume_enough or pantry_item.quantity is None:
            continue
        if not qty:
            continue

        source_unit_id = unit_obj.id if unit_obj and hasattr(unit_obj, "id") else None
        pantry_unit_id = pantry_item.unit.id if pantry_item.unit else None

        # Orphaned unit FK guard (Finding #2)
        if source_unit_id is None and pantry_unit_id is None:
            if original_unit_id is not None:
                continue  # Orphaned FK — skip
            converted_qty = qty  # Both genuinely unitless
        elif source_unit_id == pantry_unit_id:
            converted_qty = qty  # Same unit
        else:
            source_standard = unit_obj.standard_unit if unit_obj and hasattr(unit_obj, "standard_unit") else None
            pantry_standard = pantry_item.unit.standard_unit if pantry_item.unit else None
            if source_standard and pantry_standard:
                converted_qty, ok = self._try_convert_quantity(qty, source_standard, pantry_standard)
                if not ok:
                    continue
            else:
                continue

        current_qty = running_qty.get(food_id, 0)
        new_quantity = max(0.0, round(current_qty - converted_qty, 4))
        if new_quantity == current_qty:
            continue
        running_qty[food_id] = new_quantity
        modified_ids.add(food_id)

    updated_items: list[PantryItemOut] = []
    for food_id in modified_ids:
        pantry_item = pantry_map[food_id]
        updated = self.pantry_items.update(pantry_item.id, {"quantity": running_qty[food_id]})
        updated_items.append(updated)
    return updated_items
```

**Step 2: Refactor `deduct_recipe()` to be a thin wrapper.**
Extract tuples from recipe ingredients:
```python
def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
    pantry_map = self.get_pantry_map()
    if not pantry_map:
        return []

    food_qty_units = []
    for ing in recipe_ingredients:
        if not ing.food or not ing.food.id:
            continue
        unit_obj = ing.unit if hasattr(ing.unit, "id") else None
        original_unit_id = unit_obj.id if unit_obj else None
        food_qty_units.append((ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))

    return self._deduct_items(food_qty_units, pantry_map)
```

**Step 3: Refactor `deduct_shopping_items()` to be a thin wrapper.**
After Task 2.1, this method already uses `get_many()`. Now extract tuples from shopping items:
```python
def deduct_shopping_items(self, shopping_list_item_ids: list[UUID4]) -> list[PantryItemOut]:
    if not shopping_list_item_ids:
        return []
    pantry_map = self.get_pantry_map()
    if not pantry_map:
        return []

    items = self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)
    food_qty_units = []
    for item in items:
        if not item.food_id:
            continue
        unit_obj = item.unit if item.unit and hasattr(item.unit, "id") else None
        original_unit_id = item.unit_id  # FK column — may be non-None even if unit relationship didn't load
        food_qty_units.append((item.food_id, item.quantity or 0, unit_obj, original_unit_id))

    return self._deduct_items(food_qty_units, pantry_map)
```

Key detail for shopping items: `item.unit_id` is the raw FK column (always available), while `item.unit` is the relationship object (may be None if FK is orphaned). This is how the orphaned FK guard works — `original_unit_id = item.unit_id` can be non-None even when `unit_obj` resolves to None.

For recipe ingredients: `original_unit_id = unit_obj.id if unit_obj else None` — since recipe ingredients already have the unit relationship eagerly loaded, orphaned FKs are less likely but the guard still applies consistently.
</context>

<subtasks>
- [ ] Add `_deduct_items()` private method to PantryService class (before `deduct_recipe()`)
- [ ] Refactor `deduct_recipe()` to normalize ingredients into tuples and delegate to `_deduct_items()`
- [ ] Refactor `deduct_shopping_items()` to normalize items into tuples and delegate to `_deduct_items()`
- [ ] Verify orphaned unit FK guard: both unit_ids None + original_unit_id set → skip
- [ ] Verify both genuinely unitless (both None, original None) → direct comparison (existing behavior)
- [ ] Verify `deduct_recipe()` produces identical results to the old implementation for all unit combinations
</subtasks>

<acceptance>
- `_deduct_items()` exists as private method on PantryService
- `deduct_recipe()` and `deduct_shopping_items()` are thin wrappers that delegate to `_deduct_items()`
- Orphaned unit FK case (both resolved None, original unit_id was set) results in skipped deduction
- Both genuinely unitless items (both None, original None) still deduct correctly
- `task py:lint` passes
</acceptance>

<rollback risk="high">
Revert `pantry.py` to the state after Task 2.1. The old deduct_recipe and deduct_shopping_items (with N+1 already fixed) are self-contained and independently correct.
</rollback>
</task>

### 2.3 Fix `calculate_deficit()` duplicate food_id aggregation

<task id="2.3" status="pending" depends="2.2" risk="medium">
<context>
File: `mealie/services/optimizer/pantry.py`

Fix `calculate_deficit()` (starts at line 65 in the original, but line numbers may have shifted after Tasks 2.1-2.2 — find the method by name) to track running pantry quantity across duplicate food_ids in recipe ingredients (Finding #6).

**Current bug**: If a recipe has two ingredients with the same `food_id` (e.g., flour in both "dough" and "sauce" sections), each ingredient compares against the *original* pantry quantity independently. The second flour ingredient doesn't see the quantity already "claimed" by the first.

**Example**: Pantry has 500g flour. Recipe needs 300g (dough) + 250g (sauce) = 550g total. Current code: both show deficit=0 (300 < 500, 250 < 500). Correct: first claims 300g leaving 200g, second needs 250g but only 200g available → 50g deficit.

**Fix**: After building `pantry_map` (the `{food_id: item}` dict), add:
```python
running_pantry_qty: dict[UUID4, float] = {
    fid: item.quantity for fid, item in pantry_map.items() if item.quantity is not None
}
```

Then in Rule 6 (compatible units) and Rule 7 same-unit-id branch, replace `pantry_item.quantity` with `running_pantry_qty.get(food_id, pantry_item.quantity)` for deficit calculation, and after calculating, deduct the consumed amount:
```python
# In Rule 6 (after deficit calculation):
effective_pantry_qty = running_pantry_qty.get(food_id, pantry_item.quantity)
deficit = round(max(0, converted_recipe_qty - effective_pantry_qty), 4)
consumed = min(converted_recipe_qty, effective_pantry_qty)
running_pantry_qty[food_id] = max(0, effective_pantry_qty - consumed)

# In Rule 7 same-unit-id branch (after deficit calculation):
effective_pantry_qty = running_pantry_qty.get(food_id, pantry_item.quantity)
deficit = round(max(0, recipe_qty - effective_pantry_qty), 4)
consumed = min(recipe_qty, effective_pantry_qty)
running_pantry_qty[food_id] = max(0, effective_pantry_qty - consumed)
```

Rules 1-5 (no food, no qty, no match, assume_enough, untracked) don't consume pantry stock and need no changes.
</context>

<subtasks>
- [ ] Add `running_pantry_qty` dict initialization after `pantry_map` construction
- [ ] In Rule 6 (compatible units): use `running_pantry_qty` for deficit calc, then update it
- [ ] In Rule 7 same-unit-id branch: use `running_pantry_qty` for deficit calc, then update it
- [ ] Verify: two ingredients with same food_id → second sees reduced pantry quantity
- [ ] Verify: single-ingredient recipes produce identical results to before
</subtasks>

<acceptance>
- Two flour ingredients (300g + 250g) against 500g pantry: first shows deficit=0, second shows deficit=50
- Single-ingredient recipes produce identical deficit calculations as before
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
Remove the `running_pantry_qty` dict and revert to using `pantry_item.quantity` directly. The old behavior is functional, just inaccurate for duplicate food_id edge cases.
</rollback>
</task>

### 2.4 Make `check_shopping_items()` immutable

<task id="2.4" status="pending" depends="2.3" risk="low">
<context>
File: `mealie/services/optimizer/pantry.py`

Fix `check_shopping_items()` (find by method name — originally at line 523, may have shifted) to stop mutating input items in-place (Finding #12).

**Current behavior**: The method iterates over the input `items` list and directly modifies `item.checked`, `item.note`, `item.quantity` on the original Pydantic model objects.

**Caller**: `shopping_lists.py` line 182: `create_items = PantryService(self.repos).check_shopping_items(create_items)` — rebinds the variable, so it works correctly with either mutation or new-list approach.

**Fix**: Create a copy of each item at the start of the loop body, collect all items into a result list.

```python
def check_shopping_items(self, items: list[ShoppingListItemCreate]) -> list[ShoppingListItemCreate]:
    pantry_map = self.get_pantry_map()
    if not pantry_map:
        return items  # No pantry data — return original (no copies needed, no modifications made)

    result: list[ShoppingListItemCreate] = []
    for item in items:
        item = item.model_copy()  # Work on copy — never mutate input
        # ... ALL existing logic unchanged (item.checked = True, item.note = ..., etc.) ...
        result.append(item)
    return result
```

**Important details**:
- `result.append(item)` MUST be at the end of EVERY loop iteration (after all if/elif/else/continue branches). The current code has `continue` statements in several branches (lines 549, 565, 578, 601). Each `continue` must be preceded by `result.append(item)`, OR restructure to avoid `continue` and have a single `result.append(item)` at the end.
- Simpler approach: replace every `continue` in the item loop with `result.append(item); continue`, and replace the final `return items` with `result.append(item)` inside the loop + `return result` after the loop.
- The early return for `not item.food_id` (line 539-540) and `pantry_item is None` (line 543-544) also need `result.append(item); continue`.
- Preserve list order. Every item must appear in the result list, whether modified or not.
</context>

<subtasks>
- [ ] Add `result: list[ShoppingListItemCreate] = []` after the pantry_map check
- [ ] Add `item = item.model_copy()` at the start of the for-loop body
- [ ] Ensure every code path through the loop body ends with `result.append(item)` before any `continue` or fall-through
- [ ] Change final `return items` (after the for-loop) to `return result`
- [ ] Verify the early return (no pantry_map) still returns the original list (acceptable — no modifications made in this path)
</subtasks>

<acceptance>
- Input list items are not modified (original objects unchanged after call)
- Returned list has same length and order as input
- All pantry-based modifications (checked, note, quantity) appear on returned copies
- `task py:lint` passes
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] Module-level `_unit_converter` singleton exists
- [ ] `deduct_shopping_items()` uses `get_many()` (no `get_one()` loop)
- [ ] `_deduct_items()` exists as private method on PantryService
- [ ] `deduct_recipe()` and `deduct_shopping_items()` delegate to `_deduct_items()`
- [ ] `calculate_deficit()` handles duplicate food_ids correctly
- [ ] `check_shopping_items()` does not mutate input
- [ ] `task py:lint` passes on `mealie/services/optimizer/pantry.py`
</verification>
<gate>All pantry service findings (#1, #2, #6, #11, #12, #14) are resolved. Backend linting passes.</gate>
</checkpoint>

</phase>

## Phase 3: Shopping List Exception Handling

<phase id="3" name="Shopping List Logging" depends="">

### 3.1 Log pantry integration errors in `shopping_lists.py`

<task id="3.1" status="pending" depends="" risk="low">
<context>
File: `mealie/services/household_services/shopping_lists.py`

Replace the bare `except: pass` (lines 183-184) with proper exception logging (Finding #5).

**Current code** (lines 179-184):
```python
try:
    from mealie.services.optimizer.pantry import PantryService
    create_items = PantryService(self.repos).check_shopping_items(create_items)
except Exception:
    pass  # Pantry integration is non-critical; degrade gracefully
```

**First**: Check if the file already has a logger. Search for `logger` or `get_logger` at the top of the file.

- If a logger exists: reuse it.
- If no logger exists: add at module level: `from mealie.core.root_logger import get_logger` and `logger = get_logger(__name__)`. This follows the standard Mealie pattern (see `repository_generic.py` line 17 for the same pattern).

**Then**: Replace `pass` with `logger.warning("Pantry check_shopping_items failed", exc_info=True)`.

Behavior: Shopping list creation still succeeds when pantry integration fails. The only change is failures are now logged with full traceback.
</context>

<subtasks>
- [ ] Check if `shopping_lists.py` already imports/creates a logger — if so, reuse it
- [ ] If no logger: add `from mealie.core.root_logger import get_logger` and `logger = get_logger(__name__)` at module level
- [ ] Replace `pass` on line 184 with `logger.warning("Pantry check_shopping_items failed", exc_info=True)`
- [ ] Verify the `except Exception:` clause (not bare `except:`) is already in place
</subtasks>

<acceptance>
- Pantry integration failures produce a WARNING-level log with full traceback
- Shopping list creation still succeeds when pantry fails (no re-raise)
- No behavior change for happy path
- `task py:lint` passes
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] Logger exists at module level in `shopping_lists.py`
- [ ] `except` block logs with `exc_info=True`
- [ ] `task py:lint` passes
</verification>
<gate>Finding #5 resolved. Silent exception swallowing replaced with logged warning.</gate>
</checkpoint>

</phase>

## Phase 4: Recipe Projection Query Optimization

<phase id="4" name="Recipe Projection Optimization" depends="">

### 4.1 Use `load_only()` to restrict columns on `RecipeModel` query

<task id="4.1" status="pending" depends="" risk="medium">
<context>
File: `mealie/services/optimizer/recipe_projection.py`

Optimize the recipe projection query (lines 29-38) to load only needed columns instead of the full `RecipeModel` (Finding #3). Currently loads ALL RecipeModel columns (description, recipe_instructions JSON, nutrition JSON, etc.) when only `id`, `slug`, `name`, `rating`, and `total_time` are used.

**Correct approach**: Use SQLAlchemy's `load_only()` combined with `selectinload()`, NOT a raw column `select()`. Raw column selects break relationship loading because `selectinload()` requires the parent to be a full ORM model.

**Relationship model classes** (verified from `mealie/db/models/recipe/recipe.py` lines 98-138):
- `RecipeModel.recipe_ingredient` → `RecipeIngredientModel` from `mealie/db/models/recipe/ingredient.py` — only `food_id` is used (line 44: `ing.food_id`)
- `RecipeModel.recipe_category` → `Category` from `mealie/db/models/recipe/category.py` — only `id` is used (line 58: `cat.id`)
- `RecipeModel.tags` → `Tag` from `mealie/db/models/recipe/tag.py` — only `id` is used (line 59: `tag.id`)

**New imports to add**:
```python
from sqlalchemy.orm import Session, load_only, selectinload  # add load_only to existing import
from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.db.models.recipe.category import Category
from mealie.db.models.recipe.tag import Tag
```

**New query** (replace lines 29-37):
```python
stmt = (
    select(RecipeModel)
    .where(RecipeModel.group_id == self.group_id)
    .options(
        load_only(
            RecipeModel.id,
            RecipeModel.slug,
            RecipeModel.name,
            RecipeModel.rating,
            RecipeModel.total_time,
        ),
        selectinload(RecipeModel.recipe_ingredient).load_only(RecipeIngredientModel.food_id),
        selectinload(RecipeModel.recipe_category).load_only(Category.id),
        selectinload(RecipeModel.tags).load_only(Tag.id),
    )
)
```
</context>

<subtasks>
- [ ] Add `load_only` to the existing `from sqlalchemy.orm import Session, selectinload` line
- [ ] Add imports for `RecipeIngredientModel`, `Category`, `Tag`
- [ ] Replace the `stmt` query with the `load_only()` version
- [ ] Verify the response payload is identical to the current implementation (same `RecipeFoodProjection` objects)
- [ ] `task py:lint` passes
</subtasks>

<acceptance>
- Query uses `load_only()` on both the main entity and relationship loads
- `RecipeFoodProjectionResponse` output is identical to current implementation
- No extra columns (description, instructions, nutrition) are loaded from the database
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
Revert to `select(RecipeModel)` without `load_only()`. The query still works, just loads more data.
</rollback>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `load_only()` is applied to main RecipeModel select
- [ ] `load_only()` is applied to each selectinload relationship
- [ ] `task py:lint` passes
- [ ] Service still builds correct `RecipeFoodProjectionResponse` output
</verification>
<gate>Finding #3 resolved. Recipe projection query loads only required columns.</gate>
</checkpoint>

</phase>

## Phase 5: Frontend Scoring Engine — Time Parsing & Comments

All tasks in this phase touch `scoring-engine.ts` or `scoring-engine.test.ts` and MUST execute sequentially: 5.1 → 5.2.

<phase id="5" name="Scoring Engine Enhancements" depends="">

### 5.1 Expand `parseTimeToMinutes()` + add overlap score comment

<task id="5.1" status="pending" depends="" risk="low">
<context>
File: `frontend/app/composables/optimizer/scoring-engine.ts`

**Part A — Time parsing** (Finding #4): Expand `parseTimeToMinutes()` (lines 10-29) to handle ISO 8601, colon format, and variant text formats. Current implementation only handles the `"X hour Y min"` text format.

Replace the function body (lines 10-29) with:
```typescript
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
```

Note: existing text regex `(\d+)\s*min` already matches "minutes" since "min" is a prefix. The explicit `min(?:ute)?s?` is slightly more correct but not functionally different for current inputs.

**Part B — Overlap score comment** (Finding #17): Add a clarifying comment above the `overlapScore` function (line 73):
```typescript
// Higher score = more ingredient reuse with already-planned recipes (reduces shopping variety).
// This is intentionally ADDED to the total score — ingredient reuse is rewarded.
export function overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number {
```

Part B is comment-only — no behavioral change.
</context>

<subtasks>
- [ ] Replace `parseTimeToMinutes()` function body (lines 10-29) with the new implementation
- [ ] Add two-line comment above `overlapScore` function (line 73)
- [ ] Verify all 6 existing parseTimeToMinutes tests still pass: `task ui:test`
- [ ] `task ui:lint` passes
</subtasks>

<acceptance>
- `parseTimeToMinutes("PT1H30M")` → 90
- `parseTimeToMinutes("PT45M")` → 45
- `parseTimeToMinutes("PT2H")` → 120
- `parseTimeToMinutes("1:30")` → 90
- `parseTimeToMinutes("0:45")` → 45
- `parseTimeToMinutes("90 minutes")` → 90
- `parseTimeToMinutes("1.5 hours")` → 90 (existing test preserved)
- `parseTimeToMinutes("1 Hour 15 Minutes")` → 75 (existing test preserved)
- `parseTimeToMinutes(null)` → null
- `parseTimeToMinutes("garbage")` → null
- Comment exists above `overlapScore` function
- All existing scoring-engine tests pass: `task ui:test`
- `task ui:lint` passes
</acceptance>
</task>

### 5.2 Add test cases for new time formats

<task id="5.2" status="pending" depends="5.1" risk="low">
<context>
File: `frontend/app/composables/optimizer/scoring-engine.test.ts`

Add new test cases to the `parseTimeToMinutes` describe block (after line 85, the last existing test, and before the `// ── normalizedRating ──` section at line 88).

```typescript
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
```
</context>

<subtasks>
- [ ] Add 6 new test cases to the parseTimeToMinutes describe block (after line 85, before line 88)
- [ ] Run `task ui:test` and verify all tests pass (6 existing + 6 new = 12 parseTimeToMinutes tests)
</subtasks>

<acceptance>
- All 12 parseTimeToMinutes tests pass (6 existing + 6 new)
- All other scoring-engine tests still pass
- `task ui:test` exits with code 0
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] `parseTimeToMinutes()` handles ISO 8601, colon, and text formats
- [ ] All 12+ parseTimeToMinutes tests pass
- [ ] All scoring-engine tests pass: `task ui:test`
- [ ] Overlap score comment is present
- [ ] `task ui:lint` passes
</verification>
<gate>Findings #4 and #17 resolved. Time parser handles all common formats. All tests pass.</gate>
</checkpoint>

</phase>

## Phase 6: Frontend Planner Composable Fixes

Both tasks in this phase modify `use-optimizer-planner.ts` and MUST execute sequentially: 6.1 → 6.2.

<phase id="6" name="Planner Composable Fixes" depends="">

### 6.1 Fix `mapPantryToScoring()` typing

<task id="6.1" status="pending" depends="" risk="low">
<context>
File: `frontend/app/composables/optimizer/use-optimizer-planner.ts`

Replace `any` type annotations in `mapPantryToScoring()` (lines 133-143) with proper types (Finding #15).

**Current code**:
```typescript
function mapPantryToScoring(items: any[]): PantryItemScoring[] {
  return items
    .filter((item: any) => item.foodId)
    .map((item: any) => ({ ... }));
}
```

**Fix**: Import `PantryItemOut` from the API types and use it. Check existing imports at top of file first — `PantryItemScoring` is already imported from `./types` (line 2).

Add to imports:
```typescript
import type { PantryItemOut } from "~/lib/api/types/optimizer";
```

Replace function:
```typescript
function mapPantryToScoring(items: PantryItemOut[]): PantryItemScoring[] {
  return items
    .filter((item) => item.foodId)
    .map((item) => ({
      foodId: item.foodId!,
      foodName: item.food?.name ?? item.name ?? "",
      labelName: item.food?.label?.name ?? null,
      usePriority: item.usePriority ?? "auto",
      assumeEnough: item.assumeEnough ?? false,
      expirationDate: item.expirationDate ?? null,
    }));
}
```

Verify `PantryItemOut` type in `frontend/app/lib/api/types/optimizer.ts` has all accessed fields: `foodId`, `food` (with `name` and `label.name`), `name`, `usePriority`, `assumeEnough`, `expirationDate`.
</context>

<subtasks>
- [ ] Check existing imports for `PantryItemOut` — add import if not present
- [ ] Replace `items: any[]` with `items: PantryItemOut[]`
- [ ] Remove `(item: any)` annotations from filter/map callbacks (TypeScript infers from array type)
- [ ] Verify all accessed properties exist on `PantryItemOut` type
- [ ] `task ui:lint` passes
</subtasks>

<acceptance>
- No `any` type annotations remain in `mapPantryToScoring()`
- Function parameter is typed as `PantryItemOut[]`
- `task ui:lint` passes (no TypeScript errors)
</acceptance>
</task>

### 6.2 Fix `savePlan()` diff detection and `hasUnsavedChanges`

<task id="6.2" status="pending" depends="6.1" risk="medium">
<context>
File: `frontend/app/composables/optimizer/use-optimizer-planner.ts`

Fix diff detection in both `savePlan()` and `hasUnsavedChanges` (Finding #10).

**Fix A — `savePlan()` diff detection** (line 393):

Current:
```typescript
const snapEntry = snapArr.find(s => s.existingEntryId === draftEntry.existingEntryId);
if (snapEntry && snapEntry.recipeId !== draftEntry.recipeId) {
```

Replace with:
```typescript
const snapEntry = snapArr.find(s => s.existingEntryId === draftEntry.existingEntryId);
if (snapEntry && (
  snapEntry.recipeId !== draftEntry.recipeId ||
  snapEntry.entryType !== draftEntry.entryType ||
  snapEntry.date !== draftEntry.date
)) {
```

Note: the `snapEntry &&` guard handles the case where an entry moves between slot keys (e.g., from "2026-04-16|dinner" to "2026-04-16|lunch"). When an entry moves slots, `snapEntry` is null for the new slot (entry not found in that slot's snapshot). The entry gets deleted from the old slot (via `toDelete` at lines 370-376) and re-created in the new slot because it would need `existingEntryId === null` to go through the create path. If the current UI preserves `existingEntryId` when moving between slots, this would be a data loss bug — but that's a separate issue from diff detection. For now, this fix covers the in-slot field change case.

**Fix B — `hasUnsavedChanges` computed property** (lines 113-129):

Current (lines 123-125):
```typescript
for (let i = 0; i < draftArr.length; i++) {
  if (draftArr[i].recipeId !== snapArr[i].recipeId) return true;
  if (draftArr[i].existingEntryId !== snapArr[i].existingEntryId) return true;
}
```

Add after line 125 (before the closing `}`):
```typescript
  if (draftArr[i].entryType !== snapArr[i].entryType) return true;
  if (draftArr[i].date !== snapArr[i].date) return true;
```

Note: entries are keyed by `${date}|${entryType}` so changing entryType or date usually re-keys the entry, which the `length` check (line 122) catches. But edge cases exist (e.g., swapping two entries between slots simultaneously), and the field-level check is cheap insurance for correctness.
</context>

<subtasks>
- [ ] Fix `savePlan()` diff at line 393: add `entryType` and `date` comparisons
- [ ] Fix `hasUnsavedChanges` at lines 123-125: add `entryType` and `date` comparisons
- [ ] Verify: changing a meal's entryType on an existing entry triggers an update on save
- [ ] Verify: no regression in create/delete detection
- [ ] `task ui:lint` passes
</subtasks>

<acceptance>
- Changing entryType (e.g., breakfast→lunch) on an existing entry triggers an update in `savePlan()`
- Changing date on an existing entry triggers an update in `savePlan()`
- `hasUnsavedChanges` reflects true when entryType or date is changed
- Create and delete detection still works correctly
- `task ui:lint` passes
</acceptance>
</task>

### Phase 6 Checkpoint

<checkpoint phase="6">
<verification>
- [ ] `mapPantryToScoring()` has no `any` type annotations
- [ ] `savePlan()` compares recipeId, entryType, and date
- [ ] `hasUnsavedChanges` also checks entryType and date
- [ ] `task ui:lint` passes
</verification>
<gate>Findings #10 and #15 resolved. Planner diff detection is comprehensive and types are explicit.</gate>
</checkpoint>

</phase>

## Phase 7: Nav i18n

<phase id="7" name="Navigation Internationalization" depends="">

### 7.1 Replace hardcoded "Pantry" with i18n key

<task id="7.1" status="pending" depends="" risk="low">
<context>
File: `frontend/app/components/Layout/DefaultLayout.vue`

Replace the hardcoded `"Pantry"` string (line 251) with the existing i18n key (Finding #9).

Current (line 251):
```javascript
title: "Pantry",
```

Fix:
```javascript
title: i18n.t("optimizer.pantry.title"),
```

The `i18n` object is already used in this file — see line 257 where `i18n.t("optimizer.planner.title")` is used. The key `optimizer.pantry.title` with value `"Pantry"` exists in `frontend/app/lang/messages/en-US.json` (verified at line 1486).
</context>

<subtasks>
- [ ] Replace `"Pantry"` with `i18n.t("optimizer.pantry.title")` on line 251
- [ ] `task ui:lint` passes
</subtasks>

<acceptance>
- Nav link displays "Pantry" (unchanged visually — same text from i18n)
- Text is now translatable via the i18n system
- `task ui:lint` passes
</acceptance>
</task>

### Phase 7 Checkpoint

<checkpoint phase="7">
<verification>
- [ ] Hardcoded "Pantry" string replaced with i18n call
- [ ] `task ui:lint` passes
</verification>
<gate>Finding #9 resolved.</gate>
</checkpoint>

</phase>

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="high">
  <description>get_many() on RepositoryGeneric breaks existing repo behavior</description>
  <mitigation>Method is purely additive — no existing methods modified. Uses same query pattern as get_one(). Test with empty input, single item, and multi-item.</mitigation>
  <detection>task py:lint fails, or existing tests fail after adding the method</detection>
</risk>
<risk id="R2" likelihood="medium" impact="high">
  <description>_deduct_items() extraction changes deduction behavior</description>
  <mitigation>Compare output of new deduct_recipe() against manual trace of old implementation for: same unit, different convertible units, incompatible units, no unit, both unitless. The helper must produce identical results for all existing cases.</mitigation>
  <detection>Manual code review of tuple extraction in both wrappers. Run task py:lint.</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>load_only() on recipe projection breaks relationship loading</description>
  <mitigation>Use load_only() on the entity (NOT raw column select). Verify selectinload still works by checking that food_ids, category_ids, tag_ids are populated in the response.</mitigation>
  <detection>API endpoint returns empty food_ids/category_ids/tag_ids arrays when they should be populated</detection>
</risk>
<risk id="R4" likelihood="low" impact="low">
  <description>parseTimeToMinutes regex changes break existing text format handling</description>
  <mitigation>ISO and colon formats are tested first (priority order). Text format regexes are only slightly modified. All 6 existing tests must pass.</mitigation>
  <detection>task ui:test fails on existing parseTimeToMinutes tests</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] `task py:lint` passes (all Python changes)
- [ ] `task ui:lint` passes (all frontend changes)
- [ ] `task ui:test` passes (scoring-engine tests — existing + new)
- [ ] No regressions in existing scoring-engine test suite
- [ ] Code review: `deduct_shopping_items` uses `get_many()` batch query (not `get_one()` loop)
- [ ] Code review: `_deduct_items()` helper exists, both deduction methods delegate to it
- [ ] Code review: `calculate_deficit` uses `running_pantry_qty` for duplicate food_ids
- [ ] Code review: `check_shopping_items` returns new list via `model_copy()` without mutating input
- [ ] Code review: recipe projection uses `load_only()` on entity and relationships
- [ ] Code review: `shopping_lists.py` logs pantry errors with `exc_info=True`
- [ ] Code review: `DefaultLayout.vue` uses `i18n.t("optimizer.pantry.title")`
- [ ] Code review: `savePlan()` and `hasUnsavedChanges` compare entryType and date
- [ ] Code review: `mapPantryToScoring()` has no `any` annotations
</verification>
<acceptance>All 17 review findings addressed (13 fixed, 2 comment/doc only, 2 deferred as out-of-scope per spec). All linting and tests pass. No schema/migration changes required.</acceptance>
</final_validation>

## Findings Coverage Map

| Finding | Severity | Description | Task | Status |
|---------|----------|-------------|------|--------|
| #1 | Critical | N+1 query in deduct_shopping_items | 1.1 + 2.1 | Planned |
| #2 | High | Orphaned unit FK guard | 2.2 | Planned |
| #3 | High | Recipe projection full ORM load | 4.1 | Planned |
| #4 | High | Narrow time parsing | 5.1 + 5.2 | Planned |
| #5 | High | Bare except in shopping_lists | 3.1 | Planned |
| #6 | Medium | Deficit duplicate food_id | 2.3 | Planned |
| #7 | Medium | (covered by other tasks) | — | — |
| #8 | Medium | is_staple behavior | — | Out of scope |
| #9 | Medium | Nav i18n hardcoded | 7.1 | Planned |
| #10 | Medium | savePlan diff detection | 6.2 | Planned |
| #11 | Medium | Shopping item validation | 2.1 | Planned |
| #12 | Medium | In-place mutation | 2.4 | Planned |
| #13 | Medium | Overlap score direction | 5.1 | Planned |
| #14 | Low | UnitConverter per-request | 2.1 | Planned |
| #15 | Low | mapPantryToScoring typing | 6.1 | Planned |
| #16 | Low | excludeExpired UI toggle | — | Out of scope |
| #17 | Low | Overlap score comment | 5.1 | Planned |

## Dependency Verification Log

<dependency_log>
<dependency name="collections.abc.Sequence" verified="true">
  <version>Python 3.12 stdlib</version>
  <verified_via>Already imported in repository_generic.py line 4 (Iterable from same module)</verified_via>
</dependency>
<dependency name="pint.UnitRegistry" verified="true">
  <version>Used via mealie/services/parser_services/parser_utils/unit_utils.py</version>
  <verified_via>UnitRegistry instantiated in __init__, only .can_convert() and .convert() called (read-only after init)</verified_via>
</dependency>
<dependency name="sqlalchemy.orm.load_only" verified="true">
  <version>SQLAlchemy 2.x</version>
  <verified_via>Must use load_only() on entity, NOT raw column select. Raw column select breaks selectinload.</verified_via>
</dependency>
<dependency name="Pydantic BaseModel.model_copy()" verified="true">
  <version>Pydantic 2.x</version>
  <verified_via>MealieModel extends BaseModel. model_copy() is v2 replacement for .copy().</verified_via>
</dependency>
<dependency name="mealie.core.root_logger.get_logger" verified="true">
  <version>Internal utility</version>
  <verified_via>Already used in repository_generic.py line 17</verified_via>
</dependency>
<dependency name="i18n key optimizer.pantry.title" verified="true">
  <version>N/A</version>
  <verified_via>Key exists in en-US.json at line 1486 with value "Pantry"</verified_via>
</dependency>
<dependency name="RecipeIngredientModel" verified="true">
  <version>N/A</version>
  <verified_via>mealie/db/models/recipe/ingredient.py line 344, class RecipeIngredientModel with food_id at line 357</verified_via>
</dependency>
<dependency name="Category" verified="true">
  <version>N/A</version>
  <verified_via>mealie/db/models/recipe/category.py line 52, class Category with id (BaseMixins)</verified_via>
</dependency>
<dependency name="Tag" verified="true">
  <version>N/A</version>
  <verified_via>mealie/db/models/recipe/tag.py line 44, class Tag with id (BaseMixins)</verified_via>
</dependency>
</dependency_log>

## Open Questions

<open_questions>
None — all questions from the source spec have been resolved with their default assumptions.
</open_questions>

<resolved_from_source source="docs/specs/2026-04-16-023822-optimizer-review-remediation.md">
<resolved original_question="Should parseTimeToMinutes return 0 instead of null for unparseable times?">
  <resolution>Keep returning null — don't penalize recipes with missing time data. prepTimeScore returns 1.0 for null.</resolution>
</resolved>
<resolved original_question="Should recipe projection add pagination or is query optimization sufficient?">
  <resolution>Optimize query with load_only() first. Pagination deferred — planner needs all recipes for client-side scoring.</resolution>
</resolved>
<resolved original_question="Should deduct_shopping_items raise an error if some IDs were not found?">
  <resolution>Silently skip. HouseholdRepositoryGeneric already scopes queries, so cross-household IDs naturally return no results from get_many().</resolution>
</resolved>
</resolved_from_source>
