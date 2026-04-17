# Implementation Plan: Stage D — Polish & Onboarding
Source: docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md
Created: 2026-04-15

<plan_metadata>
  <feature>Stage D: Expiration Warnings, First-Run Import, Mobile Grid, Onboarding Wizard</feature>
  <source_doc>docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md</source_doc>
  <total_phases>5</total_phases>
  <total_tasks>16</total_tasks>
  <critical_path>1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3 → 2.4 → checkpoint → 3.1 → 3.2 → 3.3 → checkpoint → 5.1</critical_path>
  <status>reviewed</status>
</plan_metadata>

## Overview

Stage D adds four polish features to the Mealie optimizer fork: (1) expiration warning indicators on pantry items with sorted display, (2) a first-run import prompt when the pantry is empty, (3) a mobile-responsive planner grid using day accordions instead of a 7-column CSS grid, and (4) a stretch-goal onboarding wizard for new users. All new code lives in `optimizer/` directories per fork isolation rules.

## Dependencies & Prerequisites

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
  <description>Vuetify v-stepper component for onboarding wizard</description>
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
  <verification>ls mealie/alembic/versions/ | grep d4e5f6 — confirmed file exists at 2026-04-14-17.00.00</verification>
</prereq>
<prereq id="P7" type="library" verified="false">
  <description>Vuetify v-bottom-sheet for mobile sidebar overlay</description>
  <verification>Zero existing usage in codebase. Available in Vuetify 4 API but untested in this app. FALLBACK: use v-navigation-drawer (temporary, right-side) which is already used in AppSidebar.vue</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend — Config Fields, Migration, On-Hand Count Endpoint

<phase id="1" name="Backend Config & On-Hand Count">

### 1.1 Alembic Migration: Add Config Polish Fields

<task id="1.1" status="pending" depends="" risk="medium">
<description>
Create a new Alembic migration that adds two columns to the `optimizer_config` table:
- `expiration_warning_days`: Integer, server_default="3", NOT NULL
- `onboarding_completed`: Boolean, server_default="false", NOT NULL

The migration MUST chain after revision `d4e5f6a7b8c9` (add_slot_overlap_penalty_weight, file: `mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py`).

Follow the existing single-op migration pattern. See `mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py` for template.

File: `mealie/alembic/versions/2026-04-15-07.00.00_e5f6a7b8c9d0_add_config_polish_fields.py`
</description>

<subtasks>
- [ ] Create migration file with revision ID `e5f6a7b8c9d0`, down_revision `d4e5f6a7b8c9`
- [ ] `upgrade()`: add_column `expiration_warning_days` (sa.Integer, server_default="3", nullable=False)
- [ ] `upgrade()`: add_column `onboarding_completed` (sa.Boolean, server_default="false", nullable=False)
- [ ] `downgrade()`: drop both columns in reverse order
</subtasks>

<acceptance>
- `task py:migrate` applies the migration without error
- Existing optimizer_config rows have expiration_warning_days=3 and onboarding_completed=false
- `task py:migrate` downgrade removes both columns cleanly
</acceptance>

<rollback risk="medium">
If migration fails partway: run `alembic downgrade d4e5f6a7b8c9` to revert to previous head. If column already added partially, the downgrade will clean up.
</rollback>
</task>

### 1.2 SQLAlchemy Model + Pydantic Schema Updates

<task id="1.2" status="pending" depends="1.1" risk="low">
<description>
Add the two new fields to both the SQLAlchemy model and Pydantic schemas so they flow through the existing CRUD pipeline.

**SQLAlchemy model** (`mealie/db/models/optimizer/config.py`):
Add to OptimizerConfigModel class body (after `shelf_stable_label_keywords`):
```python
expiration_warning_days: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
```
Import `Boolean` from sqlalchemy (already imported: `JSON, Float, ForeignKey, Integer, UniqueConstraint`).

**Pydantic schema** (`mealie/schema/optimizer/config.py`):
Add to OptimizerConfigUpdate class body (after `shelf_stable_label_keywords`):
```python
expiration_warning_days: int = 3
onboarding_completed: bool = False
```
These fields auto-propagate to OptimizerConfigSave and OptimizerConfigOut via inheritance.
</description>

<subtasks>
- [ ] Add `Boolean` import to `mealie/db/models/optimizer/config.py`
- [ ] Add `expiration_warning_days` mapped column to OptimizerConfigModel
- [ ] Add `onboarding_completed` mapped column to OptimizerConfigModel
- [ ] Add `expiration_warning_days` field to OptimizerConfigUpdate in `mealie/schema/optimizer/config.py`
- [ ] Add `onboarding_completed` field to OptimizerConfigUpdate
</subtasks>

<acceptance>
- `task py:lint` passes
- GET /api/households/optimizer/config returns `expiration_warning_days` and `onboarding_completed` in response
- PUT /api/households/optimizer/config accepts both new fields and persists them
- Mealie's alias generator auto-converts to camelCase: `expirationWarningDays`, `onboardingCompleted`
</acceptance>
</task>

### 1.3 On-Hand Count Endpoint + Service Method

<task id="1.3" status="pending" depends="1.2" risk="low">
<description>
Add a lightweight GET endpoint to return the count of ingredient foods marked as on-hand for the current household. This count drives the frontend import prompt (only show when count > 0).

**IMPORTANT**: Use a count query, NOT a full relationship load. The existing `import_from_on_hand()` loads the full relationship, but counting should use SQL COUNT for efficiency.

**Schema** — Add to `mealie/schema/optimizer/pantry.py` (after existing classes):
```python
class OnHandCountResponse(MealieModel):
    count: int
```

**Service** — Add to `mealie/services/optimizer/pantry.py` PantryService class:
```python
def get_on_hand_count(self) -> int:
    """Count ingredient foods on-hand for this household using a count query."""
```
Implementation: Query the `households_to_ingredient_foods` join table, filtering by household_id, and return count. Reference the table import from `mealie/db/models/recipe/ingredient.py:21` (`households_to_ingredient_foods`).

**Route** — Add to `mealie/routes/optimizer/controller_pantry.py`:
```python
@router.get("/on-hand-count", response_model=OnHandCountResponse)
def get_on_hand_count(self) -> OnHandCountResponse:
```

**API Client** — Add to `frontend/app/lib/api/user/optimizer-pantry.ts`:
- Add route: `pantryOnHandCount: \`${prefix}/households/optimizer/pantry/on-hand-count\``
- Add method to PantryItemsApi: `async getOnHandCount()`
</description>

<subtasks>
- [ ] Add `OnHandCountResponse` schema to `mealie/schema/optimizer/pantry.py`
- [ ] Add `get_on_hand_count()` method to PantryService using a count query on `households_to_ingredient_foods` join table
- [ ] Add GET `/on-hand-count` endpoint to `controller_pantry.py`
- [ ] Add `pantryOnHandCount` route to `optimizer-pantry.ts`
- [ ] Add `getOnHandCount()` method to PantryItemsApi class
</subtasks>

<acceptance>
- GET /api/households/optimizer/pantry/on-hand-count returns `{"count": N}` matching actual on-hand food count
- Returns `{"count": 0}` when no on-hand foods exist for the household
- `task py:lint` passes
- The endpoint appears in Swagger at localhost:9000/docs under "Optimizer: Pantry"
</acceptance>
</task>

### 1.4 TypeScript Interface Updates

<task id="1.4" status="pending" depends="1.2" risk="low">
<description>
Update the TypeScript interfaces in `frontend/app/lib/api/types/optimizer.ts` to include the two new config fields. Although this file has a `pydantic2ts` auto-generated header, the optimizer types are NOT in the generation script (`dev/code-generation/gen_ts_types.py` has no optimizer references). These types are maintained manually despite the header.

Add to `OptimizerConfigUpdate` interface (after `shelfStableLabelKeywords`):
```typescript
expirationWarningDays: number;
onboardingCompleted: boolean;
```

These fields automatically appear in `OptimizerConfigOut` since it extends `OptimizerConfigUpdate`.
</description>

<subtasks>
- [ ] Add `expirationWarningDays: number` to OptimizerConfigUpdate interface
- [ ] Add `onboardingCompleted: boolean` to OptimizerConfigUpdate interface
- [ ] Verify OptimizerConfigOut inherits the new fields (it extends OptimizerConfigUpdate)
</subtasks>

<acceptance>
- `task ui:lint` passes
- No TypeScript compilation errors in files importing OptimizerConfigUpdate or OptimizerConfigOut
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `task py:lint` passes
- [ ] `task ui:lint` passes
- [ ] `task py:migrate` applies cleanly
- [ ] GET /api/households/optimizer/config returns `expirationWarningDays` and `onboardingCompleted` fields
- [ ] PUT /api/households/optimizer/config accepts and persists both new fields
- [ ] GET /api/households/optimizer/pantry/on-hand-count returns correct count
- [ ] Frontend API client `getOnHandCount()` method exists and TypeScript compiles
</verification>
<success_criteria>All backend schema changes are in place, the on-hand-count endpoint works, and TypeScript types match the backend. No frontend UI changes yet.</success_criteria>
</checkpoint>

</phase>

---

## Phase 2: Expiration Warnings + Import Prompt (Frontend)

<phase id="2" name="Expiration Warnings & First-Run Import" depends="1">

### 2.1 Create Expiration Helpers Composable + Tests

<task id="2.1" status="pending" depends="1.4" risk="low">
<description>
Create a new composable file with pure helper functions for expiration date calculations. These will be shared by PantryItemRow (pantry page) and OptimizerRecipeCard (planner page).

File: `frontend/app/composables/optimizer/use-expiration-helpers.ts`

Export these functions:

1. `daysToExpiry(expirationDate: string | null | undefined): number | null`
   - Returns null if no date
   - Returns 0 for today, negative for past dates, positive for future
   - Use date-fns `differenceInCalendarDays(parseISO(date), new Date())` for clean date math

2. `expirationSeverity(days: number | null, warningThreshold?: number): "expired" | "warning" | "ok" | "none"`
   - null → "none"
   - days < 0 → "expired"
   - days <= warningThreshold (default 3) → "warning"
   - days > warningThreshold → "ok"

3. `expirationColor(severity: "expired" | "warning" | "ok" | "none"): string`
   - "expired" → "error"
   - "warning" → "warning"
   - "ok" → "success"
   - "none" → "grey"

4. `expirationTextKey(days: number | null): { key: string; params?: Record<string, number> } | null`
   - null → null (no text)
   - days < 0 → `{ key: "optimizer.pantry.expired" }`
   - days === 0 → `{ key: "optimizer.pantry.expires-today" }`
   - days > 0 → `{ key: "optimizer.pantry.expires-in-days", params: { days } }`

5. `sortByExpiration(items: PantryItemOut[]): PantryItemOut[]`
   - Returns a NEW sorted array (does not mutate input)
   - Sort order: expired first (most negative first), then warning/ok ascending by daysToExpiry, then items with null expirationDate last
   - Stable sort within equal groups

Then create unit tests alongside:
File: `frontend/app/composables/optimizer/use-expiration-helpers.test.ts`

Test all 5 functions with edge cases: null dates, today, past, future, threshold boundaries, empty array, mixed array sorting.
</description>

<subtasks>
- [ ] Create `use-expiration-helpers.ts` with all 5 exported functions
- [ ] Import `differenceInCalendarDays` and `parseISO` from date-fns (already a project dependency)
- [ ] Import `PantryItemOut` type from `~/lib/api/types/optimizer`
- [ ] Create `use-expiration-helpers.test.ts` with vitest test suites
- [ ] Test `daysToExpiry()`: null, today, past (-2), future (+5)
- [ ] Test `expirationSeverity()`: all 4 return values + custom threshold
- [ ] Test `expirationColor()`: all 4 severity inputs
- [ ] Test `expirationTextKey()`: null, expired, today, future
- [ ] Test `sortByExpiration()`: empty array, mixed items, all-null dates, stable ordering
</subtasks>

<acceptance>
- `task ui:test` passes including new test file
- All exported functions have TypeScript types
- `task ui:lint` passes
</acceptance>
</task>

### 2.2 Modify PantryItemRow.vue — Expiration Warning Indicators

<task id="2.2" status="pending" depends="2.1" risk="low">
<description>
Add visual expiration warning indicators to each pantry item row. Currently PantryItemRow.vue (137 lines) is a v-card with inline editing fields. Add:

1. **New prop**: `warningThreshold?: number` (default 3)

2. **Computed properties** (script setup):
   - `itemDaysToExpiry` = `daysToExpiry(editItem.expirationDate)` (import from use-expiration-helpers)
   - `severity` = `expirationSeverity(itemDaysToExpiry, props.warningThreshold)`
   - `borderColor` = `expirationColor(severity)` (maps to Vuetify color name, resolve to CSS via `rgb(var(--v-theme-<color>))`)

3. **Template changes** to the v-card element (line 2):
   - Add dynamic style: `:style="severity !== 'none' ? { borderLeft: '4px solid rgb(var(--v-theme-' + borderColor + '))' } : {}"` on the v-card
   - After the expiration date input (line 71-80), add a v-chip when severity is "expired" or "warning":
     ```vue
     <v-chip v-if="severity === 'expired' || severity === 'warning'"
       size="small" :color="borderColor" variant="tonal" density="compact">
       {{ chipText }}
     </v-chip>
     ```
   - `chipText` computed: use `expirationTextKey(itemDaysToExpiry)` → pass to `$t()`

4. **Watch update**: Ensure `itemDaysToExpiry` recomputes when `editItem.expirationDate` changes via the existing reactive proxy.

Current file: `frontend/app/components/optimizer/PantryItemRow.vue` (137 lines)
Current props (line 101-105): `item`, `foods`, `units` — add `warningThreshold` with default.
</description>

<subtasks>
- [ ] Add `warningThreshold` optional prop with default value 3
- [ ] Import `daysToExpiry`, `expirationSeverity`, `expirationColor`, `expirationTextKey` from helpers
- [ ] Add computed properties: `itemDaysToExpiry`, `severity`, `borderColor`, `chipText`
- [ ] Add dynamic border-left style to v-card element
- [ ] Add v-chip after expiration date input for expired/warning items
- [ ] Use `useI18n()` for `$t()` in script setup (or rely on template `$t`)
</subtasks>

<acceptance>
- Item with expirationDate 2 days from now shows warning-colored left border and "Expires in 2 days" chip
- Item with expirationDate in the past shows error-colored left border and "Expired" chip
- Item with no expirationDate shows no border color and no chip
- Item with expirationDate 10 days out shows success-colored border, no chip
- `task ui:lint` passes
</acceptance>
</task>

### 2.3 Modify pantry.vue — Sort by Expiration + Import Prompt

<task id="2.3" status="pending" depends="2.2, 1.3" risk="medium">
<description>
Modify the pantry page to: (a) sort items by expiration status, (b) fetch config for warning threshold, and (c) show an import prompt when pantry is empty and on-hand foods exist.

File: `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` (~231 lines)

**Changes needed:**

1. **New imports**: `sortByExpiration` from helpers, `OptimizerConfigOut` type, `OptimizerApi` usage for config + on-hand count.

2. **New state variables**:
   - `config: Ref<OptimizerConfigOut | null>` — fetched on mount
   - `onHandCount: Ref<number>` — fetched on mount (default 0)
   - `importing: Ref<boolean>` — loading state for import button
   - `importResult: Ref<PantryImportResult | null>` — result after import

3. **Modified `fetchPantryItems()`**: After the API fetch, apply `sortByExpiration()` before assigning to the items ref.

4. **New `fetchOnHandCount()` function**: Call `api.optimizer.pantry.getOnHandCount()`, set `onHandCount` from response.

5. **New `onImportFromOnHand()` function**: Call `api.optimizer.pantry.importFromOnHand()`, set `importResult`, refresh pantry items list, show success snackbar with count.

6. **Parallel fetches on mount**: Fetch pantry items, config, and on-hand count in parallel with `Promise.all()`.

7. **Template changes to empty state** (currently lines 19-23):
   - Keep existing empty state card
   - Add conditional section inside empty state: when `onHandCount > 0`, show:
     - Text: `$t('optimizer.pantry.import-available', { count: onHandCount })`
     - Text: `$t('optimizer.pantry.import-prompt')`
     - Import button: `$t('optimizer.pantry.import-button')`, calls `onImportFromOnHand()`, loading state
   - When `onHandCount === 0`, show only the standard empty message (current behavior)

8. **Pass warningThreshold to PantryItemRow** (line 26-34):
   - Add prop: `:warning-threshold="config?.expirationWarningDays ?? 3"`

9. **Success snackbar for import**: Add v-snackbar for import result showing translated count.
</description>

<subtasks>
- [ ] Add new imports: sortByExpiration, config/on-hand API types
- [ ] Add state variables: config, onHandCount, importing, importResult
- [ ] Modify fetchPantryItems() to apply sortByExpiration() after fetch
- [ ] Add fetchOnHandCount() function
- [ ] Add onImportFromOnHand() function with error handling
- [ ] Update onMounted to fetch pantry items, config, and on-hand count in parallel
- [ ] Modify empty state template: conditional import prompt when onHandCount > 0
- [ ] Pass :warning-threshold to PantryItemRow
- [ ] Add success snackbar for import result
</subtasks>

<acceptance>
- Pantry items display sorted: expired first, expiring-soon next, no-date last
- Empty pantry with on-hand foods shows import prompt with correct count
- Empty pantry with zero on-hand foods shows only the standard empty message
- Clicking import calls importFromOnHand(), refreshes list, shows success toast with imported/skipped counts
- After import, empty state disappears and imported items are listed (sorted)
- PantryItemRow receives correct warningThreshold from config
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
If import prompt causes issues, the empty state can be reverted by removing the v-if/v-else on onHandCount. The sort change is independent and low-risk.
</rollback>
</task>

### 2.4 Refactor OptimizerRecipeCard.vue — Use Shared Helpers

<task id="2.4" status="pending" depends="2.1" risk="low">
<description>
Replace the local `matchColor()` and `expirationText()` functions in OptimizerRecipeCard.vue with the shared helpers from use-expiration-helpers.ts.

File: `frontend/app/components/optimizer/OptimizerRecipeCard.vue` (~140 lines)

**Current local functions** (lines 98-108):
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

**Replace with**:
```javascript
import { expirationColor, expirationSeverity, expirationTextKey } from "~/composables/optimizer/use-expiration-helpers";

function matchColor(match: PantryMatchDetail): string {
  return expirationColor(expirationSeverity(match.daysToExpiry));
}

function expirationText(match: PantryMatchDetail): string {
  const info = expirationTextKey(match.daysToExpiry);
  if (!info) return "";
  return t(info.key, info.params ?? {});
}
```

This preserves the function signatures and template usage (lines 53, 60) — callers don't change.

**Behavior note**: The new `expirationSeverity()` uses threshold=3 by default, which matches the current hardcoded `<= 3` check. The color mapping changes slightly: current code returns "warning" for <=3 days and "success" otherwise. The new code will return "error" for expired (<0), "warning" for 0-3, and "success" for >3. This is an intentional improvement — expired items should show error, not warning.
</description>

<subtasks>
- [ ] Add import for `expirationColor`, `expirationSeverity`, `expirationTextKey` from helpers
- [ ] Replace `matchColor()` function body with shared helper calls
- [ ] Replace `expirationText()` function body with shared helper calls
- [ ] Remove any unused imports after refactor
</subtasks>

<acceptance>
- Recipe cards in the planner sidebar display expiration text and colors correctly
- Expired matches now show "error" color (red) instead of "warning" (orange) — intentional improvement
- Warning matches (0-3 days) still show "warning" color
- OK matches (>3 days) still show "success" color
- `task ui:lint` passes
- `task ui:test` passes (scoring engine tests should not be affected)
</acceptance>
</task>

### 2.5 i18n Keys — Expiration & Import

<task id="2.5" status="pending" depends="" risk="low">
<description>
Add i18n translation keys for expiration warnings and import prompt to `frontend/app/lang/messages/en-US.json`.

Add under the existing `"optimizer"."pantry"` section (which already has keys like "title", "add-item", etc.):

```json
"expired": "Expired",
"expires-soon": "Expires soon",
"expires-in-days": "Expires in {days} day | Expires in {days} days",
"expires-today": "Expires today",
"expiration-warning-days": "Expiration Warning (days)",
"import-available": "You have {count} food marked as on-hand | You have {count} foods marked as on-hand",
"import-prompt": "Import them to your pantry to start tracking quantities?",
"import-button": "Import to Pantry",
"import-success": "Imported {imported} item, skipped {skipped} duplicate | Imported {imported} items, skipped {skipped} duplicates"
```

**Note on pluralization**: Vue I18n uses `|` pipe separator for singular|plural forms. The `{count}`, `{days}`, `{imported}`, `{skipped}` values drive pluralization.

Find the pantry section in en-US.json (around line 1484) and add these keys after the existing pantry keys.
</description>

<subtasks>
- [ ] Add expiration-related keys: expired, expires-soon, expires-in-days, expires-today
- [ ] Add config key: expiration-warning-days
- [ ] Add import-related keys: import-available, import-prompt, import-button, import-success
- [ ] Verify JSON is valid after edit (no trailing commas, proper nesting)
</subtasks>

<acceptance>
- `task ui:lint` passes
- All new keys resolve without warnings when used in templates
- Pluralization works for count-dependent strings (1 vs 2+)
</acceptance>
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
<success_criteria>Expiration warnings display correctly on pantry page and recipe cards. Import prompt works for empty pantry. All tests pass.</success_criteria>
</checkpoint>

</phase>

---

## Phase 3: Mobile-Responsive Planner Grid

<phase id="3" name="Mobile-Responsive Grid" depends="2">

### 3.1 PlanGrid.vue — Responsive Layout with Day Accordion

<task id="3.1" status="pending" depends="2.5" risk="high">
<description>
Modify PlanGrid.vue to render differently based on screen size: CSS grid on desktop (existing behavior), v-expansion-panels accordion on mobile.

File: `frontend/app/components/optimizer/PlanGrid.vue` (95 lines currently)

**Script changes**:
- Import `useDisplay` from "vuetify"
- Add `const { smAndDown } = useDisplay()`

**Template changes** — wrap existing grid in a v-if/v-else:

**Desktop (v-if="!smAndDown")**: Keep the existing CSS grid template exactly as-is (lines 2-35).

**Mobile (v-else)**: New v-expansion-panels layout:
```
<v-expansion-panels v-model="expandedDay" variant="accordion">
  <v-expansion-panel v-for="day in days" :key="formatDate(day)" :value="formatDate(day)">
    <v-expansion-panel-title>
      <span class="font-weight-bold">{{ formatDayHeader(day) }}</span>
      <v-badge :content="dayEntryCount(day)" color="primary" inline />
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <div v-for="entryType in entryTypes" :key="entryType" class="mb-2">
        <span class="text-caption font-weight-medium text-grey mb-1 d-block">
          {{ $t("meal-plan." + entryType) }}
        </span>
        <PlanSlot ... />
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>
</v-expansion-panels>
```

**New computed/state**:
- `expandedDay`: Ref initialized to today's formatted date (show today expanded by default, others collapsed)
- `dayEntryCount(day: Date): number`: Count all entries across all entry types for that day

**Event wiring**: PlanSlot in both layouts must emit the same events (slot-click, slot-drop, entry-remove) with the same payload format. The mobile PlanSlot instances use identical props and event bindings as the desktop version.

**Considerations from Codex review**:
- If the v-if/v-else template becomes unwieldy (>150 lines total), extract mobile layout into a separate `PlanGridMobile.vue` component. For now, start with v-if/v-else and refactor if needed.
- Test that accordion expansion/collapse does NOT interfere with slot click events.
</description>

<subtasks>
- [ ] Import useDisplay from vuetify
- [ ] Add smAndDown responsive detection
- [ ] Add expandedDay ref (default: today's date formatted)
- [ ] Add dayEntryCount() helper function
- [ ] Wrap existing grid template in v-if="!smAndDown"
- [ ] Add v-else mobile accordion template with v-expansion-panels
- [ ] Wire PlanSlot events identically in both layouts
- [ ] Add entry count badge to accordion panel headers
- [ ] Test desktop layout is unchanged (>= md breakpoint)
- [ ] Test mobile layout renders accordion with today expanded
</subtasks>

<acceptance>
- On screens >= md: 7-column CSS grid renders identically to current layout
- On screens < md: day accordion renders with one expandable panel per day
- Today's panel is expanded by default, others collapsed
- Each accordion panel header shows entry count badge
- slot-click, slot-drop, entry-remove events fire correctly in both layouts
- `task ui:lint` passes
</acceptance>

<rollback risk="high">
If the accordion layout has event propagation issues, revert by removing the v-if/v-else and keeping only the desktop grid. The existing overflow-x scroll on mobile is functional (just not optimal).
</rollback>
</task>

### 3.2 PlanSlot.vue + OptimizerRecipeCard.vue — Touch Interaction Fixes

<task id="3.2" status="pending" depends="3.1" risk="medium">
<description>
Fix touch-device usability issues in PlanSlot.vue and OptimizerRecipeCard.vue.

**PlanSlot.vue** (`frontend/app/components/optimizer/PlanSlot.vue`, 194 lines):

1. **Touch detection**: Add computed `isTouchDevice` using `window.matchMedia('(pointer: coarse)').matches`. Wrap in `onMounted` or use a computed with SSR guard (`import.meta.client`).

2. **Remove button visibility**: Currently `.plan-slot__remove` uses `opacity: 0` + hover to reveal (lines 171-179). On touch devices, hover doesn't work. Fix:
   - Add CSS: `@media (pointer: coarse) { .plan-slot__remove { opacity: 1; } }`
   - Or use class binding: `:class="{ 'always-visible': isTouchDevice }"`

3. **Touch target sizes**: Increase min-height on mobile. Add CSS variable:
   ```css
   .plan-slot { min-height: var(--slot-min-height, 80px); }
   @media (pointer: coarse) { .plan-slot { --slot-min-height: 56px; } }
   ```
   (56px is actually smaller since accordion gives more vertical context per day)

**OptimizerRecipeCard.vue** (`frontend/app/components/optimizer/OptimizerRecipeCard.vue`):

1. **Disable draggable on touch**: The card currently has `draggable="true"` and `@dragstart="onDragStart"`. On touch devices, native HTML5 drag doesn't work and can cause scroll interference.
   - Add touch detection (same pattern as PlanSlot)
   - Conditionally set `:draggable="!isTouchDevice"` and conditionally bind `@dragstart`
   - On touch devices, the card is already tappable via `@click="emit('select', recipe.recipeId)"` which is the correct mobile interaction

**Mobile interaction flow**: On mobile, the user taps a slot (activates it via slot-click), then taps a recipe card in the sidebar (fires select event which calls addToDraft). No drag needed — this flow already works via the existing click/select events.
</description>

<subtasks>
- [ ] PlanSlot.vue: Add touch device detection (pointer: coarse media query in CSS)
- [ ] PlanSlot.vue: Make remove button always visible on touch devices
- [ ] PlanSlot.vue: Adjust slot min-height via CSS custom property for touch
- [ ] OptimizerRecipeCard.vue: Add touch device detection
- [ ] OptimizerRecipeCard.vue: Conditionally disable draggable attribute on touch
- [ ] OptimizerRecipeCard.vue: Ensure click/select events still work as primary mobile interaction
- [ ] Remove drag cursor styling on touch devices
</subtasks>

<acceptance>
- On touch devices: remove button always visible (not hover-dependent)
- On touch devices: recipe cards are not draggable, no drag cursor
- On touch devices: tapping a slot activates it, tapping a recipe adds it to slot
- Desktop behavior completely unchanged (drag-drop still works, hover reveals remove button)
- `task ui:lint` passes
</acceptance>
</task>

### 3.3 planner.vue — Mobile Sidebar Toggle + Layout Refinements

<task id="3.3" status="pending" depends="3.1" risk="medium">
<description>
Add a mobile sidebar toggle and layout refinements to the planner page.

File: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` (~320 lines)

**Script changes**:
1. Import `useDisplay` from "vuetify"
2. Add `const { smAndDown } = useDisplay()`
3. Add state: `const showSidebar = ref(false)` (hidden by default on mobile)

**Template changes**:

1. **Right panel (v-col cols="12" md="4")** at line 120:
   - Desktop: Keep as-is (always visible)
   - Mobile: Wrap ConfigPanel + SuggestionSidebar content in a `v-dialog` (fullscreen on mobile) or a conditionally-shown panel
   - Use `v-show="!smAndDown || showSidebar"` on the v-col
   - When showSidebar is true on mobile, the sidebar v-col renders full-width below the grid

   **Rationale for v-dialog over v-bottom-sheet**: v-bottom-sheet has zero usage in this app (higher integration risk per Codex review). A fullscreen v-dialog on mobile is a proven pattern.

2. **FAB toggle button** (only on mobile):
   ```vue
   <v-btn v-if="smAndDown" icon color="primary" class="sidebar-fab"
     style="position: fixed; bottom: 16px; right: 16px; z-index: 10;"
     @click="showSidebar = !showSidebar">
     <v-icon>{{ showSidebar ? '$mdi-close' : '$mdi-chef-hat' }}</v-icon>
   </v-btn>
   ```

3. **Action buttons** (lines 87-116): Stack vertically on mobile:
   - Change `class="d-flex gap-2 mt-4"` to `class="d-flex mt-4" :class="smAndDown ? 'flex-column gap-1' : 'gap-2'"`

4. **Recipe selection on mobile**: When a recipe is selected from the sidebar on mobile, auto-close the sidebar:
   - In the `onRecipeSelect` handler, add: `if (smAndDown.value) showSidebar.value = false;`

5. **Date picker**: On mobile, the date picker button should be full-width for easier tapping:
   - Add `:block="smAndDown"` to the date picker v-btn
</description>

<subtasks>
- [ ] Import useDisplay, add smAndDown and showSidebar state
- [ ] Add v-show or v-if on right panel for mobile sidebar toggle
- [ ] Add FAB button (fixed position, bottom-right) visible only on smAndDown
- [ ] Stack action buttons vertically on mobile using flex-column
- [ ] Auto-close sidebar on recipe selection when on mobile
- [ ] Make date picker button full-width on mobile
- [ ] Verify desktop layout is completely unchanged
</subtasks>

<acceptance>
- On desktop: sidebar always visible, no FAB shown, layout identical to current
- On mobile: sidebar hidden by default, FAB visible at bottom-right
- Tapping FAB shows sidebar content, tapping again (or X icon) hides it
- Selecting a recipe from mobile sidebar adds it to active slot and closes sidebar
- Action buttons stack vertically on mobile screens
- Date picker is full-width on mobile
- `task ui:lint` passes
</acceptance>
</task>

### 3.4 i18n Keys — Mobile Planner

<task id="3.4" status="pending" depends="" risk="low">
<description>
Add i18n translation keys for mobile planner features to `frontend/app/lang/messages/en-US.json`.

Add under the existing `"optimizer"."planner"` section:

```json
"show-suggestions": "Show Suggestions",
"hide-suggestions": "Hide Suggestions",
"day-entries": "{count} meal | {count} meals"
```
</description>

<subtasks>
- [ ] Add show-suggestions, hide-suggestions, day-entries keys to optimizer.planner section
- [ ] Verify JSON validity
</subtasks>

<acceptance>
- `task ui:lint` passes
- Keys resolve in templates
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
<success_criteria>Planner works well on both desktop and mobile. Mobile uses accordion layout with tap interactions. Desktop is completely unchanged.</success_criteria>
</checkpoint>

</phase>

---

## Phase 4: Onboarding Wizard (Stretch Goal)

<phase id="4" name="Onboarding Wizard" depends="1">

### 4.1 Create Setup Wizard Page

<task id="4.1" status="pending" depends="1.4, 2.5" risk="medium">
<description>
Create a new page at `frontend/app/pages/g/[groupSlug]/optimizer/setup.vue` with a 4-step onboarding wizard following the pattern in `frontend/app/pages/admin/setup.vue`.

**Pattern reference**: admin/setup.vue uses:
- `v-stepper v-model="currentPage" mobile-breakpoint="sm" alt-labels`
- `v-stepper-header` with `v-stepper-item` for each step
- `v-stepper-window` with `v-stepper-window-item` for step content
- `v-stepper-actions` with prev/next buttons per step

**Wizard steps**:

**Step 1 — Welcome** (value: 1):
- Title: `$t('optimizer.onboarding.welcome-title')`
- Description: `$t('optimizer.onboarding.welcome-description')`
- Actions: Next button only

**Step 2 — Pantry** (value: 2):
- Intro text: `$t('optimizer.onboarding.import-intro')`
- If onHandCount > 0: Show import button with count
- After import: Show list of imported PantryItemRow components for review/editing
- Manual "Add more" button to add individual items
- Actions: Back / Next

**Step 3 — Config** (value: 3):
- Intro text: `$t('optimizer.onboarding.config-intro')`
- Embed `<ConfigPanel :config="config" @update="onConfigUpdate" />` — verify ConfigPanel works standalone (it's currently used only in planner.vue)
- Actions: Back / Next

**Step 4 — Done** (value: 4):
- Title: `$t('optimizer.onboarding.done-title')`
- Description: `$t('optimizer.onboarding.done-description', { pantryCount: pantryItems.length })`
- "Go to Meal Planner" button → `navigateTo('/g/' + groupSlug + '/optimizer/planner')`
- On reaching this step, call `api.optimizer.config.updateConfig({ ...config, onboardingCompleted: true })`

**Skip button**: Available on every step. Calls `updateConfig({ onboardingCompleted: true })` and navigates to planner.

**State management**:
- Fetch config, pantry items, and on-hand count on mount (reuse patterns from pantry.vue)
- Track currentStep, importing, importResult, pantryItems, config, onHandCount

**Revisiting**: If user visits /optimizer/setup after completion, the wizard still renders with current state (not blocked). This allows reconfiguration.
</description>

<subtasks>
- [ ] Create `frontend/app/pages/g/[groupSlug]/optimizer/setup.vue`
- [ ] Implement 4-step v-stepper following admin/setup.vue pattern
- [ ] Step 1: Welcome with title and description
- [ ] Step 2: Pantry import (conditional on onHandCount) + PantryItemRow list + manual add
- [ ] Step 3: ConfigPanel embed with intro text
- [ ] Step 4: Done summary with pantry count + "Go to Planner" button
- [ ] Set onboardingCompleted=true on reaching Step 4 or clicking Skip
- [ ] Fetch config, pantry items, on-hand count on mount
- [ ] Add Skip button on every step
- [ ] Set page SEO title
- [ ] Mobile-responsive: mobile-breakpoint="sm" on v-stepper
</subtasks>

<acceptance>
- 4-step wizard renders with v-stepper, mobile-responsive
- Step 2 shows import button only when on-hand count > 0
- Step 2 displays imported items for review
- Step 3 embeds working ConfigPanel with weight sliders
- Completing wizard sets onboardingCompleted=true on server
- Skip button available on every step, sets flag and navigates to planner
- Revisiting /optimizer/setup after completion shows wizard with current state
- `task ui:lint` passes
</acceptance>

<rollback risk="medium">
This is a new page — can be deleted entirely without affecting existing functionality.
</rollback>
</task>

### 4.2 Planner Onboarding Banner

<task id="4.2" status="pending" depends="4.1" risk="low">
<description>
Add a dismissible onboarding banner to the planner page for first-time users.

File: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue`

**Behavior**:
- After config loads in `loadData()`, check `config.onboardingCompleted === false`
- Show a non-blocking v-alert banner above the grid
- Banner has two actions: "Start Setup" (navigates to /optimizer/setup) and "Dismiss" (sets onboardingCompleted=true via API, hides banner)
- Do NOT auto-redirect — the planner must be usable without completing onboarding

**Template addition** (after unlinked-recipes-hint alert, before v-row):
```vue
<v-alert
  v-if="config && !config.onboardingCompleted && !onboardingDismissed"
  type="info"
  variant="tonal"
  class="mb-4"
  closable
  @click:close="dismissOnboarding"
>
  {{ $t('optimizer.onboarding.setup-banner') }}
  <template #append>
    <v-btn size="small" variant="text" color="primary"
      :to="`/g/${groupSlug}/optimizer/setup`">
      {{ $t('optimizer.onboarding.start-setup') }}
    </v-btn>
  </template>
</v-alert>
```

**Script additions**:
- `const onboardingDismissed = ref(false)` — local session state (disappears on page reload, but persists server-side)
- `async function dismissOnboarding()`: Call `updateConfig({ ...config, onboardingCompleted: true })`, set `onboardingDismissed = true`

**Distinction**: "Dismiss" sets `onboardingCompleted=true` server-side (permanent). The banner will not appear on any future visit.
</description>

<subtasks>
- [ ] Add onboardingDismissed local ref
- [ ] Add dismissOnboarding() function that calls config update API
- [ ] Add v-alert banner template after existing alerts
- [ ] Banner shows "Start Setup" link and "Dismiss" close button
- [ ] Banner only shows when config.onboardingCompleted is false
- [ ] Verify planner is fully usable even when banner is shown
</subtasks>

<acceptance>
- First visit with onboardingCompleted=false shows setup banner
- Banner has "Start Setup" link to /optimizer/setup
- Banner has dismiss button that sets onboardingCompleted=true
- Subsequent visits with onboardingCompleted=true show no banner
- Banner does not block planner usage
- `task ui:lint` passes
</acceptance>
</task>

### 4.3 DefaultLayout.vue — Conditional Setup Nav Link

<task id="4.3" status="pending" depends="4.2" risk="medium">
<description>
Add a conditional "Optimizer Setup" nav link that only appears when onboarding is not completed.

File: `frontend/app/components/Layout/DefaultLayout.vue`

**Challenge**: The layout needs to fetch optimizer config to know whether to show the link. This crosses layout-level navigation logic (flagged by Codex review).

**Approach**: Fetch config lazily and cache it. Add a new computed nav item that conditionally includes the setup link.

**Current nav structure** (lines 250-260): Two optimizer links exist (Pantry and Planner) in the `topLinks` computed array.

**Add a third link** after the planner link:
```javascript
{
  icon: "$mdi-school",
  title: t("optimizer.onboarding.setup"),
  to: `/g/${groupSlug}/optimizer/setup`,
  restricted: true,
}
```

**Conditional display**: Rather than fetching config in the global layout (which would add an API call on every page load), use a simpler approach:
- Add the link unconditionally to the nav
- The setup page itself works regardless of onboarding status
- This avoids the flicker/extra-API-call problem flagged by Codex

**Alternative (if user wants conditional)**: Fetch config once on layout mount, cache in a composable. Only show link when `!config.onboardingCompleted`. Accept the initial API call cost.

**Recommended**: Add unconditionally. The setup page is always useful for reconfiguration. The nav item is small and doesn't clutter.
</description>

<subtasks>
- [ ] Add "Optimizer Setup" link to topLinks in DefaultLayout.vue
- [ ] Position after existing Pantry and Planner links
- [ ] Use $mdi-school icon and optimizer.onboarding.setup i18n key
- [ ] Set restricted: true
</subtasks>

<acceptance>
- "Optimizer Setup" nav link appears in sidebar below Pantry and Planner
- Link navigates to /optimizer/setup page
- `task ui:lint` passes
</acceptance>
</task>

### 4.4 i18n Keys — Onboarding

<task id="4.4" status="pending" depends="" risk="low">
<description>
Add i18n translation keys for the onboarding wizard to `frontend/app/lang/messages/en-US.json`.

Add a new section `"onboarding"` under `"optimizer"`:

```json
"onboarding": {
  "setup": "Optimizer Setup",
  "welcome-title": "Welcome to the Meal Optimizer",
  "welcome-description": "Let's set up your pantry and preferences to get personalized meal suggestions.",
  "step-pantry": "Pantry",
  "step-config": "Preferences",
  "step-done": "Ready!",
  "import-intro": "Import foods you already have on hand to get started quickly.",
  "config-intro": "Adjust how the optimizer ranks recipe suggestions. Defaults work well for most households.",
  "done-title": "You're all set!",
  "done-description": "Your optimizer is configured with {pantryCount} pantry items.",
  "go-to-planner": "Start Planning Meals",
  "skip": "Skip Setup",
  "setup-banner": "New to the meal optimizer?",
  "start-setup": "Start Setup",
  "dismiss": "Dismiss"
}
```
</description>

<subtasks>
- [ ] Add optimizer.onboarding section with all keys
- [ ] Verify JSON validity
</subtasks>

<acceptance>
- `task ui:lint` passes
- All onboarding i18n keys resolve in templates
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes
- [ ] /optimizer/setup page renders 4-step wizard
- [ ] Import step works when on-hand foods exist
- [ ] ConfigPanel works in wizard context
- [ ] Completing wizard sets onboardingCompleted=true
- [ ] Skip works from any step
- [ ] Planner shows onboarding banner when not completed
- [ ] Planner hides banner after dismiss or completion
- [ ] Setup nav link appears in sidebar
- [ ] All i18n keys resolve
</verification>
<success_criteria>Onboarding wizard guides new users through setup. Banner and nav link surface the wizard. Planner is never blocked.</success_criteria>
</checkpoint>

</phase>

---

## Phase 5: Final Validation

<phase id="5" name="Final Validation" depends="2,3,4">

### 5.1 End-to-End Smoke Test

<task id="5.1" status="pending" depends="4.4" risk="low">
<description>
Run all checks and perform manual smoke testing of every Stage D feature.

**Automated checks**:
1. `task py:lint` — Python linting
2. `task ui:lint` — Frontend linting
3. `task ui:test` — Frontend tests (scoring-engine + expiration helpers)
4. `task py:migrate` — Migration applies cleanly

**Manual smoke test flow** (requires dev servers running):
1. Start fresh: Reset optimizer config (delete row or set onboarding_completed=false)
2. Visit /optimizer/planner — verify onboarding banner appears
3. Click "Start Setup" — wizard loads at /optimizer/setup
4. Step 2: If on-hand foods exist, import them. Review imported items.
5. Step 3: Adjust a weight slider. Verify it saves.
6. Step 4: Click "Start Planning Meals" — navigates to planner, banner gone
7. Visit /optimizer/pantry — verify items sorted by expiration
8. Add item with expiration 2 days out — warning chip appears
9. Add item with past expiration — error chip appears
10. Resize browser to mobile width — planner switches to accordion, FAB appears
11. Tap FAB — sidebar shows. Tap recipe — adds to slot, sidebar closes
12. Verify desktop layout unchanged at full width
</description>

<subtasks>
- [ ] Run `task py:lint`
- [ ] Run `task ui:lint`
- [ ] Run `task ui:test`
- [ ] Run `task py:migrate`
- [ ] Manual: Onboarding flow (banner → wizard → planner)
- [ ] Manual: Expiration warnings on pantry page
- [ ] Manual: Import prompt on empty pantry
- [ ] Manual: Mobile responsive planner (accordion + FAB + touch)
- [ ] Manual: Desktop planner unchanged
- [ ] Manual: No regressions in existing CRUD operations
</subtasks>

<acceptance>
- All automated checks pass
- All manual smoke test steps complete successfully
- No console errors in browser devtools
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] All Phase 1-4 checkpoints verified
- [ ] All automated lint/test/migration checks pass
- [ ] Manual smoke test completed
</verification>
<success_criteria>Stage D is complete. All features work on desktop and mobile. No regressions.</success_criteria>
</checkpoint>

</phase>

---

## Final Validation

<final_validation>
<verification>
- [ ] `task py:lint` passes
- [ ] `task ui:lint` passes
- [ ] `task ui:test` passes (scoring-engine + expiration helper tests)
- [ ] `task py:migrate` applies and downgrades cleanly
- [ ] Pantry page: items sorted by expiration, warning indicators display correctly
- [ ] Pantry page: import prompt shows when empty + on-hand foods exist
- [ ] Planner page: mobile accordion layout works with tap interactions
- [ ] Planner page: desktop layout completely unchanged
- [ ] Planner page: sidebar FAB toggle works on mobile
- [ ] Onboarding wizard: 4-step flow works end-to-end
- [ ] Onboarding banner: appears and dismisses correctly
- [ ] Recipe cards: expiration colors use shared helpers
- [ ] All i18n keys resolve without warnings
- [ ] No regressions in existing optimizer features
</verification>
<acceptance>Stage D features (expiration warnings, import prompt, mobile grid, onboarding wizard) are all functional, tested, and do not regress existing Stages A-C functionality.</acceptance>
</final_validation>

---

## Dependency Verification Log

<dependency_log>
<dependency name="Vuetify useDisplay()" verified="true">
  <version>Vuetify 4 (compat v4)</version>
  <verified_via>Grep: 10+ existing usages across codebase (DefaultLayout.vue, AppHeader.vue, shopping-lists/[id].vue, etc.)</verified_via>
  <notes>Provides smAndDown, mdAndUp breakpoints. Safe to use.</notes>
</dependency>
<dependency name="Vuetify v-expansion-panels" verified="true">
  <version>Vuetify 4</version>
  <verified_via>Grep: 6 files use it (ConfigPanel.vue, shopping-lists/[id].vue, cookbooks/index.vue, etc.)</verified_via>
  <notes>Supports variant="accordion", v-model for expanded panel tracking.</notes>
</dependency>
<dependency name="Vuetify v-stepper" verified="true">
  <version>Vuetify 4</version>
  <verified_via>Read: frontend/app/pages/admin/setup.vue uses v-stepper with mobile-breakpoint="sm", alt-labels</verified_via>
  <notes>Full wizard pattern verified. Includes v-stepper-header, v-stepper-item, v-stepper-window, v-stepper-window-item, v-stepper-actions.</notes>
</dependency>
<dependency name="Vuetify v-bottom-sheet" verified="false">
  <version>Vuetify 4</version>
  <verified_via>Grep: zero usage in codebase</verified_via>
  <notes>REJECTED per Codex review — higher integration risk. Plan uses v-dialog fullscreen or conditional v-show instead for mobile sidebar.</notes>
</dependency>
<dependency name="date-fns" verified="true">
  <version>Already in project dependencies</version>
  <verified_via>PlanGrid.vue imports { format } from "date-fns". scoring-engine uses date-fns functions.</verified_via>
  <notes>Need differenceInCalendarDays and parseISO for expiration helpers.</notes>
</dependency>
<dependency name="household.ingredient_foods_on_hand" verified="true">
  <version>SQLAlchemy many-to-many relationship</version>
  <verified_via>Read: mealie/db/models/household/household.py:72 — relationship defined. mealie/services/optimizer/pantry.py:247 — used by import_from_on_hand().</verified_via>
  <notes>Join table: households_to_ingredient_foods. NOT the deprecated IngredientFoodModel.on_hand boolean.</notes>
</dependency>
<dependency name="pydantic2ts (TS type generation)" verified="true">
  <version>Used in dev/code-generation/gen_ts_types.py</version>
  <verified_via>Grep: optimizer.ts has auto-generated header but is NOT in gen_ts_types.py script</verified_via>
  <notes>Optimizer types are manually maintained despite the header. Direct editing is correct approach.</notes>
</dependency>
<dependency name="Alembic migration chain" verified="true">
  <version>Head: d4e5f6a7b8c9</version>
  <verified_via>ls mealie/alembic/versions/ — confirmed 4 optimizer migrations, latest is 2026-04-14-17.00.00_d4e5f6a7b8c9</verified_via>
  <notes>New migration must use down_revision="d4e5f6a7b8c9". Codex correctly identified this was NOT c3d4e5f6a7b8 as the spec assumed.</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should the mobile accordion show all days expanded by default, or only today?</question>
  <impact>Affects initial scroll depth and discoverability on mobile</impact>
  <default_assumption>Show today expanded, others collapsed — reduces initial scroll depth. Implemented via expandedDay ref initialized to today's date.</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should the onboarding wizard be accessible after completion (for re-configuration)?</question>
  <impact>Whether to block or allow /optimizer/setup after onboardingCompleted=true</impact>
  <default_assumption>Yes — /optimizer/setup always works. Nav link is always visible (simplified from conditional per Codex recommendation to avoid layout-level API calls).</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
  <question>Should expiration sorting persist across sessions or always apply on load?</question>
  <impact>Whether to add a persisted sort preference</impact>
  <default_assumption>Always apply on load — no persisted sort preference needed.</default_assumption>
</question>
<question id="Q4" blocking="false">
  <question>Should both ConfigPanel and SuggestionSidebar move into the mobile sidebar overlay, or only SuggestionSidebar?</question>
  <impact>Affects mobile planner flow — config changes are infrequent, suggestions are core workflow</impact>
  <default_assumption>Both move into the sidebar v-col which is toggled by the FAB. ConfigPanel is above SuggestionSidebar, matching desktop layout. Users can scroll within the sidebar.</default_assumption>
</question>
<question id="Q5" blocking="false">
  <question>Should the setup nav link be conditional (hidden after onboarding) or always visible?</question>
  <impact>Conditional requires config fetch in layout (extra API call on every page). Always visible is simpler but adds a permanent nav item.</impact>
  <default_assumption>Always visible — avoids layout-level API call, allows reconfiguration. Per Codex recommendation to avoid config fetch timing issues in global layout.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-15-064800-stage-d-polish-onboarding.md">
<resolved original_question="Should the FAB sidebar toggle use v-bottom-sheet or v-navigation-drawer for the mobile sidebar?">
  <resolution>Neither. Per Codex review, v-bottom-sheet has zero codebase usage (integration risk). Plan uses a simpler approach: v-show toggle on the existing sidebar v-col, making it conditionally visible. The FAB toggles showSidebar ref. No new component needed — the sidebar content renders at full width below the grid when shown on mobile.</resolution>
</resolved>
<resolved original_question="Does IngredientFoodModel.on_hand exist as a queryable boolean field?">
  <resolution>Yes, it exists at mealie/db/models/recipe/ingredient.py:192 but is marked "Deprecated". The correct approach (already used by import_from_on_hand) is to query the households_to_ingredient_foods many-to-many join table. The on-hand-count endpoint will use a count query on this join table filtered by household_id.</resolution>
</resolved>
</resolved_from_source>

---

## Plan Review Notes

<review_notes>
<codex_response>
Codex (GPT-5) review with focus="planning" identified the following:

**Dependency risks:**
- Migration base is stale: `optimizer_config` already has a later migration after `c3d4e5f6a7b8`: `d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py`. New work should chain after that, not after `c3d4...`.
- The frontend TS types are generated, not hand-maintained. `frontend/app/lib/api/types/optimizer.ts` explicitly says it is generated from Pydantic models.
- `v-bottom-sheet` is probably available via Vuetify, but there is no existing usage in this app. That makes it a higher integration risk than the plan implies.
- Mobile drag/drop is the biggest runtime risk. Disabling draggable on touch avoids breakage, but it does not provide an alternative mobile placement interaction by itself.

**Architectural alignment:**
- Storing `onboarding_completed` on `optimizer_config` fits well. `RepositoryOptimizerConfig.get_or_create_default()` already guarantees a per-household row.
- The `GET /pantry/on-hand-count` endpoint should use a count query, not relationship load.
- The onboarding nav change crosses layout-level navigation logic — needs explicit attention.

**Task atomicity:**
- Phase 1 mixes migration, ORM/schema, endpoint, service, and frontend types — should be split.
- Phase 3 is too coarse — contains layout model, touch interaction, planner composition, and drag behavior changes.

**Hidden complexity:**
- "Add fields to TypeScript interfaces" — hidden step: regenerate generated API types.
- "Sort items by expiration" — hidden step: define exact ordering for null, expired, today, future.
- "Accordion on mobile" — hidden step: preserve slot selection, add/remove actions, discoverability.
- "v-bottom-sheet for mobile sidebar" — hidden step: decide whether ConfigPanel and SuggestionSidebar both move.
- "Conditional Setup nav link" — hidden step: nav rendering depends on optimizer config fetch timing.

Specific recommendations: rebase migration off d4e5f6a7b8c9; change TS edits to regeneration; separate dismissed from completed onboarding; treat nav/banner as shared state work.
</codex_response>

<changes_made>
Based on Codex feedback, the following changes were made to the plan:

1. **Migration rebase**: Fixed migration down_revision to chain after `d4e5f6a7b8c9` (not `c3d4e5f6a7b8`). Verified via filesystem listing.

2. **TS types approach**: Investigated Codex's claim about regeneration. Found that optimizer.ts has the auto-generated header BUT is NOT registered in gen_ts_types.py — it's manually maintained. Plan uses direct editing with a note explaining why.

3. **Phase decomposition**: Split original Phase 1 into 4 separate tasks (migration, model+schema, endpoint+service, TS types). Split Phase 3 into 4 tasks (grid layout, touch fixes, sidebar toggle, i18n).

4. **v-bottom-sheet rejected**: Zero codebase usage = integration risk. Replaced with simpler v-show toggle approach on existing sidebar v-col. No new Vuetify component needed.

5. **On-hand count query**: Explicitly specified count query on join table (not full relationship load) per Codex's efficiency concern.

6. **Mobile interaction**: Explicitly documented that tap-to-select flow already works (slot click + recipe select), so disabling drag-drop on touch has a working alternative.

7. **Nav link approach**: Changed from conditional (requires layout-level config fetch) to unconditional (always visible). Avoids flicker and extra API calls.

8. **Dismiss vs complete**: Clarified that "Dismiss" sets onboardingCompleted=true server-side (permanent). No separate "dismissed" flag needed — dismissal IS completion.

9. **Expiration sort ordering**: Added explicit sort specification (expired first by most-negative, then ascending daysToExpiry, nulls last) to prevent ambiguity.

10. **Hidden complexity surfaced**: Added explicit subtasks for each piece of hidden complexity Codex identified, making tasks more atomic for LLM execution.
</changes_made>
</review_notes>
