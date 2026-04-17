# Implementation Plan: Optimizer Polish — Diff Helper, DeductionItem, Test Coverage

Source: docs/plans/2026-04-17-041500-optimizer-polish-three-tasks.md
Revised: 2026-04-17

<plan_metadata>
  <feature>optimizer-polish-three-tasks</feature>
  <source>docs/plans/2026-04-17-041500-optimizer-polish-three-tasks.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>4</phases>
  <tasks>7</tasks>
  <status>revised</status>
  <critical_path>1.1 → 1.2 → 1.3; 2.1 → 3.1</critical_path>
</plan_metadata>

## Overview
Three small polish items in the optimizer fork: (1) centralize `DraftPlanEntry` diff logic behind a pure `draftEntryFieldsChanged` helper consumed by both `hasUnsavedChanges` and `savePlan()`; (2) replace the positional 4-tuple transport inside `PantryService._deduct_items` with a `DeductionItem` NamedTuple; (3) backfill unit/integration tests for three recently landed paths — `RepositoryGeneric.get_many()`, the `_deduct_items` orphaned-FK skip guard, and planner diff field sensitivity. All external behavior is preserved; this is refactor + tests only.

## Changes from Original

<revision_summary>
<change type="structural">
Removed the trailing `<review_notes>` / `<codex_response>` / `<changes_made>` block. Prior-review feedback is integrated inline into task bodies and acceptance criteria; no separate meta sections remain except this `Changes from Original` list (per rewriting rules).
</change>
<change type="structural">
Removed the redundant `<dependency_log>` section. Its content duplicated `<prerequisites>`; each prereq now carries a single authoritative verification line.
</change>
<change type="dependency">
Fixed hidden dependency: task 1.3 now declares `depends="1.2"` instead of `depends="1.1"`. The Phase 1 checkpoint's manual smoke test and the "existing tests are behavioral safety net" framing both assume the composable refactor (1.2) is complete before tests are added. Also purged stale "until 1.4" wording.
</change>
<change type="removed">
Dropped rollback blocks from tasks 1.2, 2.1, and 4.1. Per the rewriting rubric, rollback belongs only on high-risk operations; none of these tasks qualify (all are additive or single-file git-reversible edits). `git checkout -- <path>` remains the implicit fallback for any task if needed.
</change>
<change type="clarity">
Tightened acceptance criteria across every task: replaced subjective phrases ("still flips", "still partitions", "exercise three DISTINCT branches", "optional sanity check", "≥ 5 hits") with mechanical checks (named test cases, exact grep output, explicit counts, mandatory command invocations).
</change>
<change type="clarity">
Task 3.1: added MagicMock robustness note — if `RepositoryGeneric.update()` is invoked by keyword rather than positionally in a future refactor, `call_args.args[1]` will drift. Executor is instructed to verify via the already-existing positional call at `mealie/services/optimizer/pantry.py:361`, and to use `call_args[0]` / `call_args.kwargs` indexing defensively only if the plain `.args[1]` form fails.
</change>
<change type="clarity">
Task 1.1: restructured subtask order so the intermediate lint state is explicit — create + export the helper BEFORE deleting the inline interface, so `task ui:check` never sees a dangling reference. Exported `draftEntryFieldsChanged` does not need an importer to satisfy ESLint (helper is an exported public symbol, not a local unused binding).
</change>
<change type="clarity">
Renumbered open questions: Q2 was resolved during the prior revision; the remaining live questions are now `Q1` (notes field) and `Q2` (named-key repo choice, formerly Q3). Resolution history preserved in `<resolved_from_source>` with original IDs.
</change>
</revision_summary>

## Prerequisites

<prerequisites>
<prereq id="P1" type="library" verified="true">
  <description>vitest runner for frontend composable unit tests; auto-discovers co-located `*.test.ts`.</description>
  <verification>`frontend/app/composables/optimizer/scoring-engine.test.ts` and `use-expiration-helpers.test.ts` already run under `task ui:test`. `frontend/vitest.config.js` does not override `include`.</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>`typing.NamedTuple` (Python stdlib, 3.12).</description>
  <verification>Project stack per `CLAUDE.md`. No package dependency required.</verification>
</prereq>
<prereq id="P3" type="environment" verified="true">
  <description>PostgreSQL + migrations up for integration tests (Phase 4).</description>
  <verification>`task dev:services` + `task py:migrate`; `tests/integration_tests/test_repository_factory.py` already exercises the `session` fixture with this setup.</verification>
</prereq>
<prereq id="P4" type="data" verified="true">
  <description>Existing factories reused without modification: `_make_food`, `_make_unit`, `_make_pantry_item` in `tests/unit_tests/services_tests/test_pantry_service.py:14–67`; `random_string`, `random_email` in `tests/utils/factories`.</description>
  <verification>Read confirmed at those line ranges. `_make_unit` signature accepts `name`, `standard_unit`, `standard_quantity` kwargs.</verification>
</prereq>
<prereq id="P5" type="library" verified="true">
  <description>`get_repositories(session, group_id=..., household_id=...)` + per-tenant repo construction pattern.</description>
  <verification>Used at `tests/integration_tests/test_repository_factory.py:117, 121–122, 150, 154–155, 192, 219–220, 253, 280–281`.</verification>
</prereq>
<prereq id="P6" type="service" verified="true">
  <description>`RepositoryGeneric.get_many()` with empty-input short-circuit, IN() + tenant scoping, `override_schema`, and named-key support.</description>
  <verification>`mealie/repos/repository_generic.py:181–199`. Signature: `get_many(values, key=None, override_schema=None)`. Empty → `[]`; order NOT guaranteed; missing IDs silently excluded.</verification>
</prereq>
<prereq id="P7" type="service" verified="true">
  <description>Existing DB-less `PantryService` harness: `object.__new__(PantryService)` + manual `converter = UnitConverter()`.</description>
  <verification>`tests/unit_tests/services_tests/test_pantry_service.py:82–86`.</verification>
</prereq>
<prereq id="P8" type="library" verified="true">
  <description>`unittest.mock.MagicMock` for replacing `PantryService.pantry_items` in unit tests.</description>
  <verification>Stdlib. Used widely across the existing test suite.</verification>
</prereq>
</prerequisites>

## Phase 1: Frontend — Centralize Planner Diff

<phase id="1" name="Frontend — Centralize Planner Diff">

### 1.1 Relocate `DraftPlanEntry` to types.ts + create `planner-diff.ts`

<task id="1.1" status="pending" risk="low">
<context>
Today `DraftPlanEntry` is declared inline in `frontend/app/composables/optimizer/use-optimizer-planner.ts:10–22`. The new pure helper module must import this interface without creating a wrong-direction dependency (helper → stateful composable). The shared home is `frontend/app/composables/optimizer/types.ts` (47 lines today, already owns `RecipeFoodData`, `ScoredRecipe`, `ScoringWeights`, `PantryItemScoring`). That file currently has NO imports.

`DraftPlanEntry` is UI-local state, not an API contract: do NOT add it to `frontend/app/lib/api/types/`.

This task is atomic — the type relocation and the new helper are tightly coupled (moving the type alone has no consumer; the helper alone has no type). Prior Codex review explicitly validated combining these: "Avoid a standalone task whose only effect is moving DraftPlanEntry; that move has no value unless the helper and imports change with it."

Field list to preserve verbatim (11 fields, declaration order):
`localId: string`, `date: string`, `entryType: PlanEntryType`, `order: number`, `recipeId: string | null`, `recipeName: string | null`, `recipeSlug: string | null`, `existingEntryId: number | null`, `groupId: string | null`, `userId: string | null`, `householdId: string | null`.

Subtask ordering matters: create `planner-diff.ts` FIRST (depends only on the moved type), then add the type to `types.ts`, then update the composable's import and delete the old inline declaration. This keeps the intermediate state lint-clean.

Module hygiene for `planner-diff.ts`:
- NO Vue / Nuxt / composable imports.
- Exactly ONE import: `import type { DraftPlanEntry } from "./types";`.
- Export `DRAFT_PAYLOAD_FIELDS = ["recipeId", "entryType", "date"] as const;` (readonly tuple so call sites can iterate).
- Export `function draftEntryFieldsChanged(a: DraftPlanEntry, b: DraftPlanEntry): boolean`. Implementation iterates `DRAFT_PAYLOAD_FIELDS` and returns `true` on the first inequality, else `false`. Do NOT hard-code the field names inside the function body — iterate the exported tuple so it stays the single source of truth.

The helper intentionally does NOT compare: `existingEntryId` (identity, not payload), `localId` (client-only), `order` (ordering concern), `groupId`/`userId`/`householdId` (server-assigned bookkeeping), `recipeName`/`recipeSlug` (denormalized display state that mirrors `recipeId`).
</context>

<subtasks>
- [ ] Append `DraftPlanEntry` + PlanEntryType import to `types.ts`. Open `frontend/app/composables/optimizer/types.ts`, add `import type { PlanEntryType } from "~/lib/api/types/meal-plan";` as the first line, then append the `export interface DraftPlanEntry { ... }` block with the 11 fields above in declaration order at the end of the file.
- [ ] Create `frontend/app/composables/optimizer/planner-diff.ts` with a single type-only import (`import type { DraftPlanEntry } from "./types";`), an exported `DRAFT_PAYLOAD_FIELDS = ["recipeId", "entryType", "date"] as const;` tuple, and an exported `draftEntryFieldsChanged(a, b)` function that iterates the tuple and returns `true` on first field inequality.
- [ ] Update `frontend/app/composables/optimizer/use-optimizer-planner.ts`: change the `./types` import on line 5 to include `DraftPlanEntry`, i.e. `import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring, DraftPlanEntry } from "./types";`. Then delete the `export interface DraftPlanEntry { ... }` block at lines 10–22.
- [ ] Run `task ui:check`. The composable's inline `recipeId !==` / `entryType !==` / `date !==` comparisons are expected to REMAIN at this point (removed in task 1.2) and must still type-check.
</subtasks>

<acceptance>
- `task ui:check` (lint + type-check) passes.
- `grep -rn "interface DraftPlanEntry" frontend/app` returns exactly one line, matching `frontend/app/composables/optimizer/types.ts`.
- `grep -rn "interface DraftPlanEntry" frontend/app/lib/api` returns zero lines (confirms UI-local placement — NOT in shared API types).
- `grep -n "^export " frontend/app/composables/optimizer/planner-diff.ts` returns exactly two lines: one for `DRAFT_PAYLOAD_FIELDS` and one for `draftEntryFieldsChanged`.
- `grep -c "^import" frontend/app/composables/optimizer/planner-diff.ts` returns `1`.
</acceptance>
</task>

### 1.2 Refactor `use-optimizer-planner.ts` call sites to use the helper

<task id="1.2" status="pending" depends="1.1" risk="medium">
<context>
Two call sites in `frontend/app/composables/optimizer/use-optimizer-planner.ts` currently duplicate the field-by-field equality. Both sites KEEP their identity/length concerns inline because `draftEntryFieldsChanged` explicitly excludes those:

Call site 1 — `hasUnsavedChanges` computed at lines 113–131. Current inline logic:
```ts
if (draftArr.length !== snapArr.length) return true;           // KEEP (length)
for (let i = 0; i < draftArr.length; i++) {
  if (draftArr[i].recipeId !== snapArr[i].recipeId) return true;            // REPLACE
  if (draftArr[i].existingEntryId !== snapArr[i].existingEntryId) return true;  // KEEP (identity)
  if (draftArr[i].entryType !== snapArr[i].entryType) return true;          // REPLACE
  if (draftArr[i].date !== snapArr[i].date) return true;                    // REPLACE
}
```
The three REPLACE lines collapse into a single `if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;`. The `existingEntryId` check MUST stay inline — after a save, the snapshot is rebuilt with fresh `existingEntryId` values, so absorbing that field into the helper would make `hasUnsavedChanges` forever-true until page refresh.

Call site 2 — `savePlan()` update-branch predicate at lines 395–399:
```ts
if (snapEntry && (
  snapEntry.recipeId !== draftEntry.recipeId
  || snapEntry.entryType !== draftEntry.entryType
  || snapEntry.date !== draftEntry.date
)) {
  toUpdate.push({ id: draftEntry.existingEntryId, payload: { ... } });
}
```
Collapses to `if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry)) { ... }`. The `toUpdate.push(...)` payload is unchanged.

New import goes at the top of the file (below the existing `./types` import on line 5): `import { draftEntryFieldsChanged } from "./planner-diff";`. Do NOT re-export it from the composable.
</context>

<subtasks>
- [ ] Add `import { draftEntryFieldsChanged } from "./planner-diff";` immediately after the existing `./types` import at line 5.
- [ ] In `hasUnsavedChanges` (lines 113–131), replace the three lines at 124 (`recipeId !==`), 126 (`entryType !==`), and 127 (`date !==`) with a single `if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;`. Keep line 122 (`draftArr.length !== snapArr.length`) and line 125 (`existingEntryId !==`) UNCHANGED.
- [ ] In `savePlan()`, replace the compound `&&`-chained predicate at lines 395–399 with `if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry)) {` — the inner `toUpdate.push(...)` body at lines 400–410 is unchanged.
- [ ] Run `task ui:check` and `task ui:test`. The existing optimizer-planner test suite is the behavioral safety net for this refactor; direct helper tests are added in task 1.3.
</subtasks>

<acceptance>
- `grep -En "recipeId !==|entryType !==|date !==" frontend/app/composables/optimizer/use-optimizer-planner.ts` returns zero lines.
- `grep -n "draftEntryFieldsChanged" frontend/app/composables/optimizer/use-optimizer-planner.ts` returns exactly 3 lines: 1 import + 1 call in `hasUnsavedChanges` + 1 call in `savePlan`.
- `grep -n "existingEntryId !==" frontend/app/composables/optimizer/use-optimizer-planner.ts` still returns the inline identity check in `hasUnsavedChanges`.
- `task ui:check` passes.
- `task ui:test` passes (no new failures in existing suites).
</acceptance>
</task>

### 1.3 Add `planner-diff.test.ts` coverage

<task id="1.3" status="pending" depends="1.2" risk="low">
<context>
Create `frontend/app/composables/optimizer/planner-diff.test.ts` following the shape of the existing `use-expiration-helpers.test.ts` (top-level factory, `describe` per helper, `it` per case). Do NOT import from `use-optimizer-planner.ts` — the test targets the pure helper directly.

Test the six payload-sensitivity cases plus one tuple-contract assertion (seven total cases). Use a local `makeEntry(overrides: Partial<DraftPlanEntry> = {}): DraftPlanEntry` factory filling all 11 fields with deterministic literals — no `crypto.randomUUID()` so tests are fast and reproducible.

Cases:
1. `draftEntryFieldsChanged` — identical entries returns `false`.
2. `draftEntryFieldsChanged` — `recipeId` differs (including `null → "abc"`) returns `true`.
3. `draftEntryFieldsChanged` — `entryType` differs (`"breakfast"` vs `"dinner"`) returns `true`.
4. `draftEntryFieldsChanged` — `date` differs returns `true`.
5. `draftEntryFieldsChanged` — only `existingEntryId` differs returns `false` (identity, not payload).
6. `draftEntryFieldsChanged` — only `localId` OR `order` OR `recipeName` OR `recipeSlug` differs returns `false` (display/bookkeeping-only).
7. `DRAFT_PAYLOAD_FIELDS` tuple equals `["recipeId", "entryType", "date"]` (pins the semantic contract).

This task depends on 1.2 (not just 1.1) because the Phase 1 checkpoint's manual smoke test exercises the fully refactored composable.
</context>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/planner-diff.test.ts` with imports: `import { describe, it, expect } from "vitest";`, `import { draftEntryFieldsChanged, DRAFT_PAYLOAD_FIELDS } from "./planner-diff";`, `import type { DraftPlanEntry } from "./types";`.
- [ ] Implement a module-level `makeEntry(overrides: Partial<DraftPlanEntry> = {}): DraftPlanEntry` factory with deterministic literal defaults for all 11 fields.
- [ ] Write `describe("draftEntryFieldsChanged", ...)` block containing the 6 named `it(...)` cases above.
- [ ] Write a second `describe("DRAFT_PAYLOAD_FIELDS", ...)` block with one `it("exports the three payload-only field names", ...)` asserting `expect(DRAFT_PAYLOAD_FIELDS).toEqual(["recipeId", "entryType", "date"])`.
- [ ] Run `task ui:test` and confirm the new file is discovered and all 7 cases pass.
</subtasks>

<acceptance>
- `task ui:test` output lists all 7 named cases passing under the two `describe` blocks (6 `draftEntryFieldsChanged` + 1 `DRAFT_PAYLOAD_FIELDS`).
- `grep -n "use-optimizer-planner" frontend/app/composables/optimizer/planner-diff.test.ts` returns zero lines (no dependency on the stateful composable).
- `ls frontend/app/composables/optimizer/planner-diff.test.ts` returns a matching path (file exists).
- `task ui:check` passes (no lint violations in the new test file).
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `task ui:check` passes.
- [ ] `task ui:test` passes.
- [ ] `grep -rn "interface DraftPlanEntry" frontend/app` returns exactly one line (in `types.ts`).
- [ ] Manual smoke at `http://localhost:3000/g/{group}/optimizer/planner`: drag a recipe into a slot, confirm the unsaved-changes indicator appears; click Save, confirm indicator clears.
</verification>
<gate>Frontend type-checks cleanly, all tests green, diff logic lives in ONE place and is exercised by named test cases. Safe to proceed to Phase 2.</gate>
</checkpoint>

</phase>

## Phase 2: Backend — DeductionItem NamedTuple

<phase id="2" name="Backend — Type _deduct_items Transport">

### 2.1 Introduce `DeductionItem` and migrate all three sites atomically

<task id="2.1" status="pending" risk="medium">
<context>
Replace `list[tuple[UUID4, float, object | None, UUID4 | None]]` with `list[DeductionItem]` at all three touch points in `mealie/services/optimizer/pantry.py`:

1. The parameter annotation on `_deduct_items` at line 313.
2. The tuple construction in `deduct_recipe` at line 377.
3. The tuple construction in `deduct_shopping_items` at line 396.

`DeductionItem` is a module-level `typing.NamedTuple` declared BEFORE `class PantryService:` (around line 22, after the existing `_unit_converter = UnitConverter()` line at 21) so class-body annotations can reference it without forward-reference gymnastics. NamedTuple preserves positional destructuring — the existing loop at line 324 (`for food_id, qty, unit_obj, original_unit_id in items:`) binds correctly with zero body changes because NamedTuple iteration order matches field-declaration order.

Declaration:
```python
class DeductionItem(NamedTuple):
    food_id: UUID4
    quantity: float
    unit_obj: object | None          # resolved IngredientUnit (or None)
    original_unit_id: UUID4 | None   # raw FK column; non-None with unit_obj=None implies orphaned FK
```

Update the `typing` import on line 4 from `from typing import TYPE_CHECKING` to `from typing import NamedTuple, TYPE_CHECKING` (line 4 is today the only `from typing` line, so a single combined import is cleanest).

Also type the local variables at the two construction sites:
- Line 371 `food_qty_units = []` → `food_qty_units: list[DeductionItem] = []`.
- Line 390 `food_qty_units = []` → `food_qty_units: list[DeductionItem] = []`.

`DeductionItem` is public (no underscore prefix) so Phase 3 tests can import it via `from mealie.services.optimizer.pantry import DeductionItem`. This is required by the Phase 3 acceptance contract.

The `_deduct_items` body (lines 319–363) is UNCHANGED. This is purely a transport-type refactor; behavior is preserved.
</context>

<subtasks>
- [ ] Change `mealie/services/optimizer/pantry.py` line 4 from `from typing import TYPE_CHECKING` to `from typing import NamedTuple, TYPE_CHECKING`.
- [ ] Insert the `class DeductionItem(NamedTuple): ...` block (with the four annotated fields above) after line 21 (`_unit_converter = UnitConverter()`) and before line 24 (`class PantryService:`).
- [ ] Replace line 313 `food_qty_units: list[tuple[UUID4, float, object | None, UUID4 | None]],` with `food_qty_units: list[DeductionItem],`.
- [ ] Replace line 371 `food_qty_units = []` with `food_qty_units: list[DeductionItem] = []`.
- [ ] Replace line 377 `food_qty_units.append((ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))` with `food_qty_units.append(DeductionItem(ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))`.
- [ ] Replace line 390 `food_qty_units = []` with `food_qty_units: list[DeductionItem] = []`.
- [ ] Replace line 396 `food_qty_units.append((item.food_id, item.quantity or 0, unit_obj, original_unit_id))` with `food_qty_units.append(DeductionItem(item.food_id, item.quantity or 0, unit_obj, original_unit_id))`.
- [ ] Confirm line 324 (`for food_id, qty, unit_obj, original_unit_id in items:`) is UNCHANGED — do not rewrite to attribute access.
- [ ] Run `task py:check`.
- [ ] Run `task py:test -- -k pantry_service` and confirm all pre-existing cases pass.
</subtasks>

<acceptance>
- `grep -n "tuple\[UUID4, float" mealie/services/optimizer/pantry.py` returns zero lines.
- `grep -c "DeductionItem" mealie/services/optimizer/pantry.py` returns exactly `6`. Expected matching lines: `class DeductionItem(NamedTuple):`, the `food_qty_units: list[DeductionItem],` parameter annotation (line 313), the two `food_qty_units: list[DeductionItem] = []` local annotations (lines 371, 390), and the two `food_qty_units.append(DeductionItem(...))` constructor calls (lines 377, 396).
- `task py:check` passes.
- `task py:test -- -k pantry_service` passes with zero regressions from the pre-existing `CalculateDeficitTests` class.
- `python -c "from mealie.services.optimizer.pantry import DeductionItem; print(DeductionItem._fields)"` prints `('food_id', 'quantity', 'unit_obj', 'original_unit_id')` — confirms the public import path and field order that Phase 3 relies on.
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task py:check` passes.
- [ ] `task py:test -- -k pantry_service` passes.
- [ ] `grep -c "DeductionItem" mealie/services/optimizer/pantry.py` returns `6` (class decl + 1 parameter annotation + 2 list-type annotations + 2 constructor calls).
- [ ] `grep -n "tuple\[UUID4" mealie/services/optimizer/pantry.py` returns zero lines.
</verification>
<gate>Transport type migrated with zero behavioral change; public signatures of `deduct_recipe` / `deduct_shopping_items` unchanged; `DeductionItem` publicly importable. Safe to proceed to Phase 3.</gate>
</checkpoint>

</phase>

## Phase 3: Backend Tests — Pantry Orphaned-FK Guard

<phase id="3" name="Backend Tests — PantryService Orphaned-FK Guard" depends="2">

### 3.1 Add `DeductItemsOrphanedFKTests` class (three tests)

<task id="3.1" status="pending" depends="2.1" risk="low">
<context>
Append a new test class `DeductItemsOrphanedFKTests` to `tests/unit_tests/services_tests/test_pantry_service.py` that exercises three distinct skip/deduct branches in `_deduct_items` at `mealie/services/optimizer/pantry.py:335–349`.

Critical harness detail: `_deduct_items` does NOT re-read from `pantry_map` after the update — it appends whatever `self.pantry_items.update(pantry_id, data_dict)` RETURNS (see pantry.py:361–362). A naive `MagicMock()` returns another `Mock`, which makes `update.call_count == 1` pass but leaves returned-list assertions worthless. Therefore `update.return_value` MUST be a real `PantryItemOut` carrying the new quantity (use `pantry.model_copy(update={"quantity": new_qty})`).

Also: `modified_ids` is a `set` at line 322, so with multi-item updates the output list order is NOT guaranteed. These tests use single-item inputs to sidestep ordering entirely.

Call-args indexing: at `pantry.py:361` the call is positional: `self.pantry_items.update(pantry_item.id, {"quantity": running_qty[food_id]})`. So `update.call_args.args[0]` is the pantry id and `update.call_args.args[1]` is the `{"quantity": ...}` dict. If a future refactor changes the call to keyword form, the indexing must switch to `call_args.kwargs["data"]` or similar — prefer the `.args`-based form here since it matches the current code.

Three tests, all asserting on observable behavior (return value shape, `update.call_count`, `update.call_args`) — never on `DeductionItem` internal shape.

1. **test_orphaned_fk_skips_deduction** (Branch A1)
   Source `DeductionItem` has `unit_obj=None` but `original_unit_id = uuid4()` (FK column populated — shopping item had a unit reference now orphaned). Pantry item has `unit=None`. At pantry.py:335 both unit IDs are None; inner guard at 336–337 sees `original_unit_id is not None` and `continue`s.
   Expected: `result == []` and `service.pantry_items.update.assert_not_called()`.

2. **test_both_genuinely_unitless_deducts** (Branch A2, control)
   Source `DeductionItem` has `unit_obj=None` AND `original_unit_id=None`. Pantry item has `unit=None`. Guard at 336–337 evaluates False, `converted_qty = qty` (line 338), deduction proceeds.
   Expected: `len(result) == 1`, `result[0].quantity == 2.0` (the stubbed `model_copy(update={"quantity": 2.0})` return — confirms `_deduct_items` appends `update`'s return value, not the original pantry item), `update.call_count == 1`, `update.call_args.args[1]["quantity"] == 2.0`. (Arithmetic: `max(0.0, round(5.0 - 3.0, 4)) == 2.0`.)

3. **test_source_has_unit_pantry_unitless_skips** (Branch C fall-through)
   Source `DeductionItem` has a resolved `unit_obj` (e.g., `_make_unit(name="cup", standard_unit="cup")`) and `original_unit_id = source_unit.id`. Pantry item has `unit=None`. Because `source_unit_id != pantry_unit_id`, control falls to the `else` arm at pantry.py:341. Since `pantry_item.unit is None`, `pantry_standard is None`, so the guard at line 344 fails and line 348–349 `continue`s. A DISTINCT skip path from Branch A1.
   Expected: `result == []` and `service.pantry_items.update.assert_not_called()`.

Harness (class method):
```python
from unittest.mock import MagicMock

def _service(self, pantry: PantryItemOut, new_qty: float) -> PantryService:
    service = object.__new__(PantryService)
    service.converter = UnitConverter()
    service.pantry_items = MagicMock()
    service.pantry_items.update.return_value = pantry.model_copy(update={"quantity": new_qty})
    return service
```
</context>

<subtasks>
- [ ] At the top of `tests/unit_tests/services_tests/test_pantry_service.py`, add `from unittest.mock import MagicMock`, `from mealie.services.optimizer.pantry import DeductionItem`, and (if not already present via `from uuid import uuid4` on line 1 — it is) reuse `uuid4`. Also add `from mealie.services.parser_services.parser_utils import UnitConverter` at module scope if not already top-level (note: `CalculateDeficitTests._calculate` imports it inside the method at line 83; prefer a single top-level import for reuse).
- [ ] Append `class DeductItemsOrphanedFKTests:` after the last existing test class. Implement `_service(self, pantry, new_qty)` per the harness in `<context>`.
- [ ] Implement `test_orphaned_fk_skips_deduction`:
    - `food = _make_food()`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=5.0)` (new_qty is sentinel — `update` must never be called).
    - `items = [DeductionItem(food.id, 3.0, None, uuid4())]`.
    - `result = service._deduct_items(items, {food.id: pantry})`.
    - `assert result == []`; `service.pantry_items.update.assert_not_called()`.
- [ ] Implement `test_both_genuinely_unitless_deducts`:
    - `food = _make_food()`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=2.0)`.
    - `items = [DeductionItem(food.id, 3.0, None, None)]`.
    - `result = service._deduct_items(items, {food.id: pantry})`.
    - `assert len(result) == 1`; `assert result[0].quantity == 2.0`; `assert service.pantry_items.update.call_count == 1`; `assert service.pantry_items.update.call_args.args[1]["quantity"] == 2.0`.
- [ ] Implement `test_source_has_unit_pantry_unitless_skips`:
    - `food = _make_food()`; `source_unit = _make_unit(name="cup", standard_unit="cup")`; `pantry = _make_pantry_item(food, quantity=5.0, unit=None)`.
    - `service = self._service(pantry, new_qty=5.0)` (sentinel).
    - `items = [DeductionItem(food.id, 3.0, source_unit, source_unit.id)]`.
    - `result = service._deduct_items(items, {food.id: pantry})`.
    - `assert result == []`; `service.pantry_items.update.assert_not_called()`.
- [ ] Run `task py:test -- -k DeductItemsOrphanedFK` and confirm all 3 named tests pass.
</subtasks>

<acceptance>
- `task py:test -- -k DeductItemsOrphanedFK` output shows 3 passing test names: `test_orphaned_fk_skips_deduction`, `test_both_genuinely_unitless_deducts`, `test_source_has_unit_pantry_unitless_skips`.
- `grep -n "from mealie.services.optimizer.pantry import DeductionItem" tests/unit_tests/services_tests/test_pantry_service.py` returns exactly one line (public import path, not an underscore-prefixed internal).
- `grep -En "DeductionItem\._fields|DeductionItem\.food_id" tests/unit_tests/services_tests/test_pantry_service.py` returns zero lines (tests never inspect `DeductionItem` internals — decoupled from transport representation).
- `grep -cn "assert_not_called\(\)" tests/unit_tests/services_tests/test_pantry_service.py` returns ≥ 2 (the two skip-path tests each assert `update.assert_not_called()`).
- `task py:test -- -k pantry_service` passes (existing `CalculateDeficitTests` suite + new `DeductItemsOrphanedFKTests` suite all green).
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `task py:test -- -k pantry_service` passes end-to-end.
- [ ] The three named tests appear in test output: `test_orphaned_fk_skips_deduction`, `test_both_genuinely_unitless_deducts`, `test_source_has_unit_pantry_unitless_skips`.
- [ ] Branch coverage: the orphaned-FK skip (line 337), both-unitless deduct (line 338), and source-has-unit / pantry-unitless skip (line 349) are each exercised by at least one named test.
</verification>
<gate>Three distinct branches at pantry.py:335–349 are pinned down by behavioral tests. Safe to proceed to Phase 4 (parallel-independent phase; no dependency gate beyond this).</gate>
</checkpoint>

</phase>

## Phase 4: Backend Tests — RepositoryGeneric.get_many() Coverage

<phase id="4" name="Backend Tests — get_many Coverage">

### 4.1 Add 5 `get_many` tests to test_repository_factory.py

<task id="4.1" status="pending" risk="low">
<context>
Append five new module-level test functions to `tests/integration_tests/test_repository_factory.py` (the file uses top-level `def test_...` functions, not a class — match that convention). All five use the `session: Session` fixture plus the existing `get_repositories(session, group_id=..., household_id=...)` construction pattern at lines 117, 121–122, 150, 154–155, 192, 219–220, 253, 280–281.

Assertions use SET equality where order doesn't matter, honoring the documented "order is NOT guaranteed" contract at `mealie/repos/repository_generic.py:189`.

Note: this task adds five tests across three behavioral dimensions (empty/batch/missing, tenant scoping, named-key lookup). Codex flagged it as the most compound task in the plan; keeping it as one task because the tests share setup helpers (`get_repositories`, `SaveIngredientFood`, `Recipe`) and because splitting them creates five near-identical task shells. Execute subtasks in order; if any single test gets stuck, land the others first and loop back.

1. **test_get_many_empty_input_returns_empty_list** — `values=[]` short-circuits. Use `unfiltered_repos = get_repositories(session, group_id=None, household_id=None)`; assert `unfiltered_repos.ingredient_foods.get_many([]) == []`.

2. **test_get_many_returns_all_matching_ids** — Create a group + per-group repos; seed 3 `SaveIngredientFood` records with distinct `id=uuid4()` and `name=random_string()`; request all 3 by PK; assert `{r.id for r in result} == {f1.id, f2.id, f3.id}` (set equality).

3. **test_get_many_silently_excludes_missing_ids** — Seed 2 foods; call `get_many([existing1.id, existing2.id, uuid4(), uuid4()])`; assert `len(result) == 2` AND `{r.id for r in result} == {existing1.id, existing2.id}`; confirm no exception was raised.

4. **test_get_many_respects_tenant_scoping** — Mirror the setup at lines 116–144 (`test_group_repositories_filter_by_group`):
    - Create `group_1`, `group_2` via `unfiltered_repos.groups.create(...)`.
    - Build `group_1_repos` and `group_2_repos` via `get_repositories(session, group_id=..., household_id=None)`.
    - Seed `food_1` in group_1 (`SaveIngredientFood(id=uuid4(), group_id=group_1.id, name=random_string())`) and `food_2` in group_2.
    - Request BOTH ids from `group_1_repos.ingredient_foods.get_many([food_1.id, food_2.id])`; assert result contains ONLY food_1.
    - Symmetrically, from `group_2_repos.ingredient_foods.get_many([food_1.id, food_2.id])`; assert result contains ONLY food_2.
    - Also verify `unfiltered_repos.ingredient_foods.get_many([food_1.id, food_2.id])` returns BOTH (set equality).

5. **test_get_many_supports_named_key** — Mirror the setup at lines 189–247 (`test_recipe_repo_filter_by_household_with_proxy`). Recipe.slug is the alt-key column.
    - Create group, 2 households, 2 users, 2 recipes (one in each household).
    - From `household_1_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")`, assert result contains ONLY `recipe_1` (household scoping applies — verified via `_filter_builder()` at repository_generic.py:197).
    - From `unfiltered_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")`, assert set equality on both recipes' IDs.

No new fixtures; no invented test-only models.
</context>

<subtasks>
- [ ] Open `tests/integration_tests/test_repository_factory.py`; confirm existing imports cover what we need (`uuid4`, `Session`, `get_repositories`, `SaveIngredientFood`, `Recipe`, `random_email`, `random_string`). No new imports required.
- [ ] Append `def test_get_many_empty_input_returns_empty_list(session: Session):` — construct `unfiltered_repos`, assert `get_many([]) == []`.
- [ ] Append `def test_get_many_returns_all_matching_ids(session: Session):` — create group + group_repos, seed 3 foods via `group_repos.ingredient_foods.create(SaveIngredientFood(...))` (mirror pattern at line 123), call `group_repos.ingredient_foods.get_many([f1.id, f2.id, f3.id])`, assert set equality of `{r.id for r in result}`.
- [ ] Append `def test_get_many_silently_excludes_missing_ids(session: Session):` — seed 2 foods, mix in 2 random UUIDs, assert `len(result) == 2` + set equality on IDs, no exception.
- [ ] Append `def test_get_many_respects_tenant_scoping(session: Session):` — clone the two-group setup at lines 116–128, invoke `get_many` from both per-group repos and the unfiltered repo, assert three-direction isolation (group_1 sees only food_1, group_2 sees only food_2, unfiltered sees both).
- [ ] Append `def test_get_many_supports_named_key(session: Session):` — clone the recipe + 2-household + 2-user setup at lines 189–234. Call `household_1_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")` and assert only recipe_1 is returned; then call `unfiltered_repos.recipes.get_many([recipe_1.slug, recipe_2.slug], key="slug")` and assert both returned (set equality).
- [ ] Run `task py:test -- -k get_many` and confirm all 5 named tests pass.
- [ ] Run `task py:test -- tests/integration_tests/test_repository_factory.py` and confirm zero regressions in pre-existing tests.
</subtasks>

<acceptance>
- `task py:test -- -k get_many` output shows 5 passing test names: `test_get_many_empty_input_returns_empty_list`, `test_get_many_returns_all_matching_ids`, `test_get_many_silently_excludes_missing_ids`, `test_get_many_respects_tenant_scoping`, `test_get_many_supports_named_key`.
- `grep -n "def test_get_many" tests/integration_tests/test_repository_factory.py` returns exactly 5 lines.
- `grep -n "key=\"slug\"" tests/integration_tests/test_repository_factory.py` returns at least one line in the named-key test (confirms named-key parameter is used).
- `grep -En "assert \[.*\] ==" tests/integration_tests/test_repository_factory.py | grep -i get_many` returns zero lines for the new tests — confirms NO list-equality assertions on `get_many` output (order is not guaranteed; tests must use set equality).
- `task py:test -- tests/integration_tests/test_repository_factory.py` passes end-to-end.
- `task py:check` passes.
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task py:test -- -k get_many` passes (5 new tests).
- [ ] `task py:test -- tests/integration_tests/test_repository_factory.py` passes (full file).
- [ ] `task py:check` passes (no lint violations in the new test code).
</verification>
<gate>`get_many()` contract — empty-input short-circuit, batch fetch, missing-ID exclusion, tenant scoping, named-key lookup — is locked down by named tests using set equality. Plan complete.</gate>
</checkpoint>

</phase>

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="medium">
  <description>Task 1.2 accidentally removes the inline `existingEntryId` identity check, causing `hasUnsavedChanges` to return true forever after a save (snapshot is rebuilt with fresh IDs).</description>
  <mitigation>Task 1.2 subtasks explicitly call out keeping line 125 UNCHANGED. Acceptance criterion uses `grep -n "existingEntryId !==" ...` to verify the inline check still exists.</mitigation>
  <detection>Phase 1 manual smoke test: after Save, the unsaved-changes indicator should clear. If it stays lit, the identity check was removed.</detection>
</risk>
<risk id="R2" likelihood="low" impact="medium">
  <description>Task 3.1 MagicMock stub returns a bare `Mock` instead of a `PantryItemOut`, masking the fact that `_deduct_items` appends the `update()` return value rather than the original pantry item.</description>
  <mitigation>Harness explicitly sets `pantry_items.update.return_value = pantry.model_copy(update={"quantity": new_qty})` — a real `PantryItemOut`. The control test asserts `result[0].quantity == 2.0` specifically to detect this.</mitigation>
  <detection>If the control test passes with `result[0]` being a `Mock`, the assertion `result[0].quantity == 2.0` fails (a `Mock.quantity` is a `Mock`, not `2.0`).</detection>
</risk>
<risk id="R3" likelihood="low" impact="low">
  <description>Task 2.1's `NamedTuple` migration breaks the `for food_id, qty, unit_obj, original_unit_id in items:` destructure at pantry.py:324.</description>
  <mitigation>`typing.NamedTuple` iteration order matches field-declaration order, so positional unpack binds identically to a tuple. Existing `CalculateDeficitTests` suite is the regression detector.</mitigation>
  <detection>`task py:test -- -k pantry_service` fails with a `TypeError` or wrong-value assertion if iteration order diverges.</detection>
</risk>
<risk id="R4" likelihood="low" impact="low">
  <description>Task 4.1 tenant-scope or named-key test assumes `_filter_builder()` applies at the `get_many` level; if the repository's `get_many` bypassed tenant scoping, the test would pass trivially.</description>
  <mitigation>Acceptance requires BOTH-direction isolation assertions (group_1 excludes food_2 AND group_2 excludes food_1), plus an unfiltered-repo control that proves the IDs are queryable at all. Named-key test uses the same two-pronged approach.</mitigation>
  <detection>If both per-group repos return both foods, the tenant-scope assertion fails immediately.</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] `task py:check` passes (whole repo).
- [ ] `task ui:check` passes (whole frontend).
- [ ] `task py:test` passes (full Python suite).
- [ ] `task ui:test` passes (full frontend suite).
- [ ] `git status` shows changes only in this allowlist: `frontend/app/composables/optimizer/types.ts`, `frontend/app/composables/optimizer/use-optimizer-planner.ts`, `frontend/app/composables/optimizer/planner-diff.ts` (new), `frontend/app/composables/optimizer/planner-diff.test.ts` (new), `mealie/services/optimizer/pantry.py`, `tests/unit_tests/services_tests/test_pantry_service.py`, `tests/integration_tests/test_repository_factory.py`.
- [ ] `CLAUDE.md` "Modified Upstream Files" list is UNCHANGED (no new upstream edits introduced — all changes are inside the allowed optimizer + test roots).
- [ ] Manual smoke at `http://localhost:3000/g/{group}/optimizer/planner`: add/modify/remove a slot, confirm unsaved-changes indicator flips correctly, Save persists, indicator clears.
</verification>
<acceptance>All three spec items landed: planner diff centralized behind one helper + covered by named tests; `DeductionItem` NamedTuple replaces the 4-tuple with zero behavioral change; three new code paths (`get_many`, orphaned-FK skip, planner diff) have direct test coverage. No new upstream edits; fork-isolation rules preserved.</acceptance>
</final_validation>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md">
  <question>Should `draftEntryFieldsChanged` also compare an as-yet-unused `notes` field that exists on `ReadPlanEntry` but not on `DraftPlanEntry` today?</question>
  <default_assumption>No — `DraftPlanEntry` does not carry `notes` today. Adding it is out of scope and would violate the "non-goals" constraint. If a future feature adds `notes` to `DraftPlanEntry`, update `DRAFT_PAYLOAD_FIELDS` in the same PR.</default_assumption>
  <impact>If added later, callers pick up automatic sensitivity to notes changes without updating their own diff logic. No impact on this plan.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/specs/2026-04-17-035809-optimizer-polish-three-tasks.md">
  <question>For `get_many` tenant-scope tests, which repository to use (ingredient_foods, webhooks, shopping_lists, recipes)?</question>
  <default_assumption>Mirror existing file conventions: use `ingredient_foods` for the group-scope case (matches lines 116–144) and `recipes` for the named-key case (matches slug assertions at 237–244). Webhooks would work but require more setup without adding coverage value.</default_assumption>
  <impact>Choice of repo affects setup boilerplate. Plan execution proceeds under default assumption unless overridden.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/plans/2026-04-17-041500-optimizer-polish-three-tasks.md">
<resolved original_question="Q2: Should the orphaned-FK test also exercise the non-guarded control case (source has valid unit_obj but pantry unit is None) to lock down the trio of branches at pantry.py:335–349?" original_id="Q2">
  <resolution>Yes (user confirmed during prior plan review). Task 3.1 ships three tests covering Branch A1 (orphaned-FK skip), Branch A2 (both-unitless deduct), and Branch C (source-has-unit / pantry-unitless fall-through skip). Phase 3 checkpoint and acceptance criteria reflect this. Original Q3 (named-key repo choice) is now Q2 in the revised numbering.</resolution>
</resolved>
</resolved_from_source>
