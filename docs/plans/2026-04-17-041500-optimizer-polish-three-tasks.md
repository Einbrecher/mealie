# Implementation Plan: Optimizer Polish — Diff Helper, DeductionItem, Test Coverage
Source: docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md
Created: 2026-04-17

<plan_metadata>
  <feature>optimizer-polish-three-tasks</feature>
  <source_doc>docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md</source_doc>
  <total_phases>4</total_phases>
  <total_tasks>7</total_tasks>
  <critical_path>1.1 → 1.2 → 1.3 (Phase 1 gates all frontend work); 2.1 (gates 3.1)</critical_path>
  <status>draft</status>
</plan_metadata>

## Overview
Three small polish items in the optimizer fork: (1) centralize the DraftPlanEntry diff logic
behind a pure `draftEntryFieldsChanged` helper consumed by both `hasUnsavedChanges` and
`savePlan()`; (2) replace the positional 4-tuple transport inside `PantryService._deduct_items`
with a `DeductionItem` NamedTuple; (3) backfill unit/integration tests for three recently
landed paths — `RepositoryGeneric.get_many()`, the `_deduct_items` orphaned-FK skip guard,
and planner diff field sensitivity. All behavior is preserved; this is refactor + tests.

## Dependencies & Prerequisites

<prerequisites>
<prereq id="P1" type="library" verified="true">
  <description>vitest runner for frontend composable unit tests</description>
  <verification>frontend/app/composables/optimizer/scoring-engine.test.ts and use-expiration-helpers.test.ts already run under `task ui:test`.</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>typing.NamedTuple (Python stdlib)</description>
  <verification>Standard library on Python 3.12 (project stack per CLAUDE.md).</verification>
</prereq>
<prereq id="P3" type="environment" verified="true">
  <description>PostgreSQL + migrations up for integration tests</description>
  <verification>`task dev:services` + `task py:migrate`; `tests/integration_tests/test_repository_factory.py` already uses the `session` fixture with this setup.</verification>
</prereq>
<prereq id="P4" type="data" verified="true">
  <description>Existing factories: `_make_food`, `_make_unit`, `_make_pantry_item` in test_pantry_service.py (lines 14–67); `random_string`, `random_email` in tests/utils/factories.</description>
  <verification>Read confirmed factories exist at those exact lines; reused without modification.</verification>
</prereq>
<prereq id="P5" type="library" verified="true">
  <description>`get_repositories(session, group_id=..., household_id=...)` + per-tenant repo construction pattern</description>
  <verification>Pattern used at test_repository_factory.py:121–122, 154–155, 219–220, 280–281.</verification>
</prereq>
<prereq id="P6" type="service" verified="true">
  <description>`RepositoryGeneric.get_many()` exists with empty-input short-circuit, IN() scoping, `override_schema`, and named-key support</description>
  <verification>mealie/repos/repository_generic.py:181–199 — signature and body match spec exactly.</verification>
</prereq>
<prereq id="P7" type="service" verified="true">
  <description>Existing unit-test harness: `object.__new__(PantryService)` + manual `converter = UnitConverter()` assignment</description>
  <verification>tests/unit_tests/services_tests/test_pantry_service.py:82–86 establishes this pattern for `calculate_deficit`.</verification>
</prereq>
</prerequisites>

## Phase 1: Frontend — Centralize Planner Diff

<phase id="1" name="Frontend — Centralize Planner Diff">

### 1.1 Extract shared DraftPlanEntry + create `planner-diff.ts` helper

<task id="1.1" status="pending" depends="" risk="low">
<description>
This task is a single atomic structural move: the type relocation and the new helper module
are tightly coupled (moving the type alone has no consumer; the helper alone has no type).
Per Codex review: "Avoid a standalone task whose only effect is moving `DraftPlanEntry`; that
move has no value unless the helper and imports change with it." Do both in one pass.

**Part A — Relocate `DraftPlanEntry` to the shared types module**
Today `DraftPlanEntry` is declared inline in `frontend/app/composables/optimizer/use-optimizer-planner.ts`
(lines 10–22). The new pure helper module must import this interface without creating a
wrong-direction dependency (helper → stateful composable). Move the interface to the
already-established shared module `frontend/app/composables/optimizer/types.ts` and import
`PlanEntryType` from `~/lib/api/types/meal-plan` at the top of types.ts.

This is UI-local state (not an API contract). Per Codex: "keep it clearly UI-local and do not
promote it into shared API types." Do NOT add it to `frontend/app/lib/api/types/` — it stays
in the composables-facing types module.

Field list to preserve verbatim (11 fields, declaration order):
- localId: string
- date: string
- entryType: PlanEntryType
- order: number
- recipeId: string | null
- recipeName: string | null
- recipeSlug: string | null
- existingEntryId: number | null
- groupId: string | null
- userId: string | null
- householdId: string | null

**Part B — Create the pure `planner-diff.ts` helper**
Create a new pure module `frontend/app/composables/optimizer/planner-diff.ts` exporting:
- `DRAFT_PAYLOAD_FIELDS` — readonly tuple `["recipeId", "entryType", "date"] as const` so call
  sites (and future debuggers) can iterate without drift.
- `draftEntryFieldsChanged(a: DraftPlanEntry, b: DraftPlanEntry): boolean` — returns true iff any
  of the three payload fields differ. Does NOT compare `existingEntryId` (identity), `localId`
  (client-only), `order` (ordering concern), `groupId`/`userId`/`householdId` (server-assigned
  bookkeeping), or `recipeName`/`recipeSlug` (denormalized display state that mirrors recipeId).

Implementation: iterate `DRAFT_PAYLOAD_FIELDS` and return true on the first inequality. Using
the exported tuple (not hard-coded field names inside the function body) keeps the module
self-documenting and ensures `DRAFT_PAYLOAD_FIELDS` stays the single source of truth.

Module hygiene:
- No Vue/Nuxt imports. No `ref`, `computed`, or composable imports.
- Import ONLY `DraftPlanEntry` as a type from `./types`.
- Export both `DRAFT_PAYLOAD_FIELDS` and `draftEntryFieldsChanged`.

**Part C — Wire the composable's import** (minimal — the actual call-site refactor is task 1.2)
Update the existing `./types` import in `use-optimizer-planner.ts` so `DraftPlanEntry` is pulled
from `./types` rather than declared inline. Delete the in-file `export interface DraftPlanEntry`
block. Do NOT yet change the `hasUnsavedChanges` / `savePlan` bodies — that's task 1.2.
</description>

<subtasks>
- [ ] **Part A** — Open `frontend/app/composables/optimizer/types.ts`. Add `import type { PlanEntryType } from "~/lib/api/types/meal-plan";` as the first line (this file has no imports today). Append `export interface DraftPlanEntry { ... }` at the end with the 11 fields above in declaration order.
- [ ] **Part A** — In `frontend/app/composables/optimizer/use-optimizer-planner.ts`, delete the `export interface DraftPlanEntry { ... }` block at lines 10–22. Update the `./types` import on line 5 to include `DraftPlanEntry`: `import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring, DraftPlanEntry } from "./types";`.
- [ ] **Part B** — Create `frontend/app/composables/optimizer/planner-diff.ts`. Only import: `import type { DraftPlanEntry } from "./types";`. Export `DRAFT_PAYLOAD_FIELDS = ["recipeId", "entryType", "date"] as const;`. Export `function draftEntryFieldsChanged(a: DraftPlanEntry, b: DraftPlanEntry): boolean` that loops over `DRAFT_PAYLOAD_FIELDS` and returns `true` at the first inequality, else `false`.
- [ ] Verify `grep -n "import " frontend/app/composables/optimizer/planner-diff.ts` shows exactly one import (the DraftPlanEntry type).
- [ ] Verify `grep -rn "interface DraftPlanEntry" frontend/app` returns exactly one hit (in types.ts).
- [ ] Run `task ui:check` — the composable's existing inline `recipeId !==` etc. comparisons are STILL present at this point (that's task 1.2) and must still type-check.
</subtasks>

<acceptance>
- `task ui:check` (lint + type-check) passes.
- `grep -rn "interface DraftPlanEntry" frontend/app` returns exactly one hit (in types.ts).
- `frontend/app/composables/optimizer/planner-diff.ts` exists with ONE import (the type-only import from `./types`) and exports both `DRAFT_PAYLOAD_FIELDS` and `draftEntryFieldsChanged`.
- `DraftPlanEntry` is NOT added to `frontend/app/lib/api/types/` — it remains UI-local.
</acceptance>
</task>

### 1.2 Refactor use-optimizer-planner.ts call sites to use the helper

<task id="1.2" status="pending" depends="1.1" risk="medium">
<description>
Replace the inline field-by-field equality in two call sites. Behavior must be strictly
preserved. Both sites carefully keep the existingEntryId and array-length checks inline
because those are identity/length concerns, NOT payload diffs — absorbing them into the
helper would break `hasUnsavedChanges` after a save (snapshot gets rebuilt with fresh
existingEntryId values).

Call site 1 — `hasUnsavedChanges` at lines 113–131:
- KEEP inline: `draftArr.length !== snapArr.length` check, `draftArr[i].existingEntryId !== snapArr[i].existingEntryId` check.
- REPLACE: the three `recipeId !== / entryType !== / date !==` checks with a single
  `if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;`.

Call site 2 — `savePlan()` at lines 394–399 (the update-branch predicate):
- REPLACE: the `if (snapEntry && (snapEntry.recipeId !== ... || snapEntry.entryType !== ... || snapEntry.date !== ...))`
  predicate with `if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry))`.

Add the new import `import { draftEntryFieldsChanged } from "./planner-diff";` at the top of
the file. Do NOT re-export `draftEntryFieldsChanged` from the composable; callers that want it
import from `./planner-diff` directly.
</description>

<subtasks>
- [ ] In use-optimizer-planner.ts, add `import { draftEntryFieldsChanged } from "./planner-diff";` below the existing `./types` import (around line 6).
- [ ] Replace the inner three `!==` comparisons in the `hasUnsavedChanges` computed (lines 124, 126, 127 — `recipeId !==`, `entryType !==`, `date !==`) with a single `if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;`. Keep lines 122 (array-length check) and 125 (`existingEntryId !==` check) UNCHANGED.
- [ ] Replace the compound `&&` predicate in `savePlan` (lines 395–399) with `if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry)) { ... }`. The inner `toUpdate.push({ id, payload: { ... } })` call is unchanged.
- [ ] Run `grep -n "recipeId !==\|entryType !==\|date !==" frontend/app/composables/optimizer/use-optimizer-planner.ts` to confirm no residual inline payload comparisons remain (there should be zero hits).
- [ ] Run `task ui:check` and `task ui:test` (the existing test suite is the behavioral safety net until 1.4 adds direct coverage).
</subtasks>

<acceptance>
- Exactly zero hits for `recipeId !==`, `entryType !==`, `date !==` inside use-optimizer-planner.ts.
- `hasUnsavedChanges` still flips on: array-length change, existingEntryId drift, payload-field change.
- `savePlan()` still partitions into toCreate/toUpdate/toDelete on the same fixtures as before.
- `task ui:check` and `task ui:test` pass.
</acceptance>

<rollback risk="medium">
If behavior drifts (e.g., existingEntryId check accidentally removed), restore the two call sites
from git: `git checkout -- frontend/app/composables/optimizer/use-optimizer-planner.ts`.
The helper file and the types move (task 1.1) are additive and safe to keep.
</rollback>
</task>

### 1.3 Add planner-diff.test.ts coverage

<task id="1.3" status="pending" depends="1.1" risk="low">
<description>
Create `frontend/app/composables/optimizer/planner-diff.test.ts` matching the shape of
`use-expiration-helpers.test.ts`. Six cases:

1. Identical entries → false.
2. `recipeId` differs (including `null → "abc"`) → true.
3. `entryType` differs (e.g., `"breakfast"` vs `"dinner"`) → true.
4. `date` differs → true.
5. Only `existingEntryId` differs → false (identity, not payload).
6. Only `localId` OR `order` OR `recipeName` OR `recipeSlug` differs → false (display/bookkeeping-only).

Use a local `makeEntry(overrides: Partial<DraftPlanEntry> = {}): DraftPlanEntry` factory that
fills all 11 fields with sensible defaults. Import `draftEntryFieldsChanged` from `./planner-diff`
and `DraftPlanEntry` as a type from `./types`. Do NOT import from `use-optimizer-planner.ts`.

File layout mirrors use-expiration-helpers.test.ts: top-level factory, one `describe` per helper.
</description>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/planner-diff.test.ts`.
- [ ] Add imports: `import { describe, it, expect } from "vitest";`, `import { draftEntryFieldsChanged, DRAFT_PAYLOAD_FIELDS } from "./planner-diff";`, `import type { DraftPlanEntry } from "./types";`.
- [ ] Write `makeEntry` factory with defaults for all 11 fields (use literal strings/UUIDs — no `crypto.randomUUID()` dependency so tests stay deterministic and fast).
- [ ] Write `describe("draftEntryFieldsChanged", ...)` block containing the 6 `it(...)` cases listed above.
- [ ] Add one small `describe("DRAFT_PAYLOAD_FIELDS", ...)` block asserting the exported tuple equals `["recipeId", "entryType", "date"]` — this pins the semantic contract.
- [ ] Run `task ui:test` and confirm all new cases pass.
</subtasks>

<acceptance>
- 7 assertions pass under `task ui:test` (6 `draftEntryFieldsChanged` cases + 1 tuple contract).
- The test file does not import from `use-optimizer-planner.ts`.
- Running `task ui:test` from the repo root discovers and runs the new file.
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `task ui:check` passes.
- [ ] `task ui:test` passes.
- [ ] Manual smoke: open `http://localhost:3000/g/{group}/optimizer/planner` (per CLAUDE.md), drag a recipe into a slot, confirm "unsaved changes" indicator appears; click Save, confirm indicator clears.
- [ ] `grep -n "interface DraftPlanEntry" frontend/app` returns exactly one hit.
</verification>
<success_criteria>Frontend type-checks cleanly, all tests green, diff logic lives in ONE place and is exercised by tests.</success_criteria>
</checkpoint>

</phase>

## Phase 2: Backend — DeductionItem NamedTuple

<phase id="2" name="Backend — Type _deduct_items Transport">

### 2.1 Introduce `DeductionItem` and migrate all three sites atomically

<task id="2.1" status="pending" depends="" risk="medium">
<description>
Replace `list[tuple[UUID4, float, object | None, UUID4 | None]]` with
`list[DeductionItem]` at all three touch points in `mealie/services/optimizer/pantry.py`:

1. The parameter annotation on `_deduct_items` (line 313).
2. The construction in `deduct_recipe` (line 377).
3. The construction in `deduct_shopping_items` (line 396).

`DeductionItem` is a module-level `typing.NamedTuple` declared BEFORE the `PantryService`
class (so the class body can reference it in annotations without forward-ref gymnastics).
NamedTuple preserves positional destructuring, so the existing
`for food_id, qty, unit_obj, original_unit_id in items:` loop at line 324 needs zero changes.

Declaration:
```python
class DeductionItem(NamedTuple):
    food_id: UUID4
    quantity: float
    unit_obj: object | None          # resolved IngredientUnit (or None)
    original_unit_id: UUID4 | None   # raw FK column value; non-None with unit_obj=None implies orphaned FK
```

Add `from typing import NamedTuple` to the existing `from typing import TYPE_CHECKING` import
at line 4 → `from typing import NamedTuple, TYPE_CHECKING` (preserve alphabetical order if the
file's convention is alphabetical — spot-check adjacent imports; today line 4 is the only
`from typing` line so a single combined import is cleanest).

Construction change — replace tuple literals with `DeductionItem(...)`:
- `deduct_recipe` line 377: `food_qty_units.append(DeductionItem(ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))`
- `deduct_shopping_items` line 396: `food_qty_units.append(DeductionItem(item.food_id, item.quantity or 0, unit_obj, original_unit_id))`

Also type the local variables:
- line 371 `food_qty_units = []` → `food_qty_units: list[DeductionItem] = []`
- line 390 `food_qty_units = []` → `food_qty_units: list[DeductionItem] = []`

`DeductionItem` must be exported from the module (no underscore prefix) so tests in
Phase 3 can import it as `from mealie.services.optimizer.pantry import DeductionItem`.
</description>

<subtasks>
- [ ] Open `mealie/services/optimizer/pantry.py`.
- [ ] Change the `typing` import on line 4 from `from typing import TYPE_CHECKING` to `from typing import NamedTuple, TYPE_CHECKING`.
- [ ] Insert the `class DeductionItem(NamedTuple): ...` block after the existing imports and `_unit_converter = UnitConverter()` line (around line 22), before `class PantryService:`.
- [ ] On line 313, change `food_qty_units: list[tuple[UUID4, float, object | None, UUID4 | None]]` to `food_qty_units: list[DeductionItem]`.
- [ ] On line 371, change `food_qty_units = []` to `food_qty_units: list[DeductionItem] = []`.
- [ ] On line 377, change `food_qty_units.append((ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))` to `food_qty_units.append(DeductionItem(ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))`.
- [ ] On line 390, change `food_qty_units = []` to `food_qty_units: list[DeductionItem] = []`.
- [ ] On line 396, change `food_qty_units.append((item.food_id, item.quantity or 0, unit_obj, original_unit_id))` to `food_qty_units.append(DeductionItem(item.food_id, item.quantity or 0, unit_obj, original_unit_id))`.
- [ ] Verify line 324 (`for food_id, qty, unit_obj, original_unit_id in items:`) is UNCHANGED — NamedTuple iteration order matches field-declaration order, so positional unpack still binds correctly.
- [ ] Run `grep -n "tuple\[UUID4, float" mealie/services/optimizer/pantry.py` and confirm zero hits.
- [ ] Run `task py:check` (ruff + type checks).
- [ ] Run `task py:test -- -k pantry_service` and confirm existing tests still pass.
</subtasks>

<acceptance>
- No `tuple[UUID4, float, object | None, UUID4 | None]` annotation remains in this module.
- Existing tests in tests/unit_tests/services_tests/test_pantry_service.py pass unchanged (`task py:test -- -k pantry_service` green).
- `task py:check` passes.
- `DeductionItem` is importable via `from mealie.services.optimizer.pantry import DeductionItem` (verify with `python -c "from mealie.services.optimizer.pantry import DeductionItem; print(DeductionItem)"` — optional sanity check).
</acceptance>

<rollback risk="medium">
Single-file change. If tests fail or type-check breaks:
`git checkout -- mealie/services/optimizer/pantry.py`.
No other files depend on the tuple shape directly — only the tests in Phase 3 will reference
`DeductionItem`, and they haven't been added yet at this point.
</rollback>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task py:check` passes.
- [ ] `task py:test -- -k pantry_service` passes (existing suite).
- [ ] `grep -n "DeductionItem" mealie/services/optimizer/pantry.py` returns ≥ 5 hits (class decl + annotation + 2 list-type annotations + 2 constructor calls).
</verification>
<success_criteria>Transport type migrated with zero behavioral change; public API of `deduct_recipe` / `deduct_shopping_items` is unchanged; tuple annotation is gone.</success_criteria>
</checkpoint>

</phase>

## Phase 3: Backend Tests — Pantry Orphaned-FK Guard

<phase id="3" name="Backend Tests — PantryService Orphaned-FK Guard" depends="2">

### 3.1 Add DeductItemsOrphanedFKTests class

<task id="3.1" status="pending" depends="2.1" risk="low">
<description>
Append a new test class `DeductItemsOrphanedFKTests` to
`tests/unit_tests/services_tests/test_pantry_service.py` that exercises the three
distinct skip/deduct branches at pantry.py:335–349. Three tests (the third was
added to resolve open question Q2):

**test_orphaned_fk_skips_deduction**
Source DeductionItem has `unit_obj=None` (relationship didn't resolve) but
`original_unit_id=<some UUID>` (FK column is populated — the shopping item originally
had a unit reference that is now orphaned). Pantry item has `unit=None`
(`pantry_unit_id` is also None). The branch at pantry.py:335 sees both unit IDs as None;
the inner guard at 336–337 detects `original_unit_id is not None` and calls `continue`,
skipping this deduction entirely.

Per Codex: "Hit the orphaned-FK branch by passing `original_unit_id` non-None while both
`unit_obj` and `pantry_item.unit` are `None`; a merely unitless item will not exercise the
same path."

Assertions (keep minimal — do NOT overbuild the mock for this case):
- `result == []`.
- `service.pantry_items.update.assert_not_called()`.

**test_both_genuinely_unitless_deducts** (control)
Source DeductionItem has `unit_obj=None` AND `original_unit_id=None` (truly unitless).
Pantry item has `unit=None`. The guard at 336–337 evaluates False (no original unit),
so `converted_qty = qty` (line 338) and deduction proceeds.

**Critical harness detail (Codex finding):** `_deduct_items` does NOT re-read from
`pantry_map` after the update — it appends whatever `self.pantry_items.update(...)` RETURNS
to its output list (see pantry.py:361–362). A naive `MagicMock()` returns another Mock, which
would still make `update.call_count == 1` succeed but leaves the returned-list assertions
useless. Therefore `update.side_effect` MUST return a real `PantryItemOut` carrying the new
quantity.

Also: `modified_ids` is a `set` (pantry.py:322), so for tests with multiple updates the
output-list ORDER is NOT guaranteed. Use set-based assertions or test a single-item case.

Assertions:
- `len(result) == 1`.
- `service.pantry_items.update.call_count == 1`.
- The `{"quantity": ...}` payload passed to `update` equals `max(0.0, round(5.0 - 3.0, 4))` = `2.0`. Inspect via `service.pantry_items.update.call_args.args[1]["quantity"] == 2.0` (the `update` signature is `(pantry_id, data_dict)` per pantry.py:361).
- Do NOT assert on result ordering.

**test_source_has_unit_pantry_unitless_skips** (third branch — added per Q2)
Source DeductionItem has a resolved `unit_obj` (e.g., `source_unit = _make_unit(name="cup", standard_unit="cup")`) and `original_unit_id = source_unit.id`. Pantry item has `unit=None`. Because `source_unit_id != pantry_unit_id`, control falls into the `else` arm at pantry.py:341. Since `pantry_item.unit is None`, `pantry_standard` is `None`, so the guard at line 344 fails and line 348–349 takes `continue` — deduction is skipped. This is a DIFFERENT skip path than the orphaned-FK guard (Branch A1) and pins down the Branch C fall-through.

Assertions (same minimal shape as the orphaned-FK test):
- `result == []`.
- `service.pantry_items.update.assert_not_called()`.

**Harness** (class method):
```python
from unittest.mock import MagicMock

def _service(self, pantry: PantryItemOut, new_qty: float) -> PantryService:
    service = object.__new__(PantryService)
    service.converter = UnitConverter()
    service.pantry_items = MagicMock()
    # update() must return a real PantryItemOut — _deduct_items appends this verbatim
    updated = pantry.model_copy(update={"quantity": new_qty})
    service.pantry_items.update.return_value = updated
    return service
```

Tests assert on behavior (return value shape + `update.call_count`/`call_args`), NEVER on
the internal shape of `DeductionItem`. This keeps tests decoupled from the transport
representation per the spec's Codex CONCERN #5 resolution.
</description>

<subtasks>
- [ ] Open `tests/unit_tests/services_tests/test_pantry_service.py`.
- [ ] At the top of the file, add `from unittest.mock import MagicMock` and `from mealie.services.optimizer.pantry import DeductionItem` (the file already imports `PantryService` on line 11).
- [ ] Append a new class `class DeductItemsOrphanedFKTests:` after the last existing test class.
- [ ] Implement `_service(self, pantry: PantryItemOut, new_qty: float) -> PantryService`: use `object.__new__(PantryService)`, set `service.converter = UnitConverter()` and `service.pantry_items = MagicMock()`. Set `service.pantry_items.update.return_value = pantry.model_copy(update={"quantity": new_qty})` so the updated item returned by `_deduct_items` is a real `PantryItemOut`, not a MagicMock.
- [ ] Implement `test_orphaned_fk_skips_deduction`:
    - `food = _make_food()`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=5.0)` (new_qty unused — update must never be called, but passing a sentinel simplifies the helper).
    - `pantry_map = {food.id: pantry}`.
    - `items = [DeductionItem(food.id, 3.0, None, uuid4())]` — `unit_obj=None`, `original_unit_id` populated (orphaned FK).
    - `result = service._deduct_items(items, pantry_map)`.
    - `assert result == []`.
    - `service.pantry_items.update.assert_not_called()`.
- [ ] Implement `test_both_genuinely_unitless_deducts`:
    - `food = _make_food()`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=2.0)`.
    - `items = [DeductionItem(food.id, 3.0, None, None)]` — both genuinely unitless.
    - `result = service._deduct_items(items, pantry_map={food.id: pantry})`.
    - `assert len(result) == 1`.
    - `assert result[0].quantity == 2.0` (the return_value we wired — confirms `_deduct_items` returns the update's return value, not the original pantry item).
    - `assert service.pantry_items.update.call_count == 1`.
    - `call_args = service.pantry_items.update.call_args`; `assert call_args.args[1]["quantity"] == 2.0`.
    - Do NOT assert on list ordering.
- [ ] Implement `test_source_has_unit_pantry_unitless_skips`:
    - `food = _make_food()`; `source_unit = _make_unit(name="cup", standard_unit="cup")`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=5.0)` — `new_qty` is a sentinel; `update` must never be called.
    - `items = [DeductionItem(food.id, 3.0, source_unit, source_unit.id)]` — source has unit, pantry is unitless.
    - `result = service._deduct_items(items, pantry_map={food.id: pantry})`.
    - `assert result == []`.
    - `service.pantry_items.update.assert_not_called()`.
- [ ] Run `task py:test -- -k DeductItems`.
</subtasks>

<acceptance>
- All three tests pass under `task py:test -- -k DeductItems`.
- Tests import `DeductionItem` from the public module path (no underscore-prefixed internal import).
- Tests assert on `update.call_count` and `update.call_args` — NOT on DeductionItem internals.
- No modification to `_make_food` / `_make_unit` / `_make_pantry_item` factories.
- The three tests exercise three DISTINCT branches at pantry.py:335–349: (A1) orphaned-FK skip, (A2) both-unitless deduct, (C) source-has-unit / pantry-unitless fall-through skip.
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `task py:test -- -k pantry_service` passes (existing + new tests together).
- [ ] All three new test names appear in the output: `test_orphaned_fk_skips_deduction`, `test_both_genuinely_unitless_deducts`, `test_source_has_unit_pantry_unitless_skips`.
</verification>
<success_criteria>Three distinct branches at pantry.py:335–349 (orphaned-FK skip, both-unitless deduct, source-has-unit / pantry-unitless skip) are directly exercised and locked in.</success_criteria>
</checkpoint>

</phase>

## Phase 4: Backend Tests — RepositoryGeneric.get_many() Coverage

<phase id="4" name="Backend Tests — get_many Coverage">

### 4.1 Add 5 get_many tests to test_repository_factory.py

<task id="4.1" status="pending" depends="" risk="low">
<description>
Append five new tests to `tests/integration_tests/test_repository_factory.py` verifying
`RepositoryGeneric.get_many()` behavior at mealie/repos/repository_generic.py:181–199:

1. **test_get_many_empty_input_returns_empty_list** — `values=[]` short-circuits to `[]` (no DB call required, but the test still exercises a real repo bound to a session). Use `unfiltered_repos.ingredient_foods.get_many([])` and assert `== []`.

2. **test_get_many_returns_all_matching_ids** — Create a group + household, seed N=3 `ingredient_foods` in the same group, request all 3 by PK via `group_repos.ingredient_foods.get_many([f1.id, f2.id, f3.id])`, assert `{r.id for r in result} == {f1.id, f2.id, f3.id}` (set equality, per the "order is NOT guaranteed" contract at repository_generic.py:189).

3. **test_get_many_silently_excludes_missing_ids** — Seed 2 foods, call `get_many([existing1.id, existing2.id, uuid4(), uuid4()])`, assert `len(result) == 2` and `{r.id for r in result} == {existing1.id, existing2.id}`, no exception raised.

4. **test_get_many_respects_tenant_scoping** — Mirror the pattern at test_repository_factory.py:115–144 (`test_group_repositories_filter_by_group`):
    - Create group_1, group_2.
    - Build `group_1_repos` and `group_2_repos` via `get_repositories(session, group_id=..., household_id=None)`.
    - Seed food_1 in group_1, food_2 in group_2.
    - Request BOTH ids from group_1_repos.ingredient_foods.get_many([food_1.id, food_2.id]) and assert the result contains only food_1.
    - Symmetrically request from group_2_repos and assert only food_2 is returned.
    - Also verify `unfiltered_repos.ingredient_foods.get_many([food_1.id, food_2.id])` returns both.

5. **test_get_many_supports_named_key** — Uses Recipe.slug as the alt-key column, mirroring the existing slug-keyed pattern at test_repository_factory.py:237–244. Create a household, 2 recipes, call `household_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")`, assert the returned set contains both recipes. (The `key` parameter is confirmed at repository_generic.py:184.)

All tests use the `session: Session` fixture (already used throughout this file), follow
the file's existing conventions (factory helpers at tests.utils.factories, `SaveIngredientFood`,
`get_repositories`, `Recipe` schema from `mealie.schema.recipe.recipe`), and assert with SET
equality where order doesn't matter.

Important: do NOT invent test-only models or add new fixtures. Reuse what's already in the file.
</description>

<subtasks>
- [ ] Open `tests/integration_tests/test_repository_factory.py`.
- [ ] Append 5 new top-level `def test_get_many_...(session: Session):` functions (NOT inside a class — the file uses module-level functions).
- [ ] For empty-input test: use `unfiltered_repos = get_repositories(session, group_id=None, household_id=None)` and call `unfiltered_repos.ingredient_foods.get_many([])`.
- [ ] For batch-fetch test: create a group, per-group repo, seed 3 `SaveIngredientFood` records with distinct `id=uuid4()` and `name=random_string()`; call `get_many([f1.id, f2.id, f3.id])`; assert on set equality.
- [ ] For missing-ids test: seed 2 foods, mix 2 real + 2 random UUIDs in the input list, assert `len(result) == 2` and set equality on IDs.
- [ ] For tenant-scoping test: clone the setup structure at lines 115–144 (two groups, two per-group repos). Both groups must use distinct `group_id` values — use `unfiltered_repos.groups.create(...)` as at line 115 to create them.
- [ ] For named-key test: mirror the recipe + household + user setup at lines 189–235 (create group, 2 households, 2 users, 2 recipes). Call `household_1_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")` and assert it returns only recipe_1 (household scoping also applies). Then call `unfiltered_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")` and assert both are returned.
- [ ] Run `task py:test -- -k get_many` and confirm all 5 pass.
- [ ] Run `task py:test -- tests/integration_tests/test_repository_factory.py` and confirm no existing test regressed.
</subtasks>

<acceptance>
- 5 new tests pass under `task py:test -- -k get_many`.
- Tests use set equality (not list equality) per the "order not guaranteed" contract.
- Tenant-scope test exercises BOTH directions (group_1 cannot see group_2's row, and vice versa).
- Named-key test uses `key="slug"` with the Recipe repository — no new/test-only model invented.
- No new fixtures added; all tests use only `session: Session` + existing `get_repositories`.
</acceptance>

<rollback risk="low">
Additive test file change. If a specific test fails due to assumption drift:
`git checkout -- tests/integration_tests/test_repository_factory.py` restores to pre-change state.
</rollback>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task py:test -- -k get_many` passes (5 new tests).
- [ ] `task py:test -- tests/integration_tests/test_repository_factory.py` passes (all tests in file).
- [ ] `task py:check` passes (no lint violations in the new test code).
</verification>
<success_criteria>get_many() contract — empty input, batch fetch, missing IDs excluded, tenant scoping, named-key lookup — is locked down by tests.</success_criteria>
</checkpoint>

</phase>

## Final Validation

<final_validation>
<verification>
- [ ] `task py:check` passes (ruff + type checks, whole repo).
- [ ] `task ui:check` passes (eslint + type checks, whole frontend).
- [ ] `task py:test` passes (full Python suite).
- [ ] `task ui:test` passes (full frontend suite).
- [ ] No files outside `mealie/**/optimizer/`, `frontend/app/**/optimizer/`, or `tests/**` were modified. Verify with `git status` — tracked changes should ONLY be:
    - `frontend/app/composables/optimizer/types.ts`
    - `frontend/app/composables/optimizer/use-optimizer-planner.ts`
    - `frontend/app/composables/optimizer/planner-diff.ts` (new)
    - `frontend/app/composables/optimizer/planner-diff.test.ts` (new)
    - `mealie/services/optimizer/pantry.py`
    - `tests/unit_tests/services_tests/test_pantry_service.py`
    - `tests/integration_tests/test_repository_factory.py`
- [ ] `CLAUDE.md` "Modified Upstream Files" list is UNCHANGED (no new upstream edits introduced).
- [ ] Manual smoke at `http://localhost:3000/g/{group}/optimizer/planner`: add/modify/remove a slot, confirm "unsaved changes" indicator flips correctly, Save persists, indicator clears.
</verification>
<acceptance>All three spec items landed: planner diff centralized behind one helper, DeductionItem NamedTuple replaces the 4-tuple, and three new code paths have direct test coverage. No behavioral change; no new upstream edits.</acceptance>
</final_validation>

## Dependency Verification Log

<dependency_log>
<dependency name="vitest" verified="true">
  <version>existing — same as scoring-engine.test.ts and use-expiration-helpers.test.ts</version>
  <verified_via>Codebase read of those two test files confirms `describe / it / expect` imports from "vitest" work today.</verified_via>
  <notes>No new runner config required; new file is auto-discovered by existing glob.</notes>
</dependency>
<dependency name="typing.NamedTuple" verified="true">
  <version>stdlib (Python 3.12)</version>
  <verified_via>Python 3.12 is the project stack per CLAUDE.md; NamedTuple has been stable since 3.6.</verified_via>
  <notes>Chosen over @dataclass(frozen=True) so that the existing `for food_id, qty, unit_obj, original_unit_id in items:` destructure at pantry.py:324 continues to work without rewrite.</notes>
</dependency>
<dependency name="unittest.mock.MagicMock" verified="true">
  <version>stdlib</version>
  <verified_via>Used widely across the test suite.</verified_via>
  <notes>Used ONLY in Phase 3 for `PantryService.pantry_items`; no real DB needed.</notes>
</dependency>
<dependency name="RepositoryGeneric.get_many" verified="true">
  <version>present at mealie/repos/repository_generic.py:181–199</version>
  <verified_via>Direct file read; signature matches spec exactly (values, key, override_schema; empty short-circuit, IN() filter, tenant scoping via `_filter_builder()`).</verified_via>
  <notes>Order-not-guaranteed contract documented in the docstring — tests use set equality.</notes>
</dependency>
<dependency name="get_repositories + per-group/per-household repo construction" verified="true">
  <version>existing</version>
  <verified_via>Used repeatedly in test_repository_factory.py (lines 121–122, 154–155, 219–220, 280–281).</verified_via>
  <notes>Tenant-scope test for get_many reuses this pattern exactly.</notes>
</dependency>
<dependency name="Existing pantry-service test factories" verified="true">
  <version>existing at tests/unit_tests/services_tests/test_pantry_service.py:14–67</version>
  <verified_via>Direct read. `_make_food`, `_make_unit`, `_make_pantry_item` are module-level factories.</verified_via>
  <notes>Reused without modification in Phase 3.</notes>
</dependency>
</dependency_log>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md">
  <question>Should `draftEntryFieldsChanged` also compare an as-yet-unused `notes` field that exists on ReadPlanEntry but not on DraftPlanEntry today?</question>
  <impact>If added later, callers would pick up automatic sensitivity to notes changes without needing to update their own diff logic.</impact>
  <default_assumption>No — DraftPlanEntry does not carry `notes` today. Adding it is out of scope and would violate the "non-goals" constraint. If a future feature adds `notes` to DraftPlanEntry, update `DRAFT_PAYLOAD_FIELDS` in the same PR.</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md">
  <question>For get_many tenant-scope tests, which repository to use (ingredient_foods, webhooks, shopping_lists, recipes)?</question>
  <impact>Choice of repo affects setup boilerplate (household-scoped repos need user creation).</impact>
  <default_assumption>Mirror existing file conventions: use `ingredient_foods` for the group-scope case (matches lines 115–144) and `recipes` for the named-key case (matches slug assertions at 237–244). Webhooks would also work but require more setup and don't add coverage value.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md">
<resolved original_question="Should the orphaned-FK test also exercise the non-guarded control case (source has valid unit_obj but pantry unit is None) to lock down the trio of branches at pantry.py:335–349?">
  <resolution>User answered yes during plan review. Task 3.1 now includes a third test `test_source_has_unit_pantry_unitless_skips` that exercises the Branch C fall-through (`source_unit_id != pantry_unit_id`, `pantry_standard is None` → line 348–349 `continue`). This is a distinct skip path from the orphaned-FK guard in Branch A1. Phase 3 checkpoint and acceptance criteria updated accordingly.</resolution>
</resolved></resolved_from_source>

## Plan Review Notes

<review_notes>
<codex_response>
**1. Dependency risks**

No new external dependency is being introduced. `NamedTuple` is standard library and safe on Python 3.12; positional iteration/destructuring still works exactly the way `_deduct_items` currently uses tuples in `pantry.py:311`. The only real risk is not versioning, but accidentally mixing `typing.NamedTuple` and a future desire for mutability or methods.

Vitest auto-discovery also looks realistic. The frontend already runs plain `vitest` from `package.json:5`, and `vitest.config.js:4` does not override `include`, so a colocated `planner-diff.test.ts` should be picked up the same way the existing optimizer tests are.

Verbatim recommendations:
- "Do not add any package dependency for this refactor; use stdlib `typing.NamedTuple` only."
- "Treat `DeductionItem` as a readability/type-safety change, not a behavioral change; Python 3.12 has no positional-destructure risk here."
- "Keep the frontend test file named `*.test.ts` and colocated with the composable/helper so default Vitest discovery continues to work without config changes."
- "Validate CI invokes the frontend test runner at all; discovery is not the risk, pipeline coverage is."

**2. Architectural alignment**

Moving `DraftPlanEntry` out of `use-optimizer-planner.ts:10` into `types.ts:1` is acceptable and consistent with the existing optimizer-local type bucket, as long as it remains explicitly frontend-local state and does not get treated as an API contract. That is the right place for a helper-facing UI model.

Placing `DeductionItem` at module scope in `pantry.py` is also acceptable. It is an internal transport type used across `_deduct_items` plus its two builders, so module scope is better than an inner declaration. I would keep it private by naming it `_DeductionItem` unless you expect reuse from other modules.

Appending module-level tests to `test_repository_factory.py:24` fits the current file style. That file is already function-based, not class-based, so adding more top-level test functions is the least surprising option.

Verbatim recommendations:
- "Move `DraftPlanEntry` to `frontend/app/composables/optimizer/types.ts`, but keep it clearly UI-local and do not promote it into shared API types."
- "Add the diff helper as a standalone pure module in the same optimizer composables area; that aligns with the existing frontend structure."
- "Define `_DeductionItem` at module scope in `mealie/services/optimizer/pantry.py`; that is the correct scope for an internal cross-function transport type."
- "Add the `get_many()` coverage as module-level test functions in `test_repository_factory.py`; that matches the file's existing convention."

**3. Task atomicity**

Phase 2 task 2.1 is not too big. It is cross-site, but tightly coupled: type definition, `_deduct_items` annotation/destructure target, and the two tuple construction sites should change in one pass or not at all. Splitting that too finely creates temporary inconsistent states with low value.

Phase 1 is more mixed. If tasks 1.1–1.4 separate "move type", "create helper", "refactor call sites", and "add tests", that is probably too granular for LLM execution. The move and helper extraction are structurally coupled. I would collapse Phase 1 into two implementation tasks plus tests.

Verbatim recommendations:
- "Keep Phase 2 task 2.1 as one atomic refactor: introduce `_DeductionItem` and update every construction/destructure site in the same change."
- "Do not split the NamedTuple migration into separate micro-tasks unless you need an explicit review checkpoint."
- "Collapse Phase 1 implementation into: (1) extract shared planner diff types/helper, (2) refactor planner call sites, (3) add tests."
- "Avoid a standalone task whose only effect is moving `DraftPlanEntry`; that move has no value unless the helper and imports change with it."

**4. Hidden complexity**

Yes, task 3.1 hides real complexity. `_deduct_items` does not mutate and return `pantry_map` entries directly; it collects `modified_ids`, then appends whatever comes back from `self.pantry_items.update(...)` at `pantry.py:358-362`. A naive `MagicMock` will return another mock, which can make the test pass on call assertions while failing to validate returned data.

There are two subtle branches here:
- The orphaned-FK skip test is easy: assert `update` was never called and the return list is `[]`.
- The control test is harder: if you assert on returned items, your side effect must return a real `PantryItemOut` with the updated quantity. Also, `modified_ids` is a `set`, so list order is not guaranteed if more than one item changes.

Verbatim recommendations:
- "In the orphaned-FK test, assert `service.pantry_items.update.assert_not_called()` and `result == []`; do not overbuild the mock harness for that case."
- "In the non-skip control test, make `pantry_items.update` return a real `PantryItemOut` carrying the new quantity, because `_deduct_items` appends the update return value rather than re-reading `pantry_map`."
- "Do not assert returned list order from `_deduct_items`; `modified_ids` is a set."
- "Hit the orphaned-FK branch by passing `original_unit_id` non-None while both `unit_obj` and `pantry_item.unit` are `None`; a merely unitless item will not exercise the same path."

Overall: the plan is architecturally sound. The main adjustments I'd make are reducing Phase 1 granularity, keeping the NamedTuple change atomic, and making task 3.1 explicitly account for `update()` return semantics rather than treating it as a trivial MagicMock setup.
</codex_response>

<changes_made>
Incorporated Codex feedback:

1. **Collapsed Phase 1 from 4 tasks → 3 tasks.** Merged the original 1.1 (relocate DraftPlanEntry) and 1.2 (create planner-diff.ts) into a single task 1.1 ("Extract shared DraftPlanEntry + create planner-diff.ts helper"). Per Codex: "Avoid a standalone task whose only effect is moving `DraftPlanEntry`; that move has no value unless the helper and imports change with it." Renumbered the refactor step to 1.2 and the test step to 1.3. `total_tasks` dropped from 10 → 7; `critical_path` metadata updated.

2. **Strengthened Phase 3 task 3.1 MagicMock harness.** Rewrote the harness to set `service.pantry_items.update.return_value = pantry.model_copy(update={"quantity": new_qty})` — a REAL `PantryItemOut`, not a Mock. Added explicit assertion `assert result[0].quantity == 2.0` to catch the subtle bug where `_deduct_items` appends `update()`'s return value (not the original pantry item). Added the explicit "do not assert list ordering" warning because `modified_ids` is a set. Tightened the orphaned-FK assertions to `assert_not_called()` and `result == []` per Codex's "do not overbuild" guidance. Also called out explicitly that the branch requires `original_unit_id` non-None with both units=None.

3. **Added UI-local framing note to task 1.1.** Per Codex: "keep `DraftPlanEntry` clearly UI-local and do not promote it into shared API types." Acceptance criteria now explicitly rejects adding the type to `frontend/app/lib/api/types/`.

4. **Kept `DeductionItem` as `DeductionItem` (non-underscore), NOT `_DeductionItem`.** Codex suggested a private underscore name. However, the spec's Phase 3 acceptance criterion explicitly requires "Tests import DeductionItem from mealie.services.optimizer.pantry (not from a private helper)" — underscore prefix is a privacy convention that would conflict. Keeping the public name honors the spec contract and the test import path; the plan-level tradeoff is recorded here in case a reviewer prefers the underscore form.

5. **Kept Phase 2 task 2.1 intact (atomic).** Codex explicitly validated: "Keep Phase 2 task 2.1 as one atomic refactor: introduce `_DeductionItem` and update every construction/destructure site in the same change." No change.

6. **Confirmed frontend test auto-discovery and stdlib-only dependencies.** No plan changes needed — Codex validated both.
</changes_made>
</review_notes>
