# Implementation Plan: Stage D — Polish & Onboarding

Source: docs/plans/2026-04-15-070000-stage-d-polish-onboarding.md
Revised: 2026-04-15

<plan_metadata>
  <feature>Stage D: Expiration Warnings, First-Run Import, Mobile Grid, Onboarding Wizard</feature>
  <source>docs/plans/2026-04-15-070000-stage-d-polish-onboarding.md</source>
  <revision_scope>heavy</revision_scope>
  <phases>5</phases>
  <tasks>20</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Stage D adds four polish features to the Mealie optimizer fork: (1) expiration warning indicators on pantry items with sorted display, (2) a first-run import prompt when the pantry is empty, (3) a mobile-responsive planner grid using day accordions instead of a 7-column CSS grid, and (4) a stretch-goal onboarding wizard for new users. All new code lives in `optimizer/` directories per fork isolation rules.

## Changes from Original

<revision_summary>
<change type="structural">
  Moved `onboarding_completed` field (migration, model, schema, TS type) from Phase 1 to Phase 4. This makes Phase 4 truly skippable as a stretch goal — Phases 1-3 carry no unused schema surface when Phase 4 is omitted.
</change>
<change type="dependency">
  Parallelized Phase 1: on-hand count endpoint (1.2) runs independently of config field work (1.1). Previously they were falsely serialized because they touch different tables/routes.
</change>
<change type="dependency">
  Moved i18n tasks to be prerequisites of their consuming tasks, not independent. Components that render `$t()` keys would show raw key strings if keys are missing. i18n tasks 2.1, 3.1a, 4.2 now run BEFORE their consuming tasks.
</change>
<change type="structural">
  Split Task 2.3 (pantry.vue) into two tasks: 2.5 (sort + config) and 2.6 (import prompt). They are independent features and the import prompt requires the on-hand count endpoint from Phase 1.
</change>
<change type="structural">
  Split Task 3.1 (PlanGrid responsive) into two tasks: 3.2 (extract PlanGridMobile.vue) and 3.3 (PlanGrid.vue responsive routing). Starting with extraction avoids a bloated v-if/v-else template and gives a clean rollback point.
</change>
<change type="clarity">
  Fixed i18n key prefix mismatch: shared `expirationTextKey()` helper now accepts a `prefix` parameter (default `"optimizer.pantry"`). OptimizerRecipeCard passes `"optimizer.planner"` to reuse existing planner i18n keys. Pantry page uses separate pantry-namespaced keys with Title Case capitalization.
</change>
<change type="clarity">
  Fixed icon references: replaced `$mdi-chef-hat` with `$globals.icons.chefHat` (verified: defined in `frontend/app/lib/icons/icons.ts:206`, used in 5 existing files). Replaced `$mdi-school` with `$globals.icons.chefHat` for setup nav (no `school` icon registered in project).
</change>
<change type="added">
  Added `OnHandCountResponse` TypeScript interface to Task 1.2 (was missing from original plan).
</change>
<change type="added">
  Added `OnHandCountResponse` to `__all__` list in `mealie/schema/optimizer/pantry.py` (was missing — the file uses explicit `__all__`, so un-listed classes are not exported by wildcard).
</change>
<change type="added">
  Added Task 4.3 to refactor ConfigPanel.vue with an `embedded` prop. ConfigPanel wraps content in `v-expansion-panels`, which nests awkwardly inside the onboarding wizard's `v-stepper`. The prop skips the wrapper when embedded in contexts like the wizard.
</change>
<change type="clarity">
  Specified CSS-only approach for touch detection (Task 3.4) using `@media (pointer: coarse)`. Avoids SSR issues with `window.matchMedia` in Nuxt. Only the `draggable` attribute conditional uses a JS ref initialized in `onMounted`.
</change>
<change type="dependency">
  Fixed Task 2.2 (expiration helpers) dependency: was `depends="1.4"` but only needs `PantryItemOut` type which already exists. Now `depends=""`.
</change>
<change type="removed">
  Removed redundant Final Validation section (was duplicated between Phase 5 task and standalone section).
</change>
</revision_summary>

## Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>Stages A-C complete: optimizer foundation, planner UI, shopping list enhancements all functional</description>
  <verification>Verify pantry CRUD, planner grid, scoring engine, and shopping list integration pages load at localhost:3000</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>Vuetify useDisplay() composable for responsive breakpoints</description>
  <verification>Already used in 10+ files (DefaultLayout.vue, shopping-lists/[id].vue, AppHeader.vue, etc.)</verification>
</prereq>
<prereq id="P3" type="library" verified="true">
  <description>Vuetify v-stepper component for onboarding wizard (Phase 4 only)</description>
  <verification>Already used in frontend/app/pages/admin/setup.vue with mobile-breakpoint="sm"</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>Vuetify v-expansion-panels for mobile day accordion</description>
  <verification>Already used in 6 files: ConfigPanel.vue, shopping-lists/[id].vue, cookbooks/index.vue, etc.</verification>
</prereq>
<prereq id="P5" type="data" verified="true">
  <description>household.ingredient_foods_on_hand many-to-many relationship for on-hand count</description>
  <verification>Defined in mealie/db/models/household/household.py:72, used by PantryService.import_from_on_hand() at mealie/services/optimizer/pantry.py:232</verification>
</prereq>
<prereq id="P6" type="environment" verified="true">
  <description>Latest Alembic migration head: d4e5f6a7b8c9 (add_slot_overlap_penalty_weight)</description>
  <verification>Confirmed: mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py exists</verification>
</prereq>
<prereq id="P7" type="library" verified="true">
  <description>date-fns ^4.1.0 for expiration date calculations</description>
  <verification>Confirmed in frontend/package.json:27. Functions differenceInCalendarDays, parseISO available. Import path: `import { differenceInCalendarDays, parseISO } from "date-fns"`</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend — Expiration Config + On-Hand Count

<phase id="1" name="Backend Expiration Config & On-Hand Count">

### 1.1 Alembic Migration + Model + Schema: `expiration_warning_days`

<task id="1.1" status="pending" depends="" risk="medium">
<context>
Add a configurable expiration warning threshold to the optimizer config. This field controls how many days before expiration a pantry item shows a warning indicator.

The optimizer config table already exists with 7 weight columns + prep_time_budget + 2 JSON keyword arrays. This task adds one integer column.

Key files:
- Migration template: `mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py`
- SQLAlchemy model: `mealie/db/models/optimizer/config.py` (54 lines) — imports from sqlalchemy: `JSON, Float, ForeignKey, Integer, UniqueConstraint`. Must add `Boolean` is NOT needed for this task (integer field only).
- Pydantic schema: `mealie/schema/optimizer/config.py` (34 lines) — `OptimizerConfigUpdate` is the base class. `OptimizerConfigSave` and `OptimizerConfigOut` inherit from it.
- Repo: `mealie/repos/optimizer/config.py` — `get_or_create_default()` creates rows with defaults from `OptimizerConfigSave`. New field defaults propagate automatically.

IMPORTANT: Run `alembic heads` first to confirm `d4e5f6a7b8c9` is the sole head before writing the migration.
</context>

<subtasks>
- [ ] Verify single Alembic head: run `cd mealie && alembic heads` — expect exactly `d4e5f6a7b8c9`
- [ ] Create migration `mealie/alembic/versions/2026-04-15-07.00.00_e5f6a7b8c9d0_add_expiration_warning_days.py` with revision `e5f6a7b8c9d0`, down_revision `d4e5f6a7b8c9`
- [ ] `upgrade()`: `op.add_column("optimizer_config", sa.Column("expiration_warning_days", sa.Integer, server_default="3", nullable=False))`
- [ ] `downgrade()`: `op.drop_column("optimizer_config", "expiration_warning_days")`
- [ ] Add `expiration_warning_days` mapped column to `OptimizerConfigModel` in `mealie/db/models/optimizer/config.py` (after `shelf_stable_label_keywords`): `expiration_warning_days: Mapped[int] = mapped_column(Integer, default=3, server_default="3")`
- [ ] Add `expiration_warning_days: int = 3` to `OptimizerConfigUpdate` in `mealie/schema/optimizer/config.py` (after `shelf_stable_label_keywords`)
</subtasks>

<acceptance>
- `alembic heads` shows exactly one head: `e5f6a7b8c9d0`
- `task py:migrate` applies the migration without error
- Existing optimizer_config rows have `expiration_warning_days=3`
- `task py:lint` passes
- GET /api/households/optimizer/config returns `expirationWarningDays: 3` in response (auto camelCase via alias generator)
- PUT /api/households/optimizer/config accepts `expirationWarningDays` and persists it
</acceptance>

<rollback risk="medium">
If migration fails: `alembic downgrade d4e5f6a7b8c9` reverts to previous head. Then delete the migration file, model field, and schema field.
</rollback>
</task>

### 1.2 On-Hand Count Endpoint + API Client

<task id="1.2" status="pending" depends="" risk="low">
<context>
Add a lightweight GET endpoint returning the count of ingredient foods marked as on-hand for the current household. This count drives the frontend import prompt (show only when count > 0).

IMPORTANT: Use a SQL COUNT query on the `households_to_ingredient_foods` join table, NOT a full relationship load. The existing `import_from_on_hand()` loads the full relationship, but counting should be efficient.

Key files:
- Join table: defined at `mealie/db/models/recipe/ingredient.py:21` as `households_to_ingredient_foods` (columns: `household_id`, `ingredient_food_id`)
- Service: `mealie/services/optimizer/pantry.py` — `PantryService` class, `import_from_on_hand()` at line 232 shows the relationship access pattern
- Route: `mealie/routes/optimizer/controller_pantry.py` — existing pantry controller
- API client: `frontend/app/lib/api/user/optimizer-pantry.ts` — existing API client class
- Schema: `mealie/schema/optimizer/pantry.py` — has explicit `__all__` list (lines 15-31), new schemas MUST be added to it
- TS types: `frontend/app/lib/api/types/optimizer.ts` — manually maintained despite auto-generated header

Note on `__all__`: `mealie/schema/optimizer/__init__.py` uses `from .pantry import *`, which respects the `__all__` list. If `OnHandCountResponse` is not in `__all__`, it won't be importable via the package, though direct imports still work.
</context>

<subtasks>
- [ ] Add `OnHandCountResponse` schema to `mealie/schema/optimizer/pantry.py`: `class OnHandCountResponse(MealieModel): count: int`
- [ ] Add `"OnHandCountResponse"` to the `__all__` list in `mealie/schema/optimizer/pantry.py`
- [ ] Add `get_on_hand_count()` method to `PantryService` in `mealie/services/optimizer/pantry.py`: query `select(func.count()).select_from(households_to_ingredient_foods).where(households_to_ingredient_foods.c.household_id == self.household_id)`, import `func` from `sqlalchemy` and `households_to_ingredient_foods` from `mealie.db.models.recipe.ingredient`
- [ ] Add GET `/on-hand-count` endpoint to `controller_pantry.py`: `@router.get("/on-hand-count", response_model=OnHandCountResponse)`
- [ ] Add `OnHandCountResponse` TypeScript interface to `frontend/app/lib/api/types/optimizer.ts`: `export interface OnHandCountResponse { count: number; }`
- [ ] Add route `pantryOnHandCount` to routes object in `optimizer-pantry.ts`: `` `${prefix}/households/optimizer/pantry/on-hand-count` ``
- [ ] Add `async getOnHandCount(): Promise<OnHandCountResponse>` method to `PantryItemsApi` class
</subtasks>

<acceptance>
- GET /api/households/optimizer/pantry/on-hand-count returns `{"count": N}` matching actual on-hand food count
- Returns `{"count": 0}` when no on-hand foods exist for the household
- `task py:lint` passes
- `task ui:lint` passes
- The endpoint appears in Swagger at localhost:9000/docs under "Optimizer: Pantry"
</acceptance>
</task>

### 1.3 TypeScript Interface: `expirationWarningDays`

<task id="1.3" status="pending" depends="1.1" risk="low">
<context>
Update the TypeScript interface to include the new config field. The file `frontend/app/lib/api/types/optimizer.ts` has a `pydantic2ts` auto-generated header, but optimizer types are NOT in the generation script (`dev/code-generation/gen_ts_types.py` has no optimizer references). These types are maintained manually despite the header.

Current `OptimizerConfigUpdate` interface (lines 102-113) has fields through `shelfStableLabelKeywords`. `OptimizerConfigOut` extends it (lines 115-119) and inherits all fields automatically.
</context>

<subtasks>
- [ ] Add `expirationWarningDays: number;` to `OptimizerConfigUpdate` interface in `frontend/app/lib/api/types/optimizer.ts` (after `shelfStableLabelKeywords`)
</subtasks>

<acceptance>
- `task ui:lint` passes
- No TypeScript compilation errors in files importing `OptimizerConfigUpdate` or `OptimizerConfigOut`
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `task py:lint` passes
- [ ] `task ui:lint` passes
- [ ] `task py:migrate` applies cleanly (one new column: `expiration_warning_days`)
- [ ] GET /api/households/optimizer/config returns `expirationWarningDays` field
- [ ] PUT /api/households/optimizer/config accepts and persists `expirationWarningDays`
- [ ] GET /api/households/optimizer/pantry/on-hand-count returns correct count
- [ ] `OnHandCountResponse` TS interface exists and compiles
</verification>
<gate>All backend schema changes for expiration warnings are in place. On-hand count endpoint works. TypeScript types match the backend. No `onboarding_completed` field yet — that belongs to Phase 4.</gate>
</checkpoint>

</phase>

---

## Phase 2: Expiration Warnings + Import Prompt (Frontend)

<phase id="2" name="Expiration Warnings & First-Run Import" depends="1">

### 2.1 i18n Keys — Expiration & Import

<task id="2.1" status="pending" depends="" risk="low">
<context>
Add i18n translation keys BEFORE the components that use them. If components render `$t('some.key')` before the key exists, the UI shows the raw key string.

File: `frontend/app/lang/messages/en-US.json`

The existing `optimizer.pantry` section (around line 1484 in en-US.json) already has keys like "title", "add-item", etc. Add the new keys after the existing ones.

Note on capitalization: These pantry-context keys use Title Case ("Expired", "Expires today") because they appear as standalone chip text. The existing `optimizer.planner` keys (lines 1530-1532) use lowercase ("expired", "expires today") because they appear inline after recipe names. Both sets are needed — they serve different display contexts.

Vue I18n pluralization: uses `|` pipe separator for singular|plural forms.
</context>

<subtasks>
- [ ] Add expiration keys to `optimizer.pantry` section: `"expired": "Expired"`, `"expires-soon": "Expires soon"`, `"expires-in-days": "Expires in {days} day | Expires in {days} days"`, `"expires-today": "Expires today"`
- [ ] Add config key: `"expiration-warning-days": "Expiration Warning (days)"`
- [ ] Add import keys: `"import-available": "You have {count} food marked as on-hand | You have {count} foods marked as on-hand"`, `"import-prompt": "Import them to your pantry to start tracking quantities?"`, `"import-button": "Import to Pantry"`, `"import-success": "Imported {imported} item, skipped {skipped} duplicate | Imported {imported} items, skipped {skipped} duplicates"`
- [ ] Verify JSON is valid after edit (no trailing commas, proper nesting)
</subtasks>

<acceptance>
- `task ui:lint` passes
- JSON is valid (no parse errors)
- All added keys are under the `optimizer.pantry` namespace
</acceptance>
</task>

### 2.2 Create Expiration Helpers Composable + Tests

<task id="2.2" status="pending" depends="" risk="low">
<context>
Create a new composable with pure helper functions for expiration date calculations. These will be shared by PantryItemRow (pantry page) and OptimizerRecipeCard (planner page) — two different UI contexts with different i18n key prefixes.

File: `frontend/app/composables/optimizer/use-expiration-helpers.ts`
Test file: `frontend/app/composables/optimizer/use-expiration-helpers.test.ts`

Dependencies: `date-fns` (^4.1.0, confirmed in package.json). Import: `import { differenceInCalendarDays, parseISO } from "date-fns"`.
Type: `PantryItemOut` from `~/lib/api/types/optimizer` (already exists).

IMPORTANT: The `expirationTextKey` function MUST accept a `prefix` parameter to support different i18n namespaces. The pantry page uses `optimizer.pantry.*` keys (Title Case) while the recipe cards use `optimizer.planner.*` keys (lowercase). Both sets exist/will exist in en-US.json.
</context>

<subtasks>
- [ ] Create `use-expiration-helpers.ts` with these 5 exported functions:
- [ ] `daysToExpiry(expirationDate: string | null | undefined): number | null` — returns null if no date; uses `differenceInCalendarDays(parseISO(date), new Date())` for 0=today, negative=past, positive=future
- [ ] `expirationSeverity(days: number | null, warningThreshold?: number): "expired" | "warning" | "ok" | "none"` — null→"none", <0→"expired", <=threshold(default 3)→"warning", >threshold→"ok"
- [ ] `expirationColor(severity: "expired" | "warning" | "ok" | "none"): string` — "expired"→"error", "warning"→"warning", "ok"→"success", "none"→"grey"
- [ ] `expirationTextKey(days: number | null, prefix: string = "optimizer.pantry"): { key: string; params?: Record<string, number> } | null` — null→null, <0→`{key: "${prefix}.expired"}`, ===0→`{key: "${prefix}.expires-today"}`, >0→`{key: "${prefix}.expires-in-days", params: {days}}`
- [ ] `sortByExpiration(items: PantryItemOut[]): PantryItemOut[]` — returns NEW sorted array: expired first (most negative first), then ascending by daysToExpiry, then null expirationDate last. Stable sort within equal groups.
- [ ] Create `use-expiration-helpers.test.ts` with vitest test suites covering:
- [ ] `daysToExpiry()`: null input, today, past (-2), future (+5)
- [ ] `expirationSeverity()`: all 4 return values + custom threshold override
- [ ] `expirationColor()`: all 4 severity inputs
- [ ] `expirationTextKey()`: null, expired, today, future; default prefix and custom prefix
- [ ] `sortByExpiration()`: empty array, mixed items with various expiration dates, all-null dates
</subtasks>

<acceptance>
- `task ui:test` passes including new test file
- All exported functions have complete TypeScript types (no `any`)
- `task ui:lint` passes
- `expirationTextKey(5)` returns `{ key: "optimizer.pantry.expires-in-days", params: { days: 5 } }`
- `expirationTextKey(5, "optimizer.planner")` returns `{ key: "optimizer.planner.expires-in-days", params: { days: 5 } }`
</acceptance>
</task>

### 2.3 Modify PantryItemRow.vue — Expiration Warning Indicators

<task id="2.3" status="pending" depends="2.1, 2.2" risk="low">
<context>
Add visual expiration warning indicators to each pantry item row. PantryItemRow.vue (137 lines) is a v-card with inline editing fields.

File: `frontend/app/components/optimizer/PantryItemRow.vue`
Current props (lines 101-105): `item`, `foods`, `units` — add `warningThreshold`.
Expiration date input: lines 71-80.

The shared helpers from `use-expiration-helpers.ts` provide all computation. The i18n keys from Task 2.1 provide the display text.

For the colored left border, use Vuetify's theme color CSS variables: `rgb(var(--v-theme-error))`, `rgb(var(--v-theme-warning))`, etc.
</context>

<subtasks>
- [ ] Add `warningThreshold?: number` prop with default value 3
- [ ] Import `daysToExpiry`, `expirationSeverity`, `expirationColor`, `expirationTextKey` from `~/composables/optimizer/use-expiration-helpers`
- [ ] Add computed properties: `itemDaysToExpiry` = `daysToExpiry(editItem.expirationDate)`, `severity` = `expirationSeverity(itemDaysToExpiry, props.warningThreshold)`, `borderColor` = `expirationColor(severity)`
- [ ] Add computed `chipTextInfo` = `expirationTextKey(itemDaysToExpiry)` (uses default pantry prefix)
- [ ] Add dynamic border-left style on the v-card element: `:style="severity !== 'none' ? { borderLeft: '4px solid rgb(var(--v-theme-' + borderColor + '))' } : {}"`
- [ ] Add v-chip after expiration date input: `<v-chip v-if="severity === 'expired' || severity === 'warning'" size="small" :color="borderColor" variant="tonal" density="compact">{{ chipTextInfo ? $t(chipTextInfo.key, chipTextInfo.params ?? {}) : '' }}</v-chip>`
</subtasks>

<acceptance>
- Item with expirationDate 2 days from now shows warning-colored left border and "Expires in 2 days" chip
- Item with expirationDate in the past shows error-colored left border and "Expired" chip
- Item with no expirationDate shows no border color and no chip
- Item with expirationDate 10 days out shows success-colored left border, no chip
- `task ui:lint` passes
</acceptance>
</task>

### 2.4 Refactor OptimizerRecipeCard.vue — Use Shared Helpers

<task id="2.4" status="pending" depends="2.2" risk="low">
<context>
Replace the local `matchColor()` and `expirationText()` functions in OptimizerRecipeCard.vue with the shared helpers. The card is in the planner context and uses `optimizer.planner.*` i18n keys (these already exist at en-US.json lines 1530-1532).

File: `frontend/app/components/optimizer/OptimizerRecipeCard.vue` (~140 lines)

Current local functions (lines 98-108):
```javascript
function matchColor(match: PantryMatchDetail): string {
  if (match.daysToExpiry !== null && match.daysToExpiry <= 3) return "warning";
  return "success";
}
function expirationText(match: PantryMatchDetail): string {
  if (match.daysToExpiry === null) return "";
  if (match.daysToExpiry < 0) return t("optimizer.planner.expired");
  if (match.daysToExpiry === 0) return t("optimizer.planner.expires-today");
  return t("optimizer.planner.expires-in-days", { days: match.daysToExpiry });
}
```

IMPORTANT behavior change: The current code returns "warning" for ALL days <= 3 (including negative/expired). The shared helpers return "error" for expired (<0), "warning" for 0-3, "success" for >3. This is an intentional improvement — expired items should show red, not orange.

The function signatures and template usage (lines 53, 60) stay the same — callers don't change.
</context>

<subtasks>
- [ ] Add import: `import { expirationColor, expirationSeverity, expirationTextKey } from "~/composables/optimizer/use-expiration-helpers"`
- [ ] Replace `matchColor()` body: `return expirationColor(expirationSeverity(match.daysToExpiry));`
- [ ] Replace `expirationText()` body: `const info = expirationTextKey(match.daysToExpiry, "optimizer.planner"); if (!info) return ""; return t(info.key, info.params ?? {});`
- [ ] Remove any unused imports after refactor
</subtasks>

<acceptance>
- Recipe cards in the planner sidebar display expiration text and colors correctly
- Expired matches now show "error" color (red) instead of "warning" (orange) — intentional improvement
- Warning matches (0-3 days) still show "warning" color
- OK matches (>3 days) still show "success" color
- `task ui:lint` passes
- `task ui:test` passes (scoring engine tests are not affected — they don't test UI colors)
</acceptance>
</task>

### 2.5 Modify pantry.vue — Sort by Expiration + Config Fetch

<task id="2.5" status="pending" depends="2.2, 2.3, 1.3" risk="low">
<context>
Add expiration-based sorting to the pantry page and wire the config's warningThreshold to PantryItemRow.

File: `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` (~231 lines)

This task handles sorting and config — the import prompt is a separate task (2.6).

The existing `fetchPantryItems()` function fetches items and assigns to a ref. After fetching, apply `sortByExpiration()` before assignment.

For config, the optimizer API client for config already exists at `mealie/routes/optimizer/controller_config.py` and the frontend calls it via the existing config API. Check how planner.vue fetches config — follow the same pattern.
</context>

<subtasks>
- [ ] Import `sortByExpiration` from `~/composables/optimizer/use-expiration-helpers`
- [ ] Add state: `const config = ref<OptimizerConfigOut | null>(null)` — import `OptimizerConfigOut` from `~/lib/api/types/optimizer`
- [ ] Modify `fetchPantryItems()`: after the API fetch, apply `items.value = sortByExpiration(fetchedItems)`
- [ ] Add `fetchConfig()` function: call the config GET endpoint, assign to `config` ref
- [ ] Update `onMounted` to fetch both pantry items and config in parallel: `await Promise.all([fetchPantryItems(), fetchConfig()])`
- [ ] Pass `:warning-threshold="config?.expirationWarningDays ?? 3"` to each `<PantryItemRow>` in the template
</subtasks>

<acceptance>
- Pantry items display sorted: expired first (most negative daysToExpiry), then expiring-soon ascending, then no-date last
- PantryItemRow components receive correct warningThreshold from config
- Sorting re-applies after adding/editing/deleting items
- `task ui:lint` passes
</acceptance>
</task>

### 2.6 Modify pantry.vue — Import Prompt for Empty Pantry

<task id="2.6" status="pending" depends="2.1, 2.5, 1.2" risk="medium">
<context>
Add an import prompt to the pantry page's empty state. When the pantry is empty AND on-hand foods exist, show a prompt offering to import them.

File: `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` (modified by Task 2.5)

The on-hand count endpoint was added in Task 1.2. The `importFromOnHand()` API method already exists in `optimizer-pantry.ts`.

Current empty state template is around lines 19-23 (an empty-state card). This task adds a conditional section inside it.
</context>

<subtasks>
- [ ] Add state variables: `onHandCount = ref(0)`, `importing = ref(false)`, `importResult = ref<PantryImportResult | null>(null)`
- [ ] Add `fetchOnHandCount()` function: call `api.optimizer.pantry.getOnHandCount()`, set `onHandCount.value`
- [ ] Update `onMounted` to also fetch on-hand count: `await Promise.all([fetchPantryItems(), fetchConfig(), fetchOnHandCount()])`
- [ ] Add `onImportFromOnHand()` function: set `importing=true`, call `api.optimizer.pantry.importFromOnHand()`, set `importResult`, refresh pantry items, set `importing=false`, show success snackbar
- [ ] Modify empty state template: when `onHandCount > 0`, show import prompt text (`$t('optimizer.pantry.import-available', { count: onHandCount })` + `$t('optimizer.pantry.import-prompt')`) and import button (`$t('optimizer.pantry.import-button')`, loading state via `importing`)
- [ ] When `onHandCount === 0`, show only standard empty message (current behavior)
- [ ] Add v-snackbar for import result: `$t('optimizer.pantry.import-success', { imported: importResult.importedCount, skipped: importResult.skippedCount })`
</subtasks>

<acceptance>
- Empty pantry with on-hand foods shows import prompt with correct count
- Empty pantry with zero on-hand foods shows only standard empty message
- Clicking import calls importFromOnHand(), refreshes sorted list, shows success toast
- After import, empty state disappears and imported items are listed (sorted by expiration)
- Import button shows loading state during API call
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If import prompt causes issues, revert by removing the v-if/v-else on onHandCount in the empty state template. The sort change from Task 2.5 is independent and unaffected.
</rollback>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes (scoring-engine + new expiration helper tests)
- [ ] Pantry page at localhost:3000 shows items sorted by expiration
- [ ] Pantry items with near/past expiration dates show colored borders and chips
- [ ] Empty pantry with on-hand foods shows import prompt
- [ ] Import button works, refreshes list, shows success toast
- [ ] Recipe cards in planner sidebar show correct expiration colors (including "error" for expired)
- [ ] No regressions in pantry CRUD operations
- [ ] No regressions in planner scoring/suggestions
</verification>
<gate>Expiration warnings display correctly on pantry page and recipe cards. Import prompt works for empty pantry. All tests pass.</gate>
</checkpoint>

</phase>

---

## Phase 3: Mobile-Responsive Planner Grid

<phase id="3" name="Mobile-Responsive Grid" depends="2">

### 3.1 i18n Keys — Mobile Planner

<task id="3.1" status="pending" depends="" risk="low">
<context>
Add i18n keys before the mobile components that use them.

File: `frontend/app/lang/messages/en-US.json`

Add under the existing `optimizer.planner` section (which already has keys at lines 1518-1541):
</context>

<subtasks>
- [ ] Add keys to `optimizer.planner` section: `"show-suggestions": "Show Suggestions"`, `"hide-suggestions": "Hide Suggestions"`, `"day-entries": "{count} meal | {count} meals"`
- [ ] Verify JSON validity
</subtasks>

<acceptance>
- `task ui:lint` passes
- JSON is valid
</acceptance>
</task>

### 3.2 Extract PlanGridMobile.vue Component

<task id="3.2" status="pending" depends="3.1" risk="medium">
<context>
Extract the mobile accordion layout into a dedicated component BEFORE modifying PlanGrid.vue. This avoids template bloat from a v-if/v-else pattern and provides a clean rollback point: if mobile layout fails, delete the file and PlanGrid.vue stays untouched.

Create: `frontend/app/components/optimizer/PlanGridMobile.vue`

The mobile layout replaces the 7-column CSS grid with v-expansion-panels (accordion). Each day is one panel. Today is expanded by default, others collapsed.

The mobile component must accept the same props and emit the same events as PlanGrid.vue so it's a drop-in replacement. Read PlanGrid.vue (95 lines) to understand the full prop/event interface.

Key files:
- PlanGrid.vue: `frontend/app/components/optimizer/PlanGrid.vue` (95 lines) — read this to extract the prop/event interface
- PlanSlot.vue: used within PlanGrid — same slot-click, slot-drop, entry-remove events must be wired
- Vuetify v-expansion-panels: used in 6 existing files, supports `variant="accordion"`, `v-model` for expanded panel tracking
</context>

<subtasks>
- [ ] Read PlanGrid.vue to determine full props interface (days, entries, entryTypes, activeSlot, etc.) and emits (slot-click, slot-drop, entry-remove)
- [ ] Create PlanGridMobile.vue with identical props and emits
- [ ] Template: `v-expansion-panels v-model="expandedDay" variant="accordion"` with one `v-expansion-panel` per day
- [ ] Panel title: formatted day name + `v-badge :content="dayEntryCount(day)" color="primary" inline`
- [ ] Panel content: iterate `entryTypes`, render `<PlanSlot>` for each with identical prop/event bindings as PlanGrid.vue
- [ ] Add `expandedDay` ref: initialized to today's formatted date string (today expanded by default)
- [ ] Add `dayEntryCount(day: Date): number` helper: count all entries across all entry types for that day
- [ ] Use `$t('optimizer.planner.day-entries', { count })` for badge aria-label
</subtasks>

<acceptance>
- PlanGridMobile.vue compiles without errors
- Component accepts same props and emits same events as PlanGrid.vue
- v-expansion-panels render with today's panel expanded
- Each panel header shows day name and entry count badge
- PlanSlot events (slot-click, slot-drop, entry-remove) fire correctly
- `task ui:lint` passes
</acceptance>
</task>

### 3.3 PlanGrid.vue — Responsive Layout Routing

<task id="3.3" status="pending" depends="3.2" risk="medium">
<context>
Modify PlanGrid.vue to conditionally render either the existing CSS grid (desktop) or PlanGridMobile (mobile) based on screen size.

File: `frontend/app/components/optimizer/PlanGrid.vue` (95 lines)

The responsive switch is simple: import useDisplay, check smAndDown, and use v-if/v-else to swap between the existing template and the new PlanGridMobile component.

Since PlanGridMobile accepts the same props and emits the same events, the parent (planner.vue) needs NO changes — PlanGrid.vue handles the routing internally.
</context>

<subtasks>
- [ ] Import `useDisplay` from "vuetify"
- [ ] Import `PlanGridMobile` from `~/components/optimizer/PlanGridMobile.vue`
- [ ] Add `const { smAndDown } = useDisplay()`
- [ ] Wrap existing CSS grid template in `<template v-if="!smAndDown">`
- [ ] Add `<PlanGridMobile v-else v-bind="$props" v-on="$attrs" />` — pass through all props and events
- [ ] Verify that v-bind="$props" correctly forwards all props (if not, explicitly bind each prop)
</subtasks>

<acceptance>
- On screens >= md: 7-column CSS grid renders identically to current layout (pixel-perfect)
- On screens < md: PlanGridMobile accordion renders
- Resize window across md breakpoint: layout switches cleanly without errors
- slot-click, slot-drop, entry-remove events work in both layouts
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If mobile routing causes issues: remove the v-if/v-else, delete the PlanGridMobile import. PlanGrid.vue reverts to CSS-grid-only. The existing overflow-x scroll on mobile is functional (just not optimal).
</rollback>
</task>

### 3.4 Touch Interaction Fixes (PlanSlot + OptimizerRecipeCard)

<task id="3.4" status="pending" depends="3.3" risk="medium">
<context>
Fix touch-device usability issues. Use CSS-only approach where possible to avoid SSR issues with `window.matchMedia`.

Files:
- `frontend/app/components/optimizer/PlanSlot.vue` (194 lines)
- `frontend/app/components/optimizer/OptimizerRecipeCard.vue` (~140 lines, modified in Task 2.4)

**CSS approach** (no SSR issues):
- Remove button visibility: `@media (pointer: coarse) { .plan-slot__remove { opacity: 1; } }`
- Touch target sizes: `@media (pointer: coarse) { .plan-slot { --slot-min-height: 56px; } }`
- Drag cursor: `@media (pointer: coarse) { .recipe-card { cursor: default; } }`

**JS approach** (for draggable attribute — requires SSR guard):
- In OptimizerRecipeCard.vue: `const isTouchDevice = ref(false); onMounted(() => { isTouchDevice.value = window.matchMedia('(pointer: coarse)').matches; });`
- Conditionally set `:draggable="!isTouchDevice"` and conditionally bind `@dragstart`

**Mobile interaction flow**: On mobile, user taps a slot (slot-click activates it), then taps a recipe card in the sidebar (fires select event which calls addToDraft). No drag needed — this flow already works via existing click/select events.
</context>

<subtasks>
- [ ] PlanSlot.vue: Add `@media (pointer: coarse)` CSS rule to make `.plan-slot__remove` always visible (opacity: 1)
- [ ] PlanSlot.vue: Add `@media (pointer: coarse)` CSS rule for touch-friendly min-height
- [ ] OptimizerRecipeCard.vue: Add `isTouchDevice` ref with `onMounted` SSR guard
- [ ] OptimizerRecipeCard.vue: Set `:draggable="!isTouchDevice"` on the card element
- [ ] OptimizerRecipeCard.vue: Conditionally bind `@dragstart` only when `!isTouchDevice`
- [ ] OptimizerRecipeCard.vue: Add `@media (pointer: coarse)` CSS to remove drag cursor
- [ ] Verify click/select events still work as primary mobile interaction
</subtasks>

<acceptance>
- On touch devices: remove button always visible (not hover-dependent)
- On touch devices: recipe cards are not draggable, no drag cursor
- On touch devices: tapping a slot activates it, tapping a recipe adds it to slot
- Desktop behavior completely unchanged (drag-drop still works, hover reveals remove button)
- `task ui:lint` passes
</acceptance>
</task>

### 3.5 planner.vue — Mobile Sidebar Toggle + Layout Refinements

<task id="3.5" status="pending" depends="3.3" risk="medium">
<context>
Add a mobile sidebar toggle and layout refinements to the planner page.

File: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` (~320 lines)

The right panel (v-col cols="12" md="4") contains ConfigPanel + SuggestionSidebar. On mobile, hide it by default and show a FAB to toggle visibility.

Icon: Use `$globals.icons.chefHat` for the FAB (verified: defined at `frontend/app/lib/icons/icons.ts:206`, imported as `mdiChefHat` from MDI, used in 5 existing files including `admin/setup.vue`).

For the close icon when sidebar is shown, use `$close` which is a standard Vuetify alias.
</context>

<subtasks>
- [ ] Import `useDisplay` from "vuetify"
- [ ] Add `const { smAndDown } = useDisplay()` and `const showSidebar = ref(false)`
- [ ] Add `v-show="!smAndDown || showSidebar"` on the right-panel v-col
- [ ] Add FAB button (only on mobile): `<v-btn v-if="smAndDown" icon color="primary" style="position: fixed; bottom: 16px; right: 16px; z-index: 10;" @click="showSidebar = !showSidebar"><v-icon>{{ showSidebar ? '$close' : $globals.icons.chefHat }}</v-icon></v-btn>`
- [ ] Stack action buttons vertically on mobile: `:class="smAndDown ? 'flex-column gap-1' : 'gap-2'"`
- [ ] Auto-close sidebar on recipe selection when on mobile: in `onRecipeSelect` handler, add `if (smAndDown.value) showSidebar.value = false;`
- [ ] Make date picker button full-width on mobile: `:block="smAndDown"`
</subtasks>

<acceptance>
- Desktop: sidebar always visible, no FAB shown, layout identical to current
- Mobile: sidebar hidden by default, FAB visible at bottom-right with chef-hat icon
- Tapping FAB shows sidebar, icon changes to close (X)
- Selecting a recipe from mobile sidebar adds it to active slot and closes sidebar
- Action buttons stack vertically on mobile
- Date picker is full-width on mobile
- `task ui:lint` passes
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes
- [ ] Desktop planner at >= md breakpoint: CSS grid layout identical to before
- [ ] Mobile planner at < md: day accordion with today expanded, count badges
- [ ] Mobile: FAB toggles sidebar visibility
- [ ] Mobile: tapping slot then tapping recipe adds to slot and closes sidebar
- [ ] Mobile: remove buttons always visible (no hover dependency)
- [ ] Mobile: recipe cards not draggable, no drag cursor
- [ ] Mobile: action buttons stacked vertically
- [ ] Desktop: all existing functionality unchanged (drag-drop, hover, sidebar always visible)
- [ ] Resize window across breakpoint: layout switches cleanly
</verification>
<gate>Planner works well on both desktop and mobile. Mobile uses accordion layout with tap interactions. Desktop is completely unchanged.</gate>
</checkpoint>

</phase>

---

## Phase 4: Onboarding Wizard (Stretch Goal — Fully Skippable)

<phase id="4" name="Onboarding Wizard" depends="1">

Note: This entire phase can be skipped without affecting Phases 1-3. All `onboarding_completed` schema surface is self-contained here. Phase 4 depends only on Phase 1 (config infrastructure) — not on Phases 2 or 3.

### 4.1 Migration + Model + Schema + TS: `onboarding_completed`

<task id="4.1" status="pending" depends="1.1" risk="medium">
<context>
Add the `onboarding_completed` boolean field to optimizer config. This is separated from Phase 1's migration to keep the stretch goal fully self-contained.

The new migration chains after `e5f6a7b8c9d0` (from Task 1.1) which itself chains after `d4e5f6a7b8c9`.

If Phase 1 Task 1.1 has not been implemented yet, this task's migration should chain after `d4e5f6a7b8c9` directly and include BOTH columns. Adjust the down_revision accordingly.

Key files — same as Task 1.1:
- SQLAlchemy model: `mealie/db/models/optimizer/config.py` — must add `Boolean` import from sqlalchemy (currently imports `JSON, Float, ForeignKey, Integer, UniqueConstraint`)
- Pydantic schema: `mealie/schema/optimizer/config.py`
- TS types: `frontend/app/lib/api/types/optimizer.ts`
</context>

<subtasks>
- [ ] Create migration `mealie/alembic/versions/2026-04-15-08.00.00_f6a7b8c9d0e1_add_onboarding_completed.py` with revision `f6a7b8c9d0e1`, down_revision `e5f6a7b8c9d0`
- [ ] `upgrade()`: `op.add_column("optimizer_config", sa.Column("onboarding_completed", sa.Boolean, server_default="false", nullable=False))`
- [ ] `downgrade()`: `op.drop_column("optimizer_config", "onboarding_completed")`
- [ ] Add `Boolean` to sqlalchemy imports in `mealie/db/models/optimizer/config.py`
- [ ] Add `onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")` to `OptimizerConfigModel`
- [ ] Add `onboarding_completed: bool = False` to `OptimizerConfigUpdate` in `mealie/schema/optimizer/config.py`
- [ ] Add `onboardingCompleted: boolean;` to `OptimizerConfigUpdate` interface in `frontend/app/lib/api/types/optimizer.ts`
</subtasks>

<acceptance>
- `task py:migrate` applies the migration without error
- Existing optimizer_config rows have `onboarding_completed=false`
- GET /api/households/optimizer/config returns `onboardingCompleted: false`
- PUT /api/households/optimizer/config accepts `onboardingCompleted` and persists it
- `task py:lint` passes
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If migration fails: `alembic downgrade e5f6a7b8c9d0` reverts. Then delete migration file and revert model/schema/TS changes.
</rollback>
</task>

### 4.2 i18n Keys + ConfigPanel Embedded Mode

<task id="4.2" status="pending" depends="" risk="low">
<context>
Two independent preparations for the wizard:

**i18n keys**: Add all onboarding translation keys before the wizard page that uses them.

File: `frontend/app/lang/messages/en-US.json`

**ConfigPanel embedded mode**: The current ConfigPanel (`frontend/app/components/optimizer/ConfigPanel.vue`, 141 lines) wraps all content in `<v-expansion-panels>` + `<v-expansion-panel>`. When embedded in the onboarding wizard's `v-stepper-window-item`, this creates an awkward nested accordion-in-stepper UX where the config sliders start collapsed and require an extra click to reveal.

Add an `embedded` boolean prop (default false). When true, skip the expansion-panel wrapper and render the slider content directly.

Current template structure (lines 1-109):
```
<v-expansion-panels v-model="panel">
  <v-expansion-panel>
    <v-expansion-panel-title>...</v-expansion-panel-title>
    <v-expansion-panel-text>
      <div v-if="localConfig" class="d-flex flex-column gap-3">
        ... sliders ...
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>
</v-expansion-panels>
```

When `embedded=true`, render only the inner `<div v-if="localConfig" ...>` with the sliders, without the expansion panel wrapper.
</context>

<subtasks>
- [ ] Add `optimizer.onboarding` i18n section with keys: `"setup"`, `"welcome-title"`, `"welcome-description"`, `"step-pantry"`, `"step-config"`, `"step-done"`, `"import-intro"`, `"config-intro"`, `"done-title"`, `"done-description"` (uses `{pantryCount}`), `"go-to-planner"`, `"skip"`, `"setup-banner"`, `"start-setup"`, `"dismiss"`
- [ ] Verify JSON validity after adding keys
- [ ] Add `embedded?: boolean` prop to ConfigPanel.vue (default `false`)
- [ ] Modify template: wrap `v-expansion-panels` block in `<template v-if="!embedded">` ... `</template>`, add `<template v-else>` with just the inner slider `<div>` content
- [ ] When `embedded=true`, the `panel` ref is not needed — sliders render directly
</subtasks>

<acceptance>
- `task ui:lint` passes
- JSON is valid with all onboarding keys
- In planner.vue (existing usage): ConfigPanel renders identically (expansion panel wrapper, collapsed by default)
- With `<ConfigPanel :config="config" embedded @update="handler" />`: sliders render directly without expansion panel wrapper
</acceptance>
</task>

### 4.3 Create Setup Wizard Page

<task id="4.3" status="pending" depends="4.1, 4.2" risk="medium">
<context>
Create the 4-step onboarding wizard at `/optimizer/setup`.

File: `frontend/app/pages/g/[groupSlug]/optimizer/setup.vue`

Pattern reference: `frontend/app/pages/admin/setup.vue` uses `v-stepper v-model="currentPage" mobile-breakpoint="sm" alt-labels`, with v-stepper-header, v-stepper-item, v-stepper-window, v-stepper-window-item, v-stepper-actions.

State: fetch config, pantry items, and on-hand count on mount (same patterns as pantry.vue from Phase 2).

The ConfigPanel from Task 4.2 now supports an `embedded` prop — use `<ConfigPanel :config="config" embedded @update="onConfigUpdate" />` in Step 3.

IMPORTANT: Importing PantryItemRow for Step 2's review list requires PantryItemRow to already accept the props it needs. Reuse the same component from the pantry page.
</context>

<subtasks>
- [ ] Create `frontend/app/pages/g/[groupSlug]/optimizer/setup.vue`
- [ ] Implement v-stepper with `mobile-breakpoint="sm"` and `alt-labels` following admin/setup.vue pattern
- [ ] Step 1 (Welcome): title + description text, Next button only
- [ ] Step 2 (Pantry): if `onHandCount > 0`, show import button with count; after import, show PantryItemRow list for review; add "Add more" button for manual items. Back/Next buttons.
- [ ] Step 3 (Config): `<ConfigPanel :config="config" embedded @update="onConfigUpdate" />` with intro text. Back/Next buttons.
- [ ] Step 4 (Done): summary with pantry count, "Go to Meal Planner" button → `navigateTo('/g/' + groupSlug + '/optimizer/planner')`
- [ ] On reaching Step 4: call `updateConfig({ ...config, onboardingCompleted: true })`
- [ ] Add Skip button on every step: sets `onboardingCompleted=true` via API, navigates to planner
- [ ] Fetch config, pantry items, on-hand count on mount with `Promise.all()`
- [ ] Set page SEO title
</subtasks>

<acceptance>
- 4-step wizard renders with v-stepper, mobile-responsive at sm breakpoint
- Step 2 shows import button only when on-hand count > 0
- Step 2 displays imported items as PantryItemRow components
- Step 3 shows config sliders directly (no expansion panel wrapper) via `embedded` prop
- Completing wizard sets onboardingCompleted=true on server
- Skip button available on every step
- Revisiting /optimizer/setup after completion shows wizard with current state (not blocked)
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
This is a new page — delete the file entirely to revert. No existing functionality is affected.
</rollback>
</task>

### 4.4 Planner Onboarding Banner

<task id="4.4" status="pending" depends="4.1, 4.3" risk="low">
<context>
Add a dismissible onboarding banner to the planner page for first-time users.

File: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue`

The planner already fetches config on mount (in its `loadData()` function). Check `config.onboardingCompleted === false` to show the banner.

"Dismiss" sets `onboardingCompleted=true` server-side (permanent). The banner will not appear on any future visit.
</context>

<subtasks>
- [ ] Add `const onboardingDismissed = ref(false)` — local session state to hide banner immediately after dismiss
- [ ] Add `async function dismissOnboarding()`: call config update API with `onboardingCompleted: true`, set `onboardingDismissed = true`
- [ ] Add v-alert banner after existing alerts (before v-row): `v-if="config && !config.onboardingCompleted && !onboardingDismissed"`, type="info", variant="tonal", closable, @click:close="dismissOnboarding"
- [ ] Banner text: `$t('optimizer.onboarding.setup-banner')`
- [ ] Banner action: "Start Setup" link to `/g/${groupSlug}/optimizer/setup`
</subtasks>

<acceptance>
- First visit with onboardingCompleted=false shows setup banner
- Banner has "Start Setup" link to /optimizer/setup
- Banner dismiss button sets onboardingCompleted=true via API
- Subsequent visits show no banner
- Banner does not block planner usage
- `task ui:lint` passes
</acceptance>
</task>

### 4.5 DefaultLayout.vue — Setup Nav Link

<task id="4.5" status="pending" depends="4.3" risk="low">
<context>
Add an unconditional "Optimizer Setup" nav link to the sidebar.

File: `frontend/app/components/Layout/DefaultLayout.vue`

Current optimizer nav structure (around lines 250-256): Pantry (`$globals.icons.pantry`) and Planner (`$globals.icons.calendarWeek`). Add Setup after these.

The link is always visible (not conditional on onboardingCompleted). This avoids fetching config in the global layout (extra API call on every page load). The setup page is always useful for reconfiguration.

Icon: Use `$globals.icons.chefHat` — it's the closest relevant icon registered in the project (defined at `frontend/app/lib/icons/icons.ts:206`). There is no `school` icon registered.
</context>

<subtasks>
- [ ] Add nav link object after existing Planner link: `{ icon: $globals.icons.chefHat, title: t("optimizer.onboarding.setup"), to: \`/g/${groupSlug}/optimizer/setup\`, restricted: true }`
- [ ] Verify link appears below Pantry and Planner in sidebar
</subtasks>

<acceptance>
- "Optimizer Setup" nav link appears in sidebar below Pantry and Planner
- Link navigates to /optimizer/setup page
- Icon matches the chef-hat icon used elsewhere
- `task ui:lint` passes
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes
- [ ] `task py:lint` passes
- [ ] `task py:migrate` applies cleanly (adds `onboarding_completed` column)
- [ ] /optimizer/setup page renders 4-step wizard
- [ ] Import step works when on-hand foods exist
- [ ] ConfigPanel sliders render directly in wizard (no expansion panel wrapper)
- [ ] Completing wizard sets onboardingCompleted=true
- [ ] Skip works from any step
- [ ] Planner shows onboarding banner when not completed
- [ ] Planner hides banner after dismiss
- [ ] Setup nav link appears in sidebar
- [ ] All onboarding i18n keys resolve
</verification>
<gate>Onboarding wizard guides new users through setup. Banner and nav link surface the wizard. Planner is never blocked by onboarding state.</gate>
</checkpoint>

</phase>

---

## Phase 5: Final Validation

<phase id="5" name="Final Validation" depends="2,3,4">

### 5.1 End-to-End Smoke Test

<task id="5.1" status="pending" depends="2.6, 3.4, 3.5, 4.5" risk="low">
<context>
Run all automated checks and perform manual smoke testing of every Stage D feature.

If Phase 4 was skipped, adjust the smoke test to exclude onboarding steps — Phases 1-3 are independently valid.

Manual testing requires dev servers: `task dev:services` + `task py:migrate` + `task py:postgres` + `task ui` (separate terminals).
</context>

<subtasks>
- [ ] Run `task py:lint` — expect 0 errors
- [ ] Run `task ui:lint` — expect 0 errors
- [ ] Run `task ui:test` — expect all tests pass (scoring-engine + expiration helpers)
- [ ] Run `task py:migrate` — expect clean application
- [ ] Manual: Visit /optimizer/pantry — verify items sorted by expiration
- [ ] Manual: Add item with expiration 2 days out — verify warning chip appears
- [ ] Manual: Add item with past expiration — verify error chip appears
- [ ] Manual: Delete all pantry items, verify import prompt shows if on-hand foods exist
- [ ] Manual: Click import, verify items imported and sorted
- [ ] Manual: Visit /optimizer/planner — verify desktop grid unchanged
- [ ] Manual: Resize to mobile width — verify accordion layout, FAB, touch interactions
- [ ] Manual: Tap FAB — sidebar shows; tap recipe — adds to slot, sidebar closes
- [ ] Manual (if Phase 4 done): Reset onboarding_completed=false, verify banner → wizard flow
- [ ] Manual: Check browser devtools console for new errors (filter for "optimizer" or new errors only)
</subtasks>

<acceptance>
- All automated checks pass (py:lint, ui:lint, ui:test, py:migrate)
- All manual smoke test steps complete successfully
- No new console errors in browser devtools
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] All Phase 1-4 checkpoints verified (Phase 4 optional if stretch goal skipped)
- [ ] All automated lint/test/migration checks pass
- [ ] Manual smoke test completed
</verification>
<gate>Stage D is complete. All features work on desktop and mobile. No regressions in Stages A-C.</gate>
</checkpoint>

</phase>

---

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="high">
  <description>Alembic migration conflict: if upstream adds migrations between d4e5f6a7b8c9 and our new migration, the chain breaks</description>
  <mitigation>Run `alembic heads` before writing the migration. If multiple heads exist, create a merge migration first.</mitigation>
  <detection>`task py:migrate` fails with "Multiple heads" error</detection>
</risk>
<risk id="R2" likelihood="medium" impact="medium">
  <description>Mobile accordion layout has event propagation issues (v-expansion-panel intercepting click events meant for PlanSlot)</description>
  <mitigation>PlanGridMobile.vue is extracted as a separate component — can be deleted without touching PlanGrid.vue. Rollback to CSS-grid-only with overflow-x scroll.</mitigation>
  <detection>Tap on slot inside accordion doesn't fire slot-click event</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>ConfigPanel embedded mode breaks the existing planner usage</description>
  <mitigation>The `embedded` prop defaults to false — existing usage is unchanged. Only the wizard passes `embedded`.</mitigation>
  <detection>ConfigPanel in planner.vue no longer renders expansion panel wrapper</detection>
</risk>
<risk id="R4" likelihood="medium" impact="low">
  <description>Touch detection via `pointer: coarse` CSS media query may not match all mobile browsers</description>
  <mitigation>This is the recommended approach for touch detection in web standards. Fallback: mobile users can still scroll to reveal items and use click interactions.</mitigation>
  <detection>Remove button hidden on specific mobile browsers that don't report pointer: coarse</detection>
</risk>
</risks>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should the mobile accordion show all days expanded by default, or only today?</question>
  <default_assumption>Show today expanded, others collapsed — reduces initial scroll depth. Implemented via `expandedDay` ref initialized to today's formatted date.</default_assumption>
  <impact>If all expanded: simpler code (no `expandedDay` ref needed), but long initial scroll. If only today: more taps to navigate, but focused initial view.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should the onboarding wizard be accessible after completion (for re-configuration)?</question>
  <default_assumption>Yes — /optimizer/setup always works. Nav link is always visible. The wizard shows current state on revisit, not a "completed" gate.</default_assumption>
  <impact>If gated: need "reset onboarding" option. If always accessible: simpler code, more useful for reconfiguration.</impact>
</question>
<question id="Q3" blocking="false" owner="human" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should expiration sorting persist across sessions or always apply on load?</question>
  <default_assumption>Always apply on load — no persisted sort preference needed. Sort is the natural display order (expired items need attention first).</default_assumption>
  <impact>If persisted: need a sort-preference field in config + UI toggle. If always: simpler, and the default is the only sensible order.</impact>
</question>
<question id="Q4" blocking="false" owner="human">
  <question>Should both ConfigPanel and SuggestionSidebar move into the mobile sidebar overlay, or only SuggestionSidebar?</question>
  <default_assumption>Both move into the sidebar v-col toggled by the FAB. ConfigPanel is above SuggestionSidebar, matching desktop layout. Users scroll within the sidebar.</default_assumption>
  <impact>If only suggestions: config changes require navigating to /optimizer/setup or scrolling past the grid. If both: sidebar may be long on mobile.</impact>
</question>
<question id="Q5" blocking="false" owner="human">
  <question>Should the setup nav link be conditional (hidden after onboarding) or always visible?</question>
  <default_assumption>Always visible — avoids layout-level API call, allows reconfiguration. The setup page is always useful.</default_assumption>
  <impact>If conditional: cleaner nav after setup, but requires config fetch in DefaultLayout.vue (extra API call on every page load, potential flash of nav item).</impact>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
<resolved original_question="Should the FAB sidebar toggle use v-bottom-sheet or v-navigation-drawer for the mobile sidebar?">
  <resolution>Neither. v-bottom-sheet has zero codebase usage (integration risk). Plan uses a simpler v-show toggle on the existing sidebar v-col. The FAB toggles a `showSidebar` ref. No new component needed.</resolution>
</resolved>
<resolved original_question="Does IngredientFoodModel.on_hand exist as a queryable boolean field?">
  <resolution>Yes, it exists at mealie/db/models/recipe/ingredient.py:192 but is marked "Deprecated". The correct approach is to query the `households_to_ingredient_foods` many-to-many join table. The on-hand-count endpoint uses a count query on this join table filtered by household_id.</resolution>
</resolved>
</resolved_from_source>

<resolved_from_source source="docs/plans/2026-04-15-070000-stage-d-polish-onboarding.md">
<resolved original_question="i18n key prefix for shared expiration helpers — pantry vs planner?">
  <resolution>The shared `expirationTextKey()` helper accepts a `prefix` parameter (default "optimizer.pantry"). OptimizerRecipeCard passes "optimizer.planner" to reuse existing lowercase planner keys. Pantry page uses default pantry prefix with Title Case keys. Both key sets coexist — they have different capitalization for different display contexts.</resolution>
</resolved>
<resolved original_question="Should onboarding_completed be in Phase 1 (cross-phase) or Phase 4 (stretch-isolated)?">
  <resolution>Moved to Phase 4. Makes the stretch goal truly skippable — Phases 1-3 carry no unused schema surface. Phase 4 has its own migration chained after Phase 1's migration.</resolution>
</resolved>
</resolved_from_source>
