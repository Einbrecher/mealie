# Implementation Plan: Slot Overlap Penalty Persistence

Source: docs/plans/2026-04-14-173824-slot-overlap-penalty-persistence.md
Revised: 2026-04-14

<plan_metadata>
  <feature>Persist slotOverlapPenalty scoring weight to backend optimizer_config table</feature>
  <source>docs/plans/2026-04-14-173824-slot-overlap-penalty-persistence.md</source>
  <revision_scope>light</revision_scope>
  <phases>3</phases>
  <tasks>7</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

The optimizer_config table currently persists 6 scoring weights through a standard column->model->schema->TS-type->composable pipeline. The `slotOverlapPenalty` weight bypasses this pipeline -- it uses a client-side-only variable (`currentSlotPenalty` in `use-optimizer-planner.ts`), a separate prop/emit path on `ConfigPanel.vue`, and a separate ref in `planner.vue`. This means the Complement Contrast slider value is lost on page reload. This plan adds the column to the database and removes the client-side workaround so all 7 sliders follow the identical persist-and-reload path.

## Changes from Original

<revision_summary>
<change type="dependency">
  Fixed critical path: tasks 2.2 and 2.3 are independent (both depend only on 2.1). Changed from serial 2.1->2.2->2.3->2.4 to parallel 2.1->{2.2||2.3}->2.4. This is important because executing them serially creates a broken intermediate state (e.g. ConfigPanel emitting events to a deleted composable function).
</change>
<change type="clarity">
  Corrected line number references verified against actual source: optimizer.ts ratingWeight is at line 94 (was cited as 95); ConfigPanel.vue onSlotPenaltyChange spans lines 163-168 (was cited as 163-167).
</change>
<change type="clarity">
  Task 2.3: Strengthened the atomicity warning for the slider v-model swap + localConfig initialization -- these two edits must be done together or the slider shows undefined on load.
</change>
</revision_summary>

**Note**: This is the ONLY meta-section. All other feedback is integrated inline.

## Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>Alembic migration chain is at head c3d4e5f6a7b8 (add_pantry_use_priority)</description>
  <verification>Run `alembic heads` -- must show c3d4e5f6a7b8. File exists at mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py.</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>SQLAlchemy 2.0.49 with Mapped[] / mapped_column() support</description>
  <verification>All 6 existing weight columns in mealie/db/models/optimizer/config.py (lines 27-32) use this pattern.</verification>
</prereq>
<prereq id="P3" type="library" verified="true">
  <description>Pydantic 2.12.5 with ConfigDict(from_attributes=True) on OptimizerConfigOut</description>
  <verification>mealie/schema/optimizer/config.py:32 -- `model_config = ConfigDict(from_attributes=True)` already present.</verification>
</prereq>
<prereq id="P4" type="data" verified="true">
  <description>No hidden consumers of setSlotOverlapPenalty beyond 3 identified files</description>
  <verification>Grep for `setSlotOverlapPenalty` finds only: use-optimizer-planner.ts (definition + export + return), planner.vue (destructure + call). No other consumers.</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>scoring-engine.test.ts already uses slotOverlapPenalty: 0.7 as default</description>
  <verification>scoring-engine.test.ts:54 -- `slotOverlapPenalty: 0.7`. Matches backend default. No test changes needed.</verification>
</prereq>
</prerequisites>

## Phase 1: Backend -- Database Column + Model + Schema

<phase id="1" name="Backend Persistence Layer">

### 1.1 Create Alembic Migration

<task id="1.1" status="pending" depends="" risk="low">
<context>
Create a new Alembic migration file that adds a `slot_overlap_penalty_weight` column to the `optimizer_config` table.

**File to create:** `mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py`

**Pattern to follow:** Copy the structure from `mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py` -- same imports, same docstring style, same function signatures.

**Key values:**
- `revision = "d4e5f6a7b8c9"`
- `down_revision = "c3d4e5f6a7b8"` (chains off add_pantry_use_priority)
- `branch_labels = None`
- `depends_on = None`

**upgrade():** `op.add_column("optimizer_config", sa.Column("slot_overlap_penalty_weight", sa.Float(), nullable=False, server_default="0.7"))`

**downgrade():** `op.drop_column("optimizer_config", "slot_overlap_penalty_weight")`

The `server_default="0.7"` ensures existing rows in the optimizer_config table receive the default value during migration. The column is `nullable=False` consistent with all other weight columns.
</context>

<subtasks>
- [ ] Create the migration file with correct revision chain
- [ ] Implement upgrade() with add_column
- [ ] Implement downgrade() with drop_column
</subtasks>

<acceptance>
- File exists at the specified path
- `revision` is `"d4e5f6a7b8c9"` and `down_revision` is `"c3d4e5f6a7b8"`
- upgrade() adds a Float column named `slot_overlap_penalty_weight` with `nullable=False` and `server_default="0.7"`
- downgrade() drops the column
- Running `task py:migrate` (or `alembic upgrade head`) succeeds without errors
</acceptance>
</task>

### 1.2 Add SQLAlchemy Model Column

<task id="1.2" status="pending" depends="1.1" risk="low">
<context>
Add the `slot_overlap_penalty_weight` mapped column to `OptimizerConfigModel` in `mealie/db/models/optimizer/config.py`.

**Insert after line 32** (the `rating_weight` column), before line 34 (`prep_time_budget_minutes`):

```python
slot_overlap_penalty_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, server_default="0.7")
```

This follows the exact pattern of the 6 existing weight columns (lines 27-32): `Mapped[float]`, `mapped_column(Float, ...)`, `nullable=False`, `default=X`, `server_default="X"`.

The `@auto_init()` decorator on `__init__` will automatically handle the new column -- no constructor changes needed.
</context>

<subtasks>
- [ ] Add `slot_overlap_penalty_weight` mapped column after `rating_weight` in OptimizerConfigModel
- [ ] Verify the column definition matches the pattern of other weight columns (Float, nullable=False, default, server_default)
</subtasks>

<acceptance>
- `OptimizerConfigModel` has a `slot_overlap_penalty_weight` attribute of type `Mapped[float]`
- Column appears between `rating_weight` and `prep_time_budget_minutes`
- Column uses `Float`, `nullable=False`, `default=0.7`, `server_default="0.7"`
- `task py:lint` passes (no ruff errors)
</acceptance>
</task>

### 1.3 Add Pydantic Schema Field

<task id="1.3" status="pending" depends="1.2" risk="low">
<context>
Add `slot_overlap_penalty_weight` to `OptimizerConfigUpdate` in `mealie/schema/optimizer/config.py`.

**Insert after line 17** (`rating_weight: float = 0.2`), before `prep_time_budget_minutes`:

```python
slot_overlap_penalty_weight: float = 0.7
```

**Why only one line:** `OptimizerConfigSave` extends `OptimizerConfigUpdate` (line 23), and `OptimizerConfigOut` extends `OptimizerConfigUpdate` (line 28). Both inherit the new field automatically. `OptimizerConfigOut` has `model_config = ConfigDict(from_attributes=True)` which means it reads the SQLAlchemy model's attributes by name -- the matching `slot_overlap_penalty_weight` attribute on the model will be picked up automatically.

**No changes needed to:**
- `OptimizerConfigSave` -- inherits from `OptimizerConfigUpdate`
- `OptimizerConfigOut` -- inherits from `OptimizerConfigUpdate`, `from_attributes=True` handles ORM mapping
- Repository (`mealie/repos/optimizer/config.py`) -- `get_or_create_default()` creates via `OptimizerConfigSave()` which inherits defaults
- Controller (`mealie/routes/optimizer/controller_config.py`) -- generic GET/PUT, serializes whatever schema defines
</context>

<subtasks>
- [ ] Add `slot_overlap_penalty_weight: float = 0.7` to OptimizerConfigUpdate after `rating_weight`
</subtasks>

<acceptance>
- `OptimizerConfigUpdate` has `slot_overlap_penalty_weight` field with default `0.7`
- `OptimizerConfigSave()` (no args beyond group_id/household_id) produces an object with `slot_overlap_penalty_weight == 0.7`
- `task py:lint` passes
- GET `/api/households/optimizer/config` returns JSON containing `slotOverlapPenaltyWeight` (via Mealie's camelCase alias generator)
- PUT `/api/households/optimizer/config` without `slotOverlapPenaltyWeight` in body succeeds (default 0.7 applies)
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] Migration file exists and chains correctly (`down_revision = "c3d4e5f6a7b8"`)
- [ ] `task py:lint` passes with no errors
- [ ] `task py:migrate` succeeds (if database is available)
- [ ] SQLAlchemy model, Pydantic schema, and migration all use matching column name `slot_overlap_penalty_weight`
- [ ] Default value is consistently `0.7` across all three layers
</verification>
<gate>The backend stack is complete: column exists in DB, model maps it, schema exposes it, API serializes it. All without touching the controller, repository, or any upstream files.</gate>
</checkpoint>

</phase>

## Phase 2: Frontend -- TypeScript Type + Workaround Removal

<phase id="2" name="Frontend Integration and Cleanup" depends="1">

### 2.1 Add TypeScript Type Field

<task id="2.1" status="pending" depends="1.3" risk="low">
<context>
Add `slotOverlapPenaltyWeight` to the `OptimizerConfigUpdate` TypeScript interface in `frontend/app/lib/api/types/optimizer.ts`.

**Insert after line 94** (`ratingWeight: number;`), before `prepTimeBudgetMinutes`:

```typescript
slotOverlapPenaltyWeight: number;
```

`OptimizerConfigOut` extends `OptimizerConfigUpdate` (line 100), so it inherits the field automatically.

**No changes needed to:**
- `frontend/app/lib/api/user/optimizer-pantry.ts` -- the API client methods (`getConfig()`, `updateConfig()`) are generic
- `frontend/app/composables/optimizer/types.ts` -- `ScoringWeights` already has `slotOverlapPenalty` (the consumer-side name)
</context>

<subtasks>
- [ ] Add `slotOverlapPenaltyWeight: number;` to `OptimizerConfigUpdate` interface after `ratingWeight`
</subtasks>

<acceptance>
- `OptimizerConfigUpdate` interface has `slotOverlapPenaltyWeight: number`
- `OptimizerConfigOut` inherits it via `extends`
- `task ui:lint` passes
</acceptance>
</task>

### 2.2 Refactor Composable -- Remove Client-Side Workaround

**Note:** This task and task 2.3 are independent and may be executed in parallel. Both depend on 2.1. Task 2.4 depends on both completing.

<task id="2.2" status="pending" depends="2.1" risk="medium">
<context>
Modify `frontend/app/composables/optimizer/use-optimizer-planner.ts` to read `slotOverlapPenalty` from the persisted config instead of a local variable.

**4 removals:**

1. **Line 189** -- Remove `let currentSlotPenalty = 0.7;` (the client-side variable)
2. **Lines 466-472** -- Remove the entire `setSlotOverlapPenalty` function:
   ```typescript
   function setSlotOverlapPenalty(value: number): void {
     currentSlotPenalty = value;
     if (config.value) {
       const weights = mapConfigToWeights(config.value, currentSlotPenalty);
       scoring.setWeights(weights);
     }
   }
   ```
3. **Line 44** -- Remove `setSlotOverlapPenalty(value: number): void;` from the `UsePlannerReturn` interface
4. **Line 501** -- Remove `setSlotOverlapPenalty,` from the return object

**1 signature change:**

Change `mapConfigToWeights` (line 147) from:
```typescript
function mapConfigToWeights(cfg: OptimizerConfigOut, currentSlotPenalty: number): ScoringWeights {
```
to:
```typescript
function mapConfigToWeights(cfg: OptimizerConfigOut): ScoringWeights {
```

And inside the function body (line 155), change:
```typescript
slotOverlapPenalty: currentSlotPenalty,
```
to:
```typescript
slotOverlapPenalty: cfg.slotOverlapPenaltyWeight,
```

**2 call site updates (these are easy to miss -- verify both):**

1. **Line 222** (in `loadData()`): Change `mapConfigToWeights(configRes.data, currentSlotPenalty)` to `mapConfigToWeights(configRes.data)`
2. **Line 456** (in `updateConfig()`): Change `mapConfigToWeights(data, currentSlotPenalty)` to `mapConfigToWeights(data)`
</context>

<subtasks>
- [ ] Remove `let currentSlotPenalty = 0.7;` (line 189)
- [ ] Change `mapConfigToWeights` signature: remove second parameter `currentSlotPenalty` (line 147)
- [ ] Change `mapConfigToWeights` body: `slotOverlapPenalty: cfg.slotOverlapPenaltyWeight` (line 155)
- [ ] Update call in `loadData()` -- remove second argument (line 222)
- [ ] Update call in `updateConfig()` -- remove second argument (line 456)
- [ ] Remove `setSlotOverlapPenalty` function (lines 466-472)
- [ ] Remove `setSlotOverlapPenalty` from `UsePlannerReturn` interface (line 44)
- [ ] Remove `setSlotOverlapPenalty` from return object (line 501)
</subtasks>

<acceptance>
- No `currentSlotPenalty` variable exists in the file
- No `setSlotOverlapPenalty` function exists in the file
- `mapConfigToWeights` has exactly one parameter (`cfg: OptimizerConfigOut`)
- `slotOverlapPenalty` in the returned `ScoringWeights` is set to `cfg.slotOverlapPenaltyWeight`
- `UsePlannerReturn` interface has no `setSlotOverlapPenalty` member
- `task ui:lint` passes
- `task ui:test` passes (scoring-engine.test.ts should still pass as it doesn't call this composable directly)
</acceptance>

<rollback risk="medium">
If partially applied, the composable may reference removed variables or have mismatched function signatures. To recover: revert the entire file to its pre-edit state via `git checkout -- frontend/app/composables/optimizer/use-optimizer-planner.ts` and retry.
</rollback>
</task>

### 2.3 Unify ConfigPanel Slider Path

**Note:** This task and task 2.2 are independent and may be executed in parallel. Both depend on 2.1. Task 2.4 depends on both completing.

<task id="2.3" status="pending" depends="2.1" risk="medium">
<context>
Modify `frontend/app/components/optimizer/ConfigPanel.vue` to remove the separate slot-penalty prop/emit/ref/debounce path and fold the slider into the standard `localConfig` -> debounced `emit("update")` path used by all other sliders.

**Template change (line 84):**
Change the slot penalty slider from:
```html
<v-slider
  v-model="localSlotPenalty"
  ...
  @update:model-value="onSlotPenaltyChange"
/>
```
to:
```html
<v-slider
  v-model="localConfig.slotOverlapPenaltyWeight"
  ...
  @update:model-value="onConfigChange"
/>
```

**Script removals:**

1. **Line 117** -- Remove `slotOverlapPenalty: number;` from `defineProps` so it becomes:
   ```typescript
   defineProps<{
     config: OptimizerConfigOut | null;
   }>()
   ```

2. **Line 122** -- Remove `(e: "update-slot-penalty", value: number): void;` from `defineEmits` so it becomes:
   ```typescript
   defineEmits<{
     (e: "update", config: OptimizerConfigUpdate): void;
   }>()
   ```

3. **Line 128** -- Remove `const localSlotPenalty = ref(props.slotOverlapPenalty);`

4. **Line 131** -- Remove `let penaltyDebounceTimer: ReturnType<typeof setTimeout> | null = null;`

5. **Lines 149-151** -- Remove the watcher:
   ```typescript
   watch(() => props.slotOverlapPenalty, (val) => {
     localSlotPenalty.value = val;
   });
   ```

6. **Lines 163-168** -- Remove the `onSlotPenaltyChange` function entirely.

**CRITICAL -- localConfig initialization (must be done atomically with the slider v-model change):**

Add `slotOverlapPenaltyWeight: newConfig.slotOverlapPenaltyWeight,` to the `localConfig.value` assignment inside the `watch(() => props.config, ...)` callback (lines 135-145), after `ratingWeight`:

```typescript
localConfig.value = {
  overlapWeight: newConfig.overlapWeight,
  pantryUtilizationWeight: newConfig.pantryUtilizationWeight,
  pantryUrgencyWeight: newConfig.pantryUrgencyWeight,
  proteinDiversityWeight: newConfig.proteinDiversityWeight,
  categoryBalanceWeight: newConfig.categoryBalanceWeight,
  ratingWeight: newConfig.ratingWeight,
  slotOverlapPenaltyWeight: newConfig.slotOverlapPenaltyWeight,  // NEW
  prepTimeBudgetMinutes: newConfig.prepTimeBudgetMinutes,
  perishableLabelKeywords: [...newConfig.perishableLabelKeywords],
  shelfStableLabelKeywords: [...newConfig.shelfStableLabelKeywords],
};
```

If `slotOverlapPenaltyWeight` is omitted from the `localConfig` initialization but the slider v-model points to `localConfig.slotOverlapPenaltyWeight`, the slider will show `undefined` or `0` on page load. These two edits (slider v-model + config init) must land together.
</context>

<subtasks>
- [ ] Add `slotOverlapPenaltyWeight: newConfig.slotOverlapPenaltyWeight` to localConfig initialization in the config watcher (line ~141, after ratingWeight)
- [ ] Change slider v-model from `localSlotPenalty` to `localConfig.slotOverlapPenaltyWeight` (line 84)
- [ ] Change slider @update:model-value from `onSlotPenaltyChange` to `onConfigChange` (line 90)
- [ ] Remove `slotOverlapPenalty: number` from defineProps (line 117)
- [ ] Remove `update-slot-penalty` emit from defineEmits (line 122)
- [ ] Remove `localSlotPenalty` ref (line 128)
- [ ] Remove `penaltyDebounceTimer` variable (line 131)
- [ ] Remove `watch(() => props.slotOverlapPenalty, ...)` watcher (lines 149-151)
- [ ] Remove `onSlotPenaltyChange` function (lines 163-168)
</subtasks>

<acceptance>
- `defineProps` has only `config: OptimizerConfigOut | null`
- `defineEmits` has only `(e: "update", config: OptimizerConfigUpdate): void`
- No `localSlotPenalty` ref exists
- No `penaltyDebounceTimer` exists
- No `onSlotPenaltyChange` function exists
- No watcher for `slotOverlapPenalty` prop exists
- The slot penalty slider uses `v-model="localConfig.slotOverlapPenaltyWeight"` and `@update:model-value="onConfigChange"`
- `slotOverlapPenaltyWeight` appears in the `localConfig.value = { ... }` initialization block
- All 7 sliders now follow the same reactive -> debounced emit path
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If partially applied, the template may reference removed refs or the script may have dangling variables. To recover: revert via `git checkout -- frontend/app/components/optimizer/ConfigPanel.vue` and retry.
</rollback>
</task>

### 2.4 Clean Up Planner Page

<task id="2.4" status="pending" depends="2.2,2.3" risk="low">
<context>
Modify `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` to remove all slot-penalty-specific wiring now that ConfigPanel handles it through the standard config path.

**3 removals:**

1. **Line 174** -- Remove `setSlotOverlapPenalty` from the composable destructure:
   ```typescript
   // Change from:
   savePlan, updateConfig, setActiveSlot, setSlotOverlapPenalty,
   // To:
   savePlan, updateConfig, setActiveSlot,
   ```

2. **Line 180** -- Remove `const localSlotPenalty = ref(0.7);`

3. **Lines 252-255** -- Remove the `onSlotPenaltyUpdate` function:
   ```typescript
   function onSlotPenaltyUpdate(value: number) {
     localSlotPenalty.value = value;
     setSlotOverlapPenalty(value);
   }
   ```

**1 template change -- ConfigPanel binding (lines 121-127):**
Change from:
```html
<ConfigPanel
  :config="config"
  :slot-overlap-penalty="localSlotPenalty"
  class="mb-4"
  @update="onConfigUpdate"
  @update-slot-penalty="onSlotPenaltyUpdate"
/>
```
To:
```html
<ConfigPanel
  :config="config"
  class="mb-4"
  @update="onConfigUpdate"
/>
```
</context>

<subtasks>
- [ ] Remove `setSlotOverlapPenalty` from the composable destructure (line 174)
- [ ] Remove `const localSlotPenalty = ref(0.7);` (line 180)
- [ ] Remove `onSlotPenaltyUpdate` function (lines 252-255)
- [ ] Remove `:slot-overlap-penalty="localSlotPenalty"` from ConfigPanel binding
- [ ] Remove `@update-slot-penalty="onSlotPenaltyUpdate"` from ConfigPanel binding
</subtasks>

<acceptance>
- No `localSlotPenalty` ref in the file
- No `onSlotPenaltyUpdate` function in the file
- No `setSlotOverlapPenalty` in the composable destructure
- ConfigPanel binding has no `:slot-overlap-penalty` or `@update-slot-penalty` attributes
- `task ui:lint` passes
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task ui:lint` passes with no errors
- [ ] `task ui:test` passes (scoring-engine tests use hardcoded weights, unaffected)
- [ ] No references to `setSlotOverlapPenalty` remain outside of docs/
- [ ] No references to `localSlotPenalty` remain outside of docs/
- [ ] No references to `currentSlotPenalty` remain outside of docs/
- [ ] No references to `onSlotPenaltyChange` remain outside of docs/
- [ ] No references to `update-slot-penalty` remain outside of docs/
- [ ] `slotOverlapPenaltyWeight` appears in: TypeScript type, localConfig init, slider v-model, mapConfigToWeights
</verification>
<gate>The frontend reads and writes slotOverlapPenaltyWeight through the standard config API round-trip. All client-side workaround code is removed. All 7 sliders follow the same path.</gate>
</checkpoint>

</phase>

## Phase 3: End-to-End Validation

<phase id="3" name="End-to-End Validation" depends="2">

### 3.1 Full Stack Verification

<task id="3.1" status="pending" depends="2.4" risk="low">
<context>
Run all linters and tests to confirm nothing is broken.

**Commands to run:**
1. `task py:lint` -- Python linting (ruff)
2. `task ui:lint` -- Frontend linting (eslint)
3. `task ui:test` -- Frontend tests (vitest)

**Manual verification (if dev servers are available):**
1. Start backend: `task py:postgres`
2. Start frontend: `task ui`
3. Navigate to the optimizer planner page
4. Open the config panel
5. Adjust the Complement Contrast (slot overlap penalty) slider to a non-default value (e.g., 1.2)
6. Refresh the page
7. Verify the slider shows 1.2, not the old default 0.7

**Grep verification (run all 5):**
- `grep -r "setSlotOverlapPenalty" --include="*.ts" --include="*.vue"` returns no results
- `grep -r "currentSlotPenalty" --include="*.ts" --include="*.vue"` returns no results
- `grep -r "localSlotPenalty" --include="*.ts" --include="*.vue"` returns no results
- `grep -r "update-slot-penalty" --include="*.ts" --include="*.vue"` returns no results
- `grep -r "onSlotPenaltyChange" --include="*.ts" --include="*.vue"` returns no results
</context>

<subtasks>
- [ ] `task py:lint` passes
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes
- [ ] Grep confirms no remnants of client-side workaround in source files
- [ ] Manual smoke test (if servers available): slider value persists across page reloads
</subtasks>

<acceptance>
- All lint and test commands exit with code 0
- No references to removed code remain in source files (only in docs/)
- If manually testable: slider value survives page reload
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] All automated checks pass
- [ ] No regressions in existing optimizer functionality
</verification>
<gate>The feature is complete: the Complement Contrast slider persists its value to the database and survives page reloads, matching the behavior of all other scoring weight sliders.</gate>
</checkpoint>

</phase>

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="medium">
  <description>Migration head conflict if another branch adds a migration with the same down_revision (c3d4e5f6a7b8) before this ships.</description>
  <mitigation>This is a single-developer fork with no concurrent branches. If it does happen, re-chain the migration's down_revision to the new head.</mitigation>
  <detection>`alembic heads` shows multiple heads, or `task py:migrate` errors with "Multiple heads detected".</detection>
</risk>
<risk id="R2" likelihood="low" impact="high">
  <description>Partial application of tasks 2.2 or 2.3 leaves composable or ConfigPanel in broken state (references to removed variables).</description>
  <mitigation>Both tasks have explicit rollback instructions. Each task's edits should be applied as a single atomic batch -- do not save intermediate states.</mitigation>
  <detection>TypeScript compile errors from `task ui:lint` or runtime errors in browser console.</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>Task 2.3: slider v-model changed to `localConfig.slotOverlapPenaltyWeight` but field omitted from localConfig initialization, causing slider to show 0/undefined on load.</description>
  <mitigation>Subtask ordering in 2.3 places the localConfig init addition first. Acceptance criteria explicitly checks for the field in the init block.</mitigation>
  <detection>Visual: slider starts at 0 instead of 0.7 (or the persisted value) on page load.</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] `task py:lint` exits with code 0
- [ ] `task ui:lint` exits with code 0
- [ ] `task ui:test` exits with code 0
- [ ] Migration file chains correctly off c3d4e5f6a7b8
- [ ] Default value 0.7 is consistent across migration, model, schema, and scoring-engine.test.ts
- [ ] No client-side workaround remnants (grep verification)
- [ ] All 7 config sliders follow the same reactive -> debounced emit -> API PUT -> re-map path
- [ ] No upstream files modified (all changes in optimizer/ subdirectories or frontend/app/lib/api/types/optimizer.ts)
</verification>
<acceptance>The slotOverlapPenalty scoring weight is persisted to the optimizer_config table via the same pipeline as all other weights. The Complement Contrast slider value survives page reloads. No behavioral change for users -- the default remains 0.7.</acceptance>
</final_validation>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-14-164925-slot-overlap-penalty-persistence.md">
  <question>Should the migration use alembic revision --autogenerate or be hand-written?</question>
  <default_assumption>Hand-written, matching the style of the existing use_priority migration. The migration is a single op.add_column call -- autogenerate adds no value and risks pulling in unrelated model drift.</default_assumption>
  <impact>If autogenerate is used, revision ID will differ from d4e5f6a7b8c9 and may include unrelated changes.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/specs/2026-04-14-164925-slot-overlap-penalty-persistence.md">
  <question>Should we add backend validation (min=0, max=2) to match the slider range?</question>
  <default_assumption>No -- none of the other 6 weights have backend validation. The slider enforces the range on the frontend. Consistency wins.</default_assumption>
  <impact>Without validation, the API accepts any float. With validation, out-of-range values are rejected. Neither affects the UI.</impact>
</question>
<question id="Q3" blocking="false" owner="human" inherited_from="docs/plans/2026-04-14-173824-slot-overlap-penalty-persistence.md">
  <question>The migration revision ID d4e5f6a7b8c9 is a placeholder -- should it be changed to a real random hex ID?</question>
  <default_assumption>Use the placeholder ID as specified. It's deterministic and unique within the current migration chain.</default_assumption>
  <impact>The ID just needs to be unique within the repo. If another migration uses this ID (unlikely), rename at that point.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-14-164925-slot-overlap-penalty-persistence.md">
<resolved original_question="Are there hidden consumers of setSlotOverlapPenalty beyond the 3 files identified?">
  <resolution>Grep confirmed: `setSlotOverlapPenalty` only appears in use-optimizer-planner.ts (definition + export) and planner.vue (destructure + call). No other consumers exist.</resolution>
</resolved>
<resolved original_question="Will Pydantic's from_attributes=True on OptimizerConfigOut pick up the new SQLAlchemy column?">
  <resolution>Yes. OptimizerConfigOut extends OptimizerConfigUpdate. Adding `slot_overlap_penalty_weight: float = 0.7` to OptimizerConfigUpdate makes it available on Out. `from_attributes=True` reads the matching attribute name from the SQLAlchemy model. This is exactly how the existing 6 weights work.</resolution>
</resolved>
</resolved_from_source>
