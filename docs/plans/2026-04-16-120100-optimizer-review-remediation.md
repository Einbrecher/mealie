# Implementation Plan: Optimizer Review Remediation (17 Findings)

Source: docs/specs/2026-04-16-023822-optimizer-review-remediation.md
Created: 2026-04-16

<plan_metadata>
  <feature>Optimizer Review Remediation</feature>
  <source_doc>docs/specs/2026-04-16-023822-optimizer-review-remediation.md</source_doc>
  <total_phases>7</total_phases>
  <total_tasks>14</total_tasks>
  <critical_path>1.1 → 2.1 → 2.2 (get_many → batch deduction → deficit fix)</critical_path>
  <status>draft</status>
</plan_metadata>

## Overview

Fix all 17 findings from the optimizer implementation review: 1 critical N+1 query, 4 high-severity issues (orphaned unit guard, recipe projection query cost, time parsing, silent exception swallowing), 7 medium issues (deficit aggregation, nav i18n, planner diff detection, typing, shopping item validation, overlap score clarity), and 5 low-severity items. Work spans backend pantry service, recipe projection, shopping list integration, frontend scoring engine, and planner composable.

## Dependencies & Prerequisites

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
</prerequisites>

## Phase 1: Base Repository — `get_many()` Batch Fetch

<phase id="1" name="Base Repository Enhancement">

### 1.1 Add `get_many()` to `RepositoryGeneric`

<task id="1.1" status="pending" depends="" risk="medium">
<description>
Add a generic batch-fetch method to `RepositoryGeneric` in `mealie/repos/repository_generic.py`. This method retrieves multiple records by primary key (or named column) using a single SQL `IN()` query with tenant scoping.

**Why this is needed**: `deduct_shopping_items()` currently calls `get_one()` in a loop (N+1 query pattern — Finding #1, critical severity). A batch method eliminates this.

**Where to add**: After the existing `get_one()` method (line 179), before `create()` (line 181).

**Implementation**:
```python
from collections.abc import Sequence  # Add to existing collections.abc import at line 4

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

**Contract details** (per Codex review):
- Uses `self.primary_key` (not hardcoded `'id'`) for true genericity
- Uses `_filter_builder()` for automatic group/household tenant scoping
- Uses `_query()` so schema `loader_options()` still apply
- Order is NOT guaranteed to match input order
- Missing IDs silently return fewer results (no error raised)
- Works for both `RepositoryGeneric` and `HouseholdRepositoryGeneric` subclasses (inherits scoping)

**Risk**: This modifies a base class inherited by ALL repositories in Mealie. The method is purely additive (new method, no changes to existing methods) and follows the exact same query pattern as `get_one()`. Risk is mitigated by the narrow contract.
</description>

<subtasks>
- [ ] Add `Sequence` to the `collections.abc` import at line 4 of `mealie/repos/repository_generic.py`
- [ ] Add `get_many()` method to `RepositoryGeneric` class after `get_one()` (after line 179)
- [ ] Verify method uses `self.primary_key`, `_filter_builder()`, `_query()`, and `eff_schema.model_validate()`
- [ ] Verify empty input returns `[]` without hitting the database
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
<success_criteria>New `get_many()` method compiles and passes linting. No existing code is modified — only additive.</success_criteria>
</checkpoint>

</phase>

## Phase 2: Backend Pantry Service — Deduction & Deficit Fixes

<phase id="2" name="Pantry Service Deduction Refactor" depends="1">

### 2.1 Extract `_deduct_items()` shared helper, fix N+1 query, add orphaned unit guard

<task id="2.1" status="pending" depends="1.1" risk="high">
<description>
Refactor `mealie/services/optimizer/pantry.py` to extract shared deduction logic and fix the critical N+1 query.

**Current state**: `deduct_recipe()` (lines 302-381) and `deduct_shopping_items()` (lines 383-458) share ~80% of their logic (running_qty tracking, unit conversion, persist-at-end pattern) but are implemented as separate copy-pasted methods. `deduct_shopping_items()` calls `get_one()` per item in a loop (N+1, Finding #1).

**Changes required**:

1. **Module-level UnitConverter singleton** (line 17 area): Replace per-instance `self.converter = UnitConverter()` with a module-level `_unit_converter = UnitConverter()` and `self.converter = _unit_converter` in `__init__`. This avoids creating a new `pint.UnitRegistry` per request. Safe because UnitRegistry is read-only after init in this codebase.

2. **Extract `_deduct_items()` private method**: Create a shared helper that accepts a list of normalized tuples `(food_id, quantity, unit_object_or_None, original_unit_id)` plus a `pantry_map`. It contains the running_qty tracking, unit conversion logic, and persist-at-end pattern. Both `deduct_recipe()` and `deduct_shopping_items()` become thin wrappers that normalize their inputs into these tuples and delegate.

3. **Orphaned unit FK guard** (Finding #2): In `_deduct_items()`, when both the source `unit_id` and pantry `unit_id` resolve to `None`, check if the *original* `unit_id` (from the ingredient/shopping item record) was non-None. If it was, that means the unit FK failed to load (orphaned FK) — skip deduction rather than treating it as "both unitless = compatible". The tuple format `(food_id, qty, unit_obj, original_unit_id)` carries this information.

4. **Fix N+1 in `deduct_shopping_items()`**: Replace the `for item_id in ids: get_one(item_id)` loop with a single `self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)` call. Missing/cross-household IDs are silently excluded by `get_many()` + `HouseholdRepositoryGeneric` scoping.

**Behavior preservation**: The extracted `_deduct_items()` must produce identical results to the current `deduct_recipe()` for all existing inputs. The only behavioral change is the orphaned unit guard (which currently would incorrectly treat orphaned-FK-None as "both unitless = compatible").

**Key implementation detail for `_deduct_items()`**:
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

        # Orphaned unit FK guard: if both resolved to None but original had a unit_id,
        # the unit failed to load — skip rather than falsely matching as "both unitless"
        if source_unit_id is None and pantry_unit_id is None:
            if original_unit_id is not None:
                continue  # Orphaned FK — skip
            # Both genuinely unitless — direct comparison
            converted_qty = qty
        elif source_unit_id == pantry_unit_id:
            converted_qty = qty
        else:
            # Try standard unit conversion
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

    # Persist all changes
    updated_items: list[PantryItemOut] = []
    for food_id in modified_ids:
        pantry_item = pantry_map[food_id]
        updated = self.pantry_items.update(pantry_item.id, {"quantity": running_qty[food_id]})
        updated_items.append(updated)
    return updated_items
```

**Thin wrappers**:
- `deduct_recipe()`: Extracts `(ingredient.food.id, ingredient.quantity, ingredient.unit, ingredient.unit.id)` tuples, calls `_deduct_items()`
- `deduct_shopping_items()`: Batch-fetches items via `get_many()`, extracts `(item.food_id, item.quantity, item.unit, item.unit_id)` tuples, calls `_deduct_items()`
</description>

<subtasks>
- [ ] Add module-level `_unit_converter = UnitConverter()` after imports (~line 17)
- [ ] Change `__init__` to use `self.converter = _unit_converter` instead of `self.converter = UnitConverter()`
- [ ] Implement `_deduct_items()` private method with running_qty, unit conversion, orphaned FK guard, persist-at-end
- [ ] Refactor `deduct_recipe()` to normalize ingredients into tuples and delegate to `_deduct_items()`
- [ ] Refactor `deduct_shopping_items()` to use `get_many()` batch fetch, normalize to tuples, delegate to `_deduct_items()`
- [ ] Verify orphaned unit FK guard: both unit_ids None + original_unit_id set → skip
- [ ] Verify both genuinely unitless (both None, original None) → direct comparison (existing behavior)
</subtasks>

<acceptance>
- `deduct_shopping_items()` makes exactly ONE database query for shopping list items (via `get_many`), not N
- `deduct_recipe()` produces identical results to the old implementation for all unit combinations
- Orphaned unit FK case (both resolved None, original unit_id was set) results in skipped deduction
- Both genuinely unitless items (both None, original None) still deduct correctly via direct comparison
- `UnitConverter()` is instantiated exactly once at module level
- `task py:lint` passes
</acceptance>

<rollback risk="high">
Revert the entire `pantry.py` file to its previous state. The old deduct_recipe and deduct_shopping_items are self-contained and independently correct (aside from the N+1). UnitConverter singleton revert is trivial.
</rollback>
</task>

### 2.2 Fix `calculate_deficit()` duplicate food_id aggregation

<task id="2.2" status="pending" depends="" risk="medium">
<description>
Fix `calculate_deficit()` in `mealie/services/optimizer/pantry.py` (lines 65-244) to track running pantry quantity across duplicate food_ids in recipe ingredients.

**Current bug** (Finding #6): If a recipe has two ingredients with the same `food_id` (e.g., flour in both "dough" and "sauce" sections), each ingredient compares against the *original* pantry quantity independently. The second flour ingredient doesn't see the quantity already "claimed" by the first.

**Example**: Pantry has 500g flour. Recipe needs 300g flour (dough) + 250g flour (sauce) = 550g total. Current code reports both as covered (300 < 500, 250 < 500). Correct: first claims 300g leaving 200g, second needs 250g but only 200g available → 50g deficit.

**Fix**: Add a `running_pantry_qty` dict at the top of the method, initialized from `pantry_map`. For each ingredient with a food_id match, use `running_pantry_qty[food_id]` instead of `pantry_item.quantity` for deficit calculation. After calculating, deduct the consumed amount from `running_pantry_qty[food_id]`.

**Key change locations**:
- Line 92: After building `pantry_map`, initialize `running_pantry_qty = {fid: item.quantity for fid, item in pantry_map.items() if item.quantity is not None}`
- Lines 170-193 (Rule 6 — compatible units): Replace `pantry_item.quantity` with `running_pantry_qty.get(food_id, pantry_item.quantity)` and update `running_pantry_qty[food_id]` after
- Lines 197-231 (Rule 7 — same unit_id fallback): Same running quantity pattern

**Note**: Rules 2-5 (no qty, no match, assume_enough, untracked) don't need running qty since they don't consume pantry stock.
</description>

<subtasks>
- [ ] Add `running_pantry_qty` dict initialization after `pantry_map` construction (~line 93)
- [ ] In Rule 6 (compatible units, ~line 179-193): use `running_pantry_qty` for deficit calculation, then update it
- [ ] In Rule 7 same-unit-id branch (~line 201-216): use `running_pantry_qty` for deficit calculation, then update it
- [ ] Verify: two ingredients with same food_id → second sees reduced pantry quantity
- [ ] Verify: single-ingredient recipes produce identical results to before
</subtasks>

<acceptance>
- Two flour ingredients (300g + 250g) against 500g pantry: first shows deficit=0, second shows deficit=50
- Single-ingredient recipes produce identical deficit calculations as before
- `task py:lint` passes
</acceptance>

<rollback risk="medium">
Remove the `running_pantry_qty` dict and revert to using `pantry_item.quantity` directly. The old behavior (no aggregation) is functional, just inaccurate for edge cases.
</rollback>
</task>

### 2.3 Make `check_shopping_items()` immutable

<task id="2.3" status="pending" depends="" risk="low">
<description>
Fix `check_shopping_items()` in `mealie/services/optimizer/pantry.py` (lines 523-605) to stop mutating input items in-place (Finding #12).

**Current behavior**: The method iterates over the input `items` list and directly modifies `item.checked`, `item.note`, `item.quantity` on the original objects.

**Caller**: `shopping_lists.py` line 182: `create_items = PantryService(self.repos).check_shopping_items(create_items)` — rebinds the variable, so it works correctly with either mutation or new-list approach.

**Fix**: At the start of the loop body (line 538), create a copy: `item = item.model_copy()`. Collect all items (modified and unmodified) into a new result list. Return the new list.

```python
def check_shopping_items(self, items: list[ShoppingListItemCreate]) -> list[ShoppingListItemCreate]:
    pantry_map = self.get_pantry_map()
    if not pantry_map:
        return items  # No pantry data — return original (no copies needed)

    result: list[ShoppingListItemCreate] = []
    for item in items:
        item = item.model_copy()  # Work on copy — never mutate input
        # ... rest of existing logic unchanged ...
        result.append(item)
    return result
```

**Important**: Preserve list order. Every item must appear in the result list, whether modified or not.
</description>

<subtasks>
- [ ] Add `result: list[ShoppingListItemCreate] = []` after the pantry_map check
- [ ] Add `item = item.model_copy()` at the start of the for-loop body
- [ ] Add `result.append(item)` at the end of each loop iteration (after all modification branches)
- [ ] Change `return items` at the end to `return result`
- [ ] Verify the early return (no pantry_map) still returns the original list (acceptable — no modifications made)
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
- [ ] `_deduct_items()` exists as private method on PantryService
- [ ] `deduct_recipe()` and `deduct_shopping_items()` delegate to `_deduct_items()`
- [ ] `deduct_shopping_items()` uses `get_many()` (no `get_one()` loop)
- [ ] `calculate_deficit()` handles duplicate food_ids correctly
- [ ] `check_shopping_items()` does not mutate input
- [ ] Module-level `_unit_converter` singleton exists
- [ ] `task py:lint` passes on `mealie/services/optimizer/pantry.py`
</verification>
<success_criteria>All pantry service findings (#1, #2, #6, #11, #12, #14) are resolved. Backend linting passes.</success_criteria>
</checkpoint>

</phase>

## Phase 3: Shopping List Exception Handling

<phase id="3" name="Shopping List Logging" depends="">

### 3.1 Log pantry integration errors in `shopping_lists.py`

<task id="3.1" status="pending" depends="" risk="low">
<description>
Replace the bare `except: pass` in `mealie/services/household_services/shopping_lists.py` (lines 183-184) with proper exception logging (Finding #5).

**Current code** (lines 179-184):
```python
try:
    from mealie.services.optimizer.pantry import PantryService
    create_items = PantryService(self.repos).check_shopping_items(create_items)
except Exception:
    pass  # Pantry integration is non-critical; degrade gracefully
```

**Changes needed**:
1. Add logger import at module level: `from mealie.core.root_logger import get_logger` and `logger = get_logger(__name__)`. Check if the file already has a logger — if so, reuse it.
2. Replace `pass` with `logger.warning("Pantry check_shopping_items failed", exc_info=True)`

**Behavior**: Shopping list creation still succeeds when pantry integration fails. The only change is that failures are now logged with full traceback instead of silently swallowed.
</description>

<subtasks>
- [ ] Check if `shopping_lists.py` already imports/creates a logger — if so, reuse it
- [ ] If no logger exists: add `from mealie.core.root_logger import get_logger` and `logger = get_logger(__name__)` at module level
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
<success_criteria>Finding #5 resolved. Silent exception swallowing replaced with logged warning.</success_criteria>
</checkpoint>

</phase>

## Phase 4: Recipe Projection Query Optimization

<phase id="4" name="Recipe Projection Optimization" depends="">

### 4.1 Use `load_only()` to restrict columns on `RecipeModel` query

<task id="4.1" status="pending" depends="" risk="medium">
<description>
Optimize the recipe projection query in `mealie/services/optimizer/recipe_projection.py` (lines 29-38) to load only needed columns instead of the full `RecipeModel` (Finding #3).

**Current query** loads the entire `RecipeModel` ORM object (all columns including `description`, `recipe_instructions` JSON, `nutrition` JSON, etc.) when only `id`, `slug`, `name`, `rating`, and `total_time` are used.

**Correct approach** (per Codex review): Use SQLAlchemy's `load_only()` combined with `selectinload()`, NOT a raw column `select()`. Raw column selects break relationship loading. The pattern is:

```python
from sqlalchemy.orm import load_only, selectinload

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
        selectinload(RecipeModel.recipe_ingredient).load_only(IngredientModel.food_id),
        selectinload(RecipeModel.recipe_category).load_only(CategoryModel.id),
        selectinload(RecipeModel.tags).load_only(TagModel.id),
    )
)
```

**Why `load_only()` and not column select**: `selectinload()` requires the parent entity to be a full ORM model (not a Row tuple). `load_only()` defers loading of unneeded columns while keeping the model intact.

**Additional optimization on relationships**: The current code only uses `ing.food_id` from ingredients, `cat.id` from categories, and `tag.id` from tags. Adding `load_only()` to the selectinload options avoids loading all relationship columns.

**Note**: You need to identify the correct model class names for the relationship targets. Check:
- `RecipeModel.recipe_ingredient` → what model class?
- `RecipeModel.recipe_category` → what model class?
- `RecipeModel.tags` → what model class?

Look at the relationship definitions in `mealie/db/models/recipe/recipe.py` to find the target model names, then import them.
</description>

<subtasks>
- [ ] Identify the ORM model classes for recipe_ingredient, recipe_category, and tags relationships
- [ ] Add `load_only` import from `sqlalchemy.orm` (alongside existing `selectinload`)
- [ ] Add `load_only(RecipeModel.id, .slug, .name, .rating, .total_time)` to the query
- [ ] Add `load_only()` to each `selectinload()` to restrict relationship columns to only IDs/food_ids
- [ ] Verify the response payload is identical to the current implementation
- [ ] Verify `task py:lint` passes
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
<success_criteria>Finding #3 resolved. Recipe projection query loads only required columns.</success_criteria>
</checkpoint>

</phase>

## Phase 5: Frontend Scoring Engine — Time Parsing & Comments

<phase id="5" name="Scoring Engine Enhancements" depends="">

### 5.1 Expand `parseTimeToMinutes()` to handle multiple formats

<task id="5.1" status="pending" depends="" risk="low">
<description>
Expand `parseTimeToMinutes()` in `frontend/app/composables/optimizer/scoring-engine.ts` (lines 10-29) to handle ISO 8601, colon format, and variant text formats (Finding #4).

**Current implementation** only handles the `"X hour Y min"` text format using two independent regexes.

**New implementation** — parse formats in priority order:

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

  // 3. Text format: "1 hour 30 min", "2 hours", "45 minutes", "1.5 hours", "90 minutes"
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

**Important**: The existing text-format regex `(\d+)\s*min` must be widened to also match "minutes" (currently only matches "min" prefix due to `\s*min`). Verify: existing test at line 63 `"30 Minutes"` — the current regex `(\d+)\s*min` matches "30 Min" prefix of "30 Minutes", so it already works. But `"90 minutes"` should also work — confirm with the regex.

Actually, re-checking: `/(\d+)\s*min/i` will match "minutes" because "min" is a substring prefix. So `"90 minutes"` already works. The main new capability is ISO 8601 and colon format.
</description>

<subtasks>
- [ ] Replace `parseTimeToMinutes()` function body (lines 10-29) with the new implementation
- [ ] Verify all existing tests still pass (6 existing tests for this function)
- [ ] Add new test cases (see task 5.2)
</subtasks>

<acceptance>
- `parseTimeToMinutes("PT1H30M")` returns `90`
- `parseTimeToMinutes("PT45M")` returns `45`
- `parseTimeToMinutes("PT2H")` returns `120`
- `parseTimeToMinutes("1:30")` returns `90`
- `parseTimeToMinutes("0:45")` returns `45`
- `parseTimeToMinutes("90 minutes")` returns `90`
- `parseTimeToMinutes("1.5 hours")` returns `90` (existing test)
- `parseTimeToMinutes("1 Hour 15 Minutes")` returns `75` (existing test preserved)
- `parseTimeToMinutes(null)` returns `null`
- `parseTimeToMinutes("garbage")` returns `null`
- All existing scoring-engine tests pass: `task ui:test`
</acceptance>
</task>

### 5.2 Add test cases for new time formats

<task id="5.2" status="pending" depends="5.1" risk="low">
<description>
Add new test cases to the `parseTimeToMinutes` describe block in `frontend/app/composables/optimizer/scoring-engine.test.ts` (after line 85).

**New tests to add** (after the existing "returns null for unparseable string" test):

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

**Location**: Insert after line 85 (the last existing parseTimeToMinutes test) and before the `// ── normalizedRating ──` section at line 88.
</description>

<subtasks>
- [ ] Add 6 new test cases to the parseTimeToMinutes describe block
- [ ] Run `task ui:test` and verify all tests pass (existing + new)
</subtasks>

<acceptance>
- All 12 parseTimeToMinutes tests pass (6 existing + 6 new)
- All other scoring-engine tests still pass
- `task ui:test` exits with code 0
</acceptance>
</task>

### 5.3 Add clarifying comment on overlap score direction

<task id="5.3" status="pending" depends="" risk="low">
<description>
Add a clarifying comment to the `overlapScore` function in `frontend/app/composables/optimizer/scoring-engine.ts` (line 73) explaining that higher overlap = ingredient reuse = good (Finding #17).

**Current code** (line 73):
```typescript
export function overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number {
```

**Add comment above**:
```typescript
// Higher score = more ingredient reuse with already-planned recipes (reduces shopping variety).
// This is intentionally ADDED to the total score — ingredient reuse is rewarded.
export function overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number {
```

This is comment-only — no behavioral change.
</description>

<subtasks>
- [ ] Add two-line comment above `overlapScore` function at line 73
- [ ] Verify no behavior change — comment only
</subtasks>

<acceptance>
- Comment exists above `overlapScore` function
- No code changes — tests unaffected
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
<success_criteria>Findings #4 and #17 resolved. Time parser handles all common formats. All tests pass.</success_criteria>
</checkpoint>

</phase>

## Phase 6: Frontend Planner Composable Fixes

<phase id="6" name="Planner Composable Fixes" depends="">

### 6.1 Fix `mapPantryToScoring()` typing

<task id="6.1" status="pending" depends="" risk="low">
<description>
Replace `any` type annotations in `mapPantryToScoring()` in `frontend/app/composables/optimizer/use-optimizer-planner.ts` (lines 133-143) with proper types (Finding #15).

**Current code**:
```typescript
function mapPantryToScoring(items: any[]): PantryItemScoring[] {
  return items
    .filter((item: any) => item.foodId)
    .map((item: any) => ({ ... }));
}
```

**Fix**: Import `PantryItemOut` from the API types and use it:
```typescript
import type { PantryItemOut } from "~/lib/api/types/optimizer";

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

**Check**: Verify `PantryItemOut` type has all the fields accessed: `foodId`, `food`, `name`, `usePriority`, `assumeEnough`, `expirationDate`. Also verify `food` has `name` and `label.name`.

**Also check**: Is `PantryItemScoring` already imported? Look at existing imports at top of file.
</description>

<subtasks>
- [ ] Check if `PantryItemOut` is already imported in use-optimizer-planner.ts — if not, add import
- [ ] Check if `PantryItemScoring` is already imported — if not, add import from `./types`
- [ ] Replace `items: any[]` with `items: PantryItemOut[]`
- [ ] Remove `(item: any)` type annotations from filter/map callbacks (TypeScript infers from array type)
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

<task id="6.2" status="pending" depends="" risk="medium">
<description>
Fix the diff detection in `savePlan()` in `frontend/app/composables/optimizer/use-optimizer-planner.ts` to compare `entryType` and `date` in addition to `recipeId` (Finding #10).

**Current code** (line 393):
```typescript
if (snapEntry && snapEntry.recipeId !== draftEntry.recipeId) {
```

**Fix** — expand the comparison:
```typescript
if (snapEntry && (
  snapEntry.recipeId !== draftEntry.recipeId ||
  snapEntry.entryType !== draftEntry.entryType ||
  snapEntry.date !== draftEntry.date
)) {
```

**Also fix `hasUnsavedChanges`** (per Codex review): The `hasUnsavedChanges` computed property (around lines 115-129) has the same blind spot. It compares arrays by checking `recipeId` and `existingEntryId` but does NOT check `entryType` or `date`. Find the comparison logic in `hasUnsavedChanges` and add the same fields.

Look at the `hasUnsavedChanges` implementation — it likely does a structural comparison of the draft vs snapshot arrays. If it uses a simple equality check on the entry objects, verify that `entryType` and `date` are included in whatever comparison is used.

**Current hasUnsavedChanges** (lines 115-129): Read the actual implementation to determine what comparison it uses and whether it needs updating.
</description>

<subtasks>
- [ ] Read `hasUnsavedChanges` implementation (lines 115-129) to understand its comparison logic
- [ ] Fix `savePlan()` diff detection at line 393: add `entryType` and `date` comparisons
- [ ] Fix `hasUnsavedChanges` if it has the same blind spot (compare entryType and date)
- [ ] Verify: changing a meal's entryType triggers an update on save
- [ ] Verify: changing a meal's date triggers an update on save
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
<success_criteria>Findings #10 and #15 resolved. Planner diff detection is comprehensive and types are explicit.</success_criteria>
</checkpoint>

</phase>

## Phase 7: Nav i18n

<phase id="7" name="Navigation Internationalization" depends="">

### 7.1 Replace hardcoded "Pantry" with i18n key

<task id="7.1" status="pending" depends="" risk="low">
<description>
Replace the hardcoded `"Pantry"` string in `frontend/app/components/Layout/DefaultLayout.vue` (line 251) with the existing i18n key (Finding #9).

**Current code** (line 251):
```javascript
title: "Pantry",
```

**Fix**:
```javascript
title: i18n.t("optimizer.pantry.title"),
```

**Context**: The `i18n` object is already available in this file — see line 257 where `i18n.t("optimizer.planner.title")` is used. The key `optimizer.pantry.title` with value `"Pantry"` already exists in `frontend/app/lang/messages/en-US.json` at line 1486.
</description>

<subtasks>
- [ ] Replace `"Pantry"` with `i18n.t("optimizer.pantry.title")` on line 251
- [ ] Verify the i18n key exists in en-US.json
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
<success_criteria>Finding #9 resolved.</success_criteria>
</checkpoint>

</phase>

## Final Validation

<final_validation>
<verification>
- [ ] `task py:lint` passes (all Python changes)
- [ ] `task ui:lint` passes (all frontend changes)
- [ ] `task ui:test` passes (scoring-engine tests — existing + new)
- [ ] No regressions in existing scoring-engine test suite (397+ lines)
- [ ] Manual verification: `deduct_shopping_items` makes batch query (check code)
- [ ] Manual verification: `calculate_deficit` handles duplicate food_ids (check code)
- [ ] Manual verification: `check_shopping_items` returns new list without mutating input (check code)
- [ ] Manual verification: recipe projection uses `load_only()` (check code)
- [ ] Manual verification: shopping_lists.py logs pantry errors (check code)
- [ ] Manual verification: DefaultLayout.vue uses i18n for Pantry (check code)
</verification>
<acceptance>All 17 review findings addressed (13 fixed, 2 comment/doc only, 2 deferred as out-of-scope per spec). All linting and tests pass. No schema/migration changes required.</acceptance>
</final_validation>

## Findings Coverage Map

| Finding | Severity | Description | Task | Status |
|---------|----------|-------------|------|--------|
| #1 | Critical | N+1 query in deduct_shopping_items | 1.1 + 2.1 | Planned |
| #2 | High | Orphaned unit FK guard | 2.1 | Planned |
| #3 | High | Recipe projection full ORM load | 4.1 | Planned |
| #4 | High | Narrow time parsing | 5.1 + 5.2 | Planned |
| #5 | High | Bare except in shopping_lists | 3.1 | Planned |
| #6 | Medium | Deficit duplicate food_id | 2.2 | Planned |
| #7 | Medium | (covered by other tasks) | — | — |
| #8 | Medium | is_staple behavior | — | Out of scope |
| #9 | Medium | Nav i18n hardcoded | 7.1 | Planned |
| #10 | Medium | savePlan diff detection | 6.2 | Planned |
| #11 | Medium | Shopping item validation | 2.1 | Planned |
| #12 | Medium | In-place mutation | 2.3 | Planned |
| #13 | Medium | (overlap score direction) | 5.3 | Planned |
| #14 | Low | UnitConverter per-request | 2.1 | Planned |
| #15 | Low | mapPantryToScoring typing | 6.1 | Planned |
| #16 | Low | excludeExpired UI toggle | — | Out of scope |
| #17 | Low | Overlap score comment | 5.3 | Planned |

## Dependency Verification Log

<dependency_log>
<dependency name="collections.abc.Sequence" verified="true">
  <version>Python 3.12 stdlib</version>
  <verified_via>Already imported in repository_generic.py line 4 (Iterable from same module)</verified_via>
  <notes>No concerns</notes>
</dependency>
<dependency name="pint.UnitRegistry" verified="true">
  <version>Used via mealie/services/parser_services/parser_utils/unit_utils.py</version>
  <verified_via>Read unit_utils.py — UnitRegistry instantiated in __init__, only .can_convert() and .convert() called (read-only after init)</verified_via>
  <notes>Thread-safe for concurrent reads when state is not mutated. Module-level singleton is safe for this usage pattern.</notes>
</dependency>
<dependency name="sqlalchemy.orm.load_only" verified="true">
  <version>SQLAlchemy 2.x</version>
  <verified_via>SQLAlchemy docs — load_only() is a column-level loader option compatible with selectinload()</verified_via>
  <notes>Must use load_only() on the entity, NOT switch to raw column select. Raw column select breaks selectinload.</notes>
</dependency>
<dependency name="Pydantic BaseModel.model_copy()" verified="true">
  <version>Pydantic 2.x</version>
  <verified_via>Codebase uses Pydantic v2 (MealieModel extends BaseModel). model_copy() is the v2 replacement for .copy().</verified_via>
  <notes>No concerns</notes>
</dependency>
<dependency name="mealie.core.root_logger.get_logger" verified="true">
  <version>Internal utility</version>
  <verified_via>Already imported in repository_generic.py line 17</verified_via>
  <notes>Standard Mealie logging pattern</notes>
</dependency>
<dependency name="i18n key optimizer.pantry.title" verified="true">
  <version>N/A</version>
  <verified_via>Read en-US.json — key exists at line 1486 with value "Pantry"</verified_via>
  <notes>No concerns</notes>
</dependency>
</dependency_log>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-16-023822-optimizer-review-remediation.md">
  <question>Should parseTimeToMinutes return 0 instead of null for unparseable times?</question>
  <impact>Returning 0 would make the prep filter EXCLUDE unknown-time recipes (stricter). Current behavior lets them through.</impact>
  <default_assumption>Keep returning null — don't penalize recipes with missing time data. prepTimeScore returns 1.0 for null.</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-16-023822-optimizer-review-remediation.md">
  <question>Should recipe projection add pagination or is query optimization sufficient?</question>
  <impact>For 2000+ recipes the response payload is still large, but pagination would require architectural changes to client-side scoring.</impact>
  <default_assumption>Optimize query first with load_only(). Pagination deferred — planner needs all recipes for scoring.</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-16-023822-optimizer-review-remediation.md">
  <question>Should deduct_shopping_items raise an error if some IDs were not found?</question>
  <impact>Raising errors would make the API stricter but could break frontend flows that pass stale IDs.</impact>
  <default_assumption>Silently skip — consistent with HouseholdRepositoryGeneric scoping pattern and existing behavior.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-16-023822-optimizer-review-remediation.md">
<resolved original_question="Should parseTimeToMinutes return 0 instead of null for unparseable times?">
  <resolution>Spec default adopted: keep returning null. Verified that prepTimeScore(null budget) returns 1.0 and prepTimeScore(non-null budget, null time) also returns 1.0, so unknown-time recipes are not penalized.</resolution>
</resolved>
<resolved original_question="Should recipe projection add pagination or is query optimization sufficient?">
  <resolution>Spec default adopted: optimize query with load_only() first. Codex confirmed that pagination would require fundamental architectural changes to client-side scoring.</resolution>
</resolved>
<resolved original_question="Should deduct_shopping_items raise an error if some IDs were not found?">
  <resolution>Spec default adopted: silently skip. Codex confirmed HouseholdRepositoryGeneric already scopes queries, so cross-household IDs naturally return no results from get_many().</resolution>
</resolved>
</resolved_from_source>

## Plan Review Notes

<codex_response>
The plan is mostly directionally right, but two items are understated architecturally: the base-repo change and the recipe projection query.

1. `get_many()` on `RepositoryGeneric` is safe only if you keep the contract very narrow. Additive API on a base class is low risk, but the blast radius is real because every repo inherits the query path. The safe shape is: exact-match lookup by one key, tenant-scoped via `_filter_builder()`, same `_query()` path so schema loader options still apply, empty input returns `[]`. The hidden decisions are order and duplicates: SQL `IN (...)` does not preserve input order, and a list return silently drops missing ids.

2. The Phase 4 query as written is not aligned with SQLAlchemy loader semantics. `selectinload(...)` works because the statement selects `RecipeModel`. If you switch to `select(RecipeModel.id, ...)`, loader options for relationships no longer apply. The right optimization is `select(RecipeModel).options(load_only(...), selectinload(...))`, not a pure column tuple select.

3. Phase 2 is too broad: it mixes a shared deduction refactor, a base-repo dependency, a business-rule fix, an immutability change, and a singleton lifecycle change. Recommended splitting into: deduction-path refactor + get_many consumer; calculate_deficit duplicate ingredient aggregation; check_shopping_items purity change + UnitConverter lifetime change.

4. Hidden multi-step items: orphaned unit FK guard needs definition of "orphaned" vs "same unit omitted"; `hasUnsavedChanges` has the same blind spot as `savePlan()` diff detection.

5. `UnitConverter` singleton: acceptable if UnitRegistry is initialized once and used read-only.

6. `model_copy()` in check_shopping_items: safe — caller rebinds the returned list.
</codex_response>

<changes_made>
1. **Phase 4 rewritten**: Changed from raw column `select()` to `load_only()` approach per Codex recommendation. This preserves `selectinload()` compatibility while still restricting loaded columns.
2. **Phase 2 split into 3 tasks**: Task 2.1 (deduction refactor + N+1 + singleton), Task 2.2 (deficit aggregation), Task 2.3 (immutability). This addresses Codex's concern about Phase 2 being too broad.
3. **hasUnsavedChanges added to Task 6.2**: Per Codex observation that it has the same blind spot as savePlan() diff detection.
4. **get_many() contract documented explicitly**: Order not guaranteed, missing IDs silently excluded, uses _query() for loader options.
5. **Orphaned unit FK guard detailed**: Explicitly defined "orphaned" (both resolved None but original unit_id was set) vs "genuinely unitless" (both None, original None) in Task 2.1.
</changes_made>
