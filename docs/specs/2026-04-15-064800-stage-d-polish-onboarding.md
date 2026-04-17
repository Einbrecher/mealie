```yaml
spec_metadata:
  goal: "Stage D: Polish & Onboarding — Expiration warnings, first-run import prompt, mobile-responsive grid, onboarding wizard"
  constraints:
    - "All new code in optimizer/ directories per fork isolation rules"
    - "Minimal backend work — only config field additions and one lightweight endpoint"
    - "Follow existing Vuetify patterns (useDisplay, v-expansion-panels, v-stepper)"
    - "Must work on kitchen tablet (landscape) and phone (portrait)"
    - "Stages A-C (optimizer foundation, UI, shopping enhancements) must be complete first"
  non_goals:
    - "Daily expiration notification emails — Mealie uses Apprise event bus, no scheduled job infrastructure exists"
    - "Mobile drag-and-drop — touch drag-drop is fragile; use tap-to-select instead"
    - "Expiration date auto-population from external databases"
    - "Per-user onboarding tracking — per-household via OptimizerConfig is sufficient for family use"
  timestamp: "2026-04-15T06:48:00"
  confidence: medium
  survey_consumed: false

current_state:
  summary: "Pantry CRUD, optimizer planner grid, scoring engine, and shopping list integration are all functional. Expiration dates exist on pantry items but have no visual warnings on the pantry page. The planner grid uses CSS grid with horizontal scroll on mobile. No onboarding or first-run detection exists."
  relevant_files:
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue"
      purpose: "Pantry page — CRUD UI, empty state, item list"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/PantryItemRow.vue"
      purpose: "Individual pantry item row with inline editing"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/PlanGrid.vue"
      purpose: "7-day CSS grid meal plan layout"
      reuse_potential: high
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue"
      purpose: "Planner page — grid + sidebar + config panels"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/PlanSlot.vue"
      purpose: "Individual meal slot with drag-drop support"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/OptimizerRecipeCard.vue"
      purpose: "Recipe card with expiration text/color logic (to extract)"
      reuse_potential: medium
    - path: "frontend/app/composables/optimizer/types.ts"
      purpose: "Shared TS types including PantryMatchDetail with daysToExpiry"
      reuse_potential: high
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "API types — PantryItemOut, OptimizerConfigUpdate"
      reuse_potential: high
    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      purpose: "API client — importFromOnHand(), config endpoints"
      reuse_potential: high
    - path: "frontend/app/pages/admin/setup.vue"
      purpose: "v-stepper wizard pattern (template for D4)"
      reuse_potential: medium
    - path: "frontend/app/composables/use-announcements.ts"
      purpose: "First-run detection pattern using server-side user field"
      reuse_potential: low
    - path: "mealie/db/models/optimizer/config.py"
      purpose: "OptimizerConfigModel — target for new fields"
      reuse_potential: high
    - path: "mealie/schema/optimizer/pantry.py"
      purpose: "Pydantic schemas for pantry + config"
      reuse_potential: high
  patterns_identified:
    - "Vuetify responsive: useDisplay() composable with smAndDown/lgAndUp breakpoints"
    - "Expiration display: matchColor() + expirationText() in OptimizerRecipeCard.vue"
    - "Stepper wizard: v-stepper with v-model page tracking in admin/setup.vue"
    - "API client: BaseCRUDAPI extension pattern in optimizer-pantry.ts"
    - "i18n: Nested keys under optimizer.* namespace in en-US.json"
    - "Server-side state: User/config model fields for cross-device persistent flags"

gaps:
  exists:
    - component: "expirationDate field"
      location: "PantryItemOut.expirationDate, PantryItemRow date input"
      notes: "Field exists in DB, schema, and UI — just needs visual warning treatment"
    - component: "importFromOnHand API"
      location: "optimizer-pantry.ts:importFromOnHand(), controller_pantry.py POST /import-on-hand"
      notes: "Endpoint and client method both exist, just need UI trigger"
    - component: "Expiration text helpers"
      location: "OptimizerRecipeCard.vue:matchColor(), expirationText()"
      notes: "Logic exists but is component-local — extract to shared composable"
    - component: "Planner responsive split"
      location: "planner.vue cols='12' md='8' / md='4'"
      notes: "Grid/sidebar already stack on mobile — needs refinement, not rewrite"
    - component: "v-stepper pattern"
      location: "admin/setup.vue"
      notes: "Complete wizard pattern to follow for D4"
    - component: "OptimizerConfig model"
      location: "mealie/db/models/optimizer/config.py, schema/optimizer/pantry.py"
      notes: "Target for expirationWarningDays and onboardingCompleted fields"
  partial:
    - component: "Pantry item sorting"
      location: "pantry.vue:fetchPantryItems()"
      missing: "Items are unsorted — need client-side sort by expiration status"
    - component: "Pantry empty state"
      location: "pantry.vue lines 20-24"
      missing: "Static message only — needs import detection + action button"
    - component: "Mobile grid layout"
      location: "PlanGrid.vue CSS grid with overflow-x-auto"
      missing: "Horizontal scroll on mobile is usable but not ideal — needs accordion alternative"
    - component: "Touch interaction"
      location: "PlanSlot.vue drag-drop events, OptimizerRecipeCard.vue draggable"
      missing: "Drag-drop doesn't work on touch — need tap-to-select fallback"
  missing:
    - component: "Expiration warning indicators"
      rationale: "PantryItemRow shows raw date input but no visual urgency signal (color, icon, chip)"
    - component: "Shared expiration helpers composable"
      rationale: "daysToExpiry calculation and color/text logic duplicated if not extracted"
    - component: "On-hand count endpoint"
      rationale: "Need to know if on-hand foods exist before showing import prompt (avoid empty prompt)"
    - component: "Mobile day accordion"
      rationale: "Phone screens can't display 7-column grid — need stacked day-by-day layout"
    - component: "Sidebar toggle FAB"
      rationale: "On mobile, sidebar stacks below grid — need toggle to show/hide it"
    - component: "Onboarding wizard page"
      rationale: "New users need guided flow through pantry → config → planner → shopping list"
    - component: "Onboarding completion flag"
      rationale: "Server-side flag on OptimizerConfig to track per-household onboarding state"
  integration_points:
    - location: "pantry.vue:fetchPantryItems()"
      connects_to: "D1 sort logic, D2 import detection"
    - location: "PantryItemRow.vue template"
      connects_to: "D1 warning indicators"
    - location: "PlanGrid.vue template + style"
      connects_to: "D3 responsive layout switch"
    - location: "planner.vue v-col layout"
      connects_to: "D3 sidebar toggle, D4 onboarding redirect"
    - location: "OptimizerConfigModel / OptimizerConfigUpdate"
      connects_to: "D1 expirationWarningDays, D4 onboardingCompleted"
    - location: "en-US.json optimizer section"
      connects_to: "All features — new i18n keys"

specification:
  files:
    # ──────────────────────────────────────────────
    # D1: Expiration Warnings
    # ──────────────────────────────────────────────
    - path: "frontend/app/composables/optimizer/use-expiration-helpers.ts"
      action: create
      purpose: "Shared expiration calculation and display helpers — extracted from OptimizerRecipeCard"
      signature: |
        import type { PantryItemOut } from "~/lib/api/types/optimizer";
        import type { PantryMatchDetail } from "~/composables/optimizer/types";

        /**
         * Calculate days until expiration from a date string.
         * Returns null if no expiration date, negative if expired.
         */
        export function daysToExpiry(expirationDate: string | null | undefined): number | null;

        /**
         * Determine visual severity level for an expiration status.
         * @param days - result of daysToExpiry()
         * @param warningThreshold - days before expiry to start warning (default 3)
         */
        export function expirationSeverity(
          days: number | null,
          warningThreshold?: number
        ): "expired" | "warning" | "ok" | "none";

        /**
         * Get Vuetify color string for expiration severity.
         */
        export function expirationColor(severity: "expired" | "warning" | "ok" | "none"): string;

        /**
         * Get i18n-ready expiration display text.
         * Returns key + params for use with $t().
         */
        export function expirationTextKey(days: number | null): {
          key: string;
          params?: Record<string, number>;
        } | null;

        /**
         * Sort pantry items: expired first, then expiring-soon (by days ascending),
         * then items with no expiration date last.
         */
        export function sortByExpiration(items: PantryItemOut[]): PantryItemOut[];
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
        - "frontend/app/composables/optimizer/types.ts"
      acceptance_criteria:
        - "daysToExpiry('2026-04-15') returns 0 when called on 2026-04-15"
        - "daysToExpiry('2026-04-13') returns -2 when called on 2026-04-15"
        - "daysToExpiry(null) returns null"
        - "expirationSeverity(-1) returns 'expired'"
        - "expirationSeverity(2, 3) returns 'warning'"
        - "expirationSeverity(5, 3) returns 'ok'"
        - "expirationSeverity(null) returns 'none'"
        - "sortByExpiration places expired items first, then by ascending daysToExpiry, nulls last"

    - path: "frontend/app/components/optimizer/PantryItemRow.vue"
      action: modify
      purpose: "Add visual expiration warning indicators — colored left border, warning chip, expiration status text"
      signature: |
        // NEW prop: warningThreshold (from config)
        defineProps<{
          item: PantryItemOut;
          foods: IngredientFood[];
          units: IngredientUnit[];
          warningThreshold?: number;  // NEW — default 3
        }>();

        // NEW computed properties
        const itemDaysToExpiry: ComputedRef<number | null>;     // uses daysToExpiry(editItem.expirationDate)
        const severity: ComputedRef<"expired" | "warning" | "ok" | "none">;  // uses expirationSeverity()
        const borderColor: ComputedRef<string>;                  // maps severity to CSS border-left color

        // TEMPLATE CHANGES:
        // - v-card gets dynamic :style="{ borderLeft: `4px solid ${borderColor}` }"
        // - After expiration date input, add v-chip showing expiration status text
        //   when severity is "expired" or "warning"
        // - Chip uses expirationColor(severity) and displays translated text
      depends_on:
        - "frontend/app/composables/optimizer/use-expiration-helpers.ts"
      acceptance_criteria:
        - "Item with expirationDate 2 days from now shows warning-colored left border and 'expires in 2 days' chip"
        - "Item with expirationDate in the past shows error-colored left border and 'expired' chip"
        - "Item with no expirationDate shows no border color and no chip"
        - "Item with expirationDate 10 days out shows success-colored border, no chip"

    - path: "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue"
      action: modify
      purpose: "D1: Sort items by expiration. D2: Add import prompt to empty state."
      signature: |
        // NEW imports
        import { sortByExpiration } from "~/composables/optimizer/use-expiration-helpers";

        // NEW state for D2
        const onHandCount: Ref<number>;          // fetched on mount
        const importing: Ref<boolean>;
        const importResult: Ref<PantryImportResult | null>;

        // MODIFIED: fetchPantryItems() applies sortByExpiration() after fetch
        async function fetchPantryItems(): Promise<void>;

        // NEW: fetch on-hand count for import prompt
        async function fetchOnHandCount(): Promise<void>;

        // NEW: trigger import and refresh
        async function onImportFromOnHand(): Promise<void>;

        // NEW: pass warningThreshold to PantryItemRow from config
        // Fetch config on mount alongside pantry items
        const config: Ref<OptimizerConfigOut | null>;

        // TEMPLATE CHANGES:
        // - Empty state card: conditionally show import prompt when onHandCount > 0
        //   "You have {count} foods marked as on-hand. Import them to your pantry?"
        //   [Import] button calling onImportFromOnHand()
        // - PantryItemRow gets :warning-threshold="config?.expirationWarningDays ?? 3"
        // - Success snackbar for import result
      depends_on:
        - "frontend/app/composables/optimizer/use-expiration-helpers.ts"
        - "frontend/app/lib/api/user/optimizer-pantry.ts"
      acceptance_criteria:
        - "Pantry items display sorted: expired first, expiring-soon next, no-date last"
        - "Empty pantry with on-hand foods shows import prompt with count"
        - "Empty pantry with zero on-hand foods shows only the standard empty message"
        - "Clicking import calls importFromOnHand(), refreshes list, shows success toast"
        - "After import, empty state disappears and imported items are listed"

    - path: "frontend/app/components/optimizer/OptimizerRecipeCard.vue"
      action: modify
      purpose: "Replace local expiration helpers with shared composable imports"
      signature: |
        // REMOVE local matchColor() and expirationText() functions
        // REPLACE with imports from use-expiration-helpers.ts:
        import { expirationColor, expirationSeverity, expirationTextKey } from "~/composables/optimizer/use-expiration-helpers";

        // matchColor(match) → expirationColor(expirationSeverity(match.daysToExpiry))
        // expirationText(match) → t(expirationTextKey(match.daysToExpiry).key, ...)
      depends_on:
        - "frontend/app/composables/optimizer/use-expiration-helpers.ts"
      acceptance_criteria:
        - "Recipe cards display identical expiration text and colors as before refactor"

    # ──────────────────────────────────────────────
    # D2: First-Run Import (backend)
    # ──────────────────────────────────────────────
    - path: "mealie/routes/optimizer/controller_pantry.py"
      action: modify
      purpose: "Add GET /pantry/on-hand-count endpoint to check import availability"
      signature: |
        from mealie.schema.optimizer.pantry import OnHandCountResponse

        @router.get("/on-hand-count", response_model=OnHandCountResponse)
        def get_on_hand_count(self) -> OnHandCountResponse:
            """Return count of ingredient_foods with on_hand=True for the household.
            Used by frontend to decide whether to show import prompt."""
            ...
      depends_on:
        - "mealie/schema/optimizer/pantry.py"
        - "mealie/services/optimizer/pantry.py"
      acceptance_criteria:
        - "GET /households/optimizer/pantry/on-hand-count returns {count: N} where N matches foods with on_hand=True"
        - "Returns {count: 0} when no on-hand foods exist"

    - path: "mealie/schema/optimizer/pantry.py"
      action: modify
      purpose: "Add OnHandCountResponse schema"
      signature: |
        class OnHandCountResponse(MealieModel):
            count: int
      depends_on: []
      acceptance_criteria:
        - "Schema validates and serializes correctly"

    - path: "mealie/services/optimizer/pantry.py"
      action: modify
      purpose: "Add method to count on-hand foods"
      signature: |
        def get_on_hand_count(self) -> int:
            """Count ingredient foods with on_hand=True for this household's group."""
            ...
      depends_on:
        - "mealie/db/models/recipe/ingredient.py (IngredientFoodModel.on_hand)"
      acceptance_criteria:
        - "Returns accurate count of on-hand foods for the household's group"

    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      action: modify
      purpose: "Add getOnHandCount() method to PantryItemsApi"
      signature: |
        // NEW route
        const routes = {
          ...existing,
          pantryOnHandCount: `${prefix}/households/optimizer/pantry/on-hand-count`,
        };

        // NEW method on PantryItemsApi
        async getOnHandCount(): Promise<ApiRequestResponse<{ count: number }>>;
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "Method calls GET /households/optimizer/pantry/on-hand-count and returns parsed response"

    # ──────────────────────────────────────────────
    # D1: Expiration Warning Config (backend)
    # ──────────────────────────────────────────────
    - path: "mealie/db/models/optimizer/config.py"
      action: modify
      purpose: "Add expiration_warning_days and onboarding_completed columns"
      signature: |
        # NEW columns on OptimizerConfigModel
        expiration_warning_days: Mapped[int] = mapped_column(Integer, default=3)
        onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
      depends_on: []
      acceptance_criteria:
        - "Columns exist with correct defaults after migration"

    - path: "mealie/schema/optimizer/config.py or pantry.py (wherever OptimizerConfigUpdate lives)"
      action: modify
      purpose: "Add fields to config schemas"
      signature: |
        class OptimizerConfigUpdate(MealieModel):
            ...existing fields...
            expiration_warning_days: int = 3           # NEW
            onboarding_completed: bool = False          # NEW
      depends_on:
        - "mealie/db/models/optimizer/config.py"
      acceptance_criteria:
        - "GET /optimizer/config returns expirationWarningDays and onboardingCompleted"
        - "PUT /optimizer/config accepts and persists both new fields"

    - path: "frontend/app/lib/api/types/optimizer.ts"
      action: modify
      purpose: "Add new config fields to TypeScript interfaces"
      signature: |
        export interface OptimizerConfigUpdate {
          ...existing fields...
          expirationWarningDays: number;        // NEW
          onboardingCompleted: boolean;          // NEW
        }
      depends_on: []
      acceptance_criteria:
        - "TypeScript types match backend schema after changes"

    - path: "mealie/alembic/versions/xxxx_add_config_polish_fields.py"
      action: create
      purpose: "Alembic migration adding expiration_warning_days and onboarding_completed to optimizer_config"
      signature: |
        # Single migration adding two columns to optimizer_config table
        def upgrade():
            op.add_column("optimizer_config", sa.Column("expiration_warning_days", sa.Integer(), server_default="3"))
            op.add_column("optimizer_config", sa.Column("onboarding_completed", sa.Boolean(), server_default="false"))

        def downgrade():
            op.drop_column("optimizer_config", "onboarding_completed")
            op.drop_column("optimizer_config", "expiration_warning_days")
      depends_on:
        - "mealie/db/models/optimizer/config.py"
      acceptance_criteria:
        - "Migration applies cleanly on existing database"
        - "Existing config rows get default values (3, false)"

    # ──────────────────────────────────────────────
    # D3: Mobile-Responsive Plan Grid
    # ──────────────────────────────────────────────
    - path: "frontend/app/components/optimizer/PlanGrid.vue"
      action: modify
      purpose: "Add responsive layout — CSS grid on desktop, day accordion on mobile"
      signature: |
        import { useDisplay } from "vuetify";

        // NEW: responsive detection
        const { smAndDown } = useDisplay();

        // EXISTING props unchanged
        defineProps<{
          days: Date[];
          entries: Map<string, DraftPlanEntry[]>;
          entryTypes: PlanEntryType[];
          activeSlot: string | null;
        }>();

        // TEMPLATE CHANGES:
        // - Wrap in v-if/v-else on smAndDown
        // - Desktop (v-if="!smAndDown"): existing CSS grid layout unchanged
        // - Mobile (v-else): v-expansion-panels with one panel per day
        //   Each panel title: "Mon 4/15" with entry count badge
        //   Panel content: vertical list of PlanSlot per entryType
        //   Optional: sticky day-chip row above accordion for quick jump
      depends_on:
        - "frontend/app/components/optimizer/PlanSlot.vue"
      acceptance_criteria:
        - "On screens >= md: 7-column CSS grid renders identically to current"
        - "On screens < md: day accordion renders with one expandable panel per day"
        - "Each accordion panel shows entry count badge in header"
        - "Slot-click, slot-drop, entry-remove events fire correctly in both layouts"
        - "Transition between layouts is clean on window resize"

    - path: "frontend/app/components/optimizer/PlanSlot.vue"
      action: modify
      purpose: "Enlarge touch targets on mobile, add tap-to-select fallback"
      signature: |
        import { useDisplay } from "vuetify";

        const { smAndDown } = useDisplay();

        // NEW computed
        const isTouchDevice: ComputedRef<boolean>;  // detected via matchMedia('(pointer: coarse)')

        // TEMPLATE CHANGES:
        // - Dynamic min-height: 80px desktop, 56px mobile (denser since accordion gives vertical space)
        // - When isTouchDevice: hide drag affordance, make entire card tappable
        // - Remove button gets larger touch target (40px) on mobile
        // - plan-slot__empty gets larger tap area on mobile

        // STYLE CHANGES:
        // - .plan-slot { min-height: var(--slot-min-height, 80px); }
        // - @media (pointer: coarse) { --slot-min-height: 56px; }
        // - .plan-slot__remove always visible on touch (no hover dependency)
      depends_on: []
      acceptance_criteria:
        - "On touch devices: remove button always visible (not hover-dependent)"
        - "On touch devices: no drag cursor shown"
        - "Tap on slot still fires click event correctly"
        - "Desktop behavior unchanged"

    - path: "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue"
      action: modify
      purpose: "Add mobile sidebar toggle, improve responsive layout"
      signature: |
        import { useDisplay } from "vuetify";

        const { smAndDown } = useDisplay();

        // NEW state
        const showSidebar: Ref<boolean>;  // default: !smAndDown (auto-hide on mobile)

        // NEW: toggle function
        function toggleSidebar(): void;

        // TEMPLATE CHANGES:
        // - Right panel v-col gets v-show="showSidebar"
        // - Add v-btn FAB (position fixed bottom-right) on smAndDown to toggle sidebar
        //   Icon: $mdi-chef-hat when hidden, $mdi-close when shown
        // - When sidebar shown on mobile, it overlays as a v-bottom-sheet or full-width panel
        // - Date picker: on mobile, use full-width button instead of menu
        // - Action buttons: stack vertically on mobile (flex-column on smAndDown)
      depends_on:
        - "frontend/app/components/optimizer/PlanGrid.vue"
        - "frontend/app/components/optimizer/SuggestionSidebar.vue"
      acceptance_criteria:
        - "On desktop: sidebar always visible, no FAB shown"
        - "On mobile: sidebar hidden by default, FAB visible at bottom-right"
        - "Tapping FAB shows sidebar as overlay/bottom-sheet"
        - "Selecting a recipe from mobile sidebar adds it to active slot and closes sidebar"
        - "Action buttons stack vertically on mobile screens"

    # ──────────────────────────────────────────────
    # D4: Onboarding Wizard (stretch)
    # ──────────────────────────────────────────────
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/setup.vue"
      action: create
      purpose: "Guided onboarding wizard for new optimizer users — 4-step v-stepper flow"
      signature: |
        // Page component using v-stepper pattern from admin/setup.vue

        enum Steps {
          WELCOME = 1,
          PANTRY = 2,
          CONFIG = 3,
          DONE = 4,
        }

        // State
        const currentStep: Ref<Steps>;
        const importing: Ref<boolean>;
        const onHandCount: Ref<number>;
        const config: Ref<OptimizerConfigOut | null>;
        const pantryItems: Ref<PantryItemOut[]>;

        // Step 1 (WELCOME): Brief intro, "Let's set up your optimizer"
        // Step 2 (PANTRY): Import from on-hand button (if available),
        //   inline PantryItemRow list for reviewing/editing imported items,
        //   "Add more" button to manually add items
        // Step 3 (CONFIG): Embed ConfigPanel component for weight adjustment,
        //   brief explanation of what each weight does
        // Step 4 (DONE): Summary stats (N pantry items, config saved),
        //   "Go to Meal Planner" button → navigates to planner page
        //   Calls updateConfig({ onboardingCompleted: true }) on completion

        // Navigation: Back/Next buttons, Skip button on every step
        // Skip sets onboardingCompleted=true and navigates to planner
      depends_on:
        - "frontend/app/components/optimizer/PantryItemRow.vue"
        - "frontend/app/components/optimizer/ConfigPanel.vue"
        - "frontend/app/lib/api/user/optimizer-pantry.ts"
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "4-step wizard renders with v-stepper, mobile-responsive (mobile-breakpoint='sm')"
        - "Step 2 shows import button only when on-hand count > 0"
        - "Step 2 displays imported items for review"
        - "Step 3 embeds working ConfigPanel with weight sliders"
        - "Completing wizard sets onboardingCompleted=true on server"
        - "Skip button available on every step, sets flag and navigates to planner"
        - "Revisiting /optimizer/setup after completion shows wizard with current state (not blocked)"

    - path: "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue"
      action: modify
      purpose: "D4: Add onboarding redirect for first-time users"
      signature: |
        // ADDITION to onMounted:
        // If config.onboardingCompleted === false, show a dismissible banner:
        //   "New to the optimizer? [Start Setup] or [Dismiss]"
        // Clicking "Start Setup" navigates to /optimizer/setup
        // Clicking "Dismiss" sets onboardingCompleted=true via API
        // NOTE: Do NOT auto-redirect — use a non-blocking banner instead
      depends_on:
        - "frontend/app/lib/api/user/optimizer-pantry.ts"
      acceptance_criteria:
        - "First visit with onboardingCompleted=false shows setup banner"
        - "Banner has 'Start Setup' link to /optimizer/setup"
        - "Banner has 'Dismiss' button that sets onboardingCompleted=true"
        - "Subsequent visits with onboardingCompleted=true show no banner"
        - "Banner does not block planner usage"

    - path: "frontend/app/components/Layout/DefaultLayout.vue"
      action: modify
      purpose: "D4: Add optimizer setup link to nav (only when onboarding not completed)"
      signature: |
        // CONDITIONAL nav item: only show "Setup" link when onboardingCompleted is false
        // Below existing pantry and planner links in topLinks array
        // {
        //   icon: $globals.icons.wizardHat (or $mdi-school),
        //   title: i18n.t("optimizer.onboarding.setup"),
        //   to: `/g/${groupSlug}/optimizer/setup`,
        //   restricted: true,
        //   condition: !optimizerConfig?.onboardingCompleted,  // hide after completion
        // }
      depends_on:
        - "frontend/app/lib/api/user/optimizer-pantry.ts"
      acceptance_criteria:
        - "Setup nav link visible when onboardingCompleted is false"
        - "Setup nav link hidden after onboarding is completed"

    # ──────────────────────────────────────────────
    # i18n (all features)
    # ──────────────────────────────────────────────
    - path: "frontend/app/lang/messages/en-US.json"
      action: modify
      purpose: "Add i18n keys for all Stage D features"
      signature: |
        // Under "optimizer.pantry":
        "expired": "Expired",
        "expires-soon": "Expires soon",
        "expires-in-days": "Expires in {days} day | Expires in {days} days",
        "expires-today": "Expires today",
        "expiration-warning-days": "Expiration Warning (days)",
        "import-available": "You have {count} food marked as on-hand | You have {count} foods marked as on-hand",
        "import-prompt": "Import them to your pantry to start tracking quantities?",
        "import-button": "Import to Pantry",
        "import-success": "Imported {imported} item, skipped {skipped} duplicate | Imported {imported} items, skipped {skipped} duplicates",

        // Under "optimizer.planner" (D3 additions):
        "show-suggestions": "Show Suggestions",
        "hide-suggestions": "Hide Suggestions",
        "day-entries": "{count} meal | {count} meals",

        // NEW section "optimizer.onboarding":
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
      depends_on: []
      acceptance_criteria:
        - "All new i18n keys resolve without warnings"
        - "Pluralization works correctly for count-dependent strings"

handoff_to_deep_plan:
  skip_exploration:
    - "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue — fully read, 231 lines"
    - "frontend/app/components/optimizer/PantryItemRow.vue — fully read, 137 lines"
    - "frontend/app/components/optimizer/PlanGrid.vue — fully read, 95 lines"
    - "frontend/app/components/optimizer/PlanSlot.vue — fully read, 194 lines"
    - "frontend/app/components/optimizer/OptimizerRecipeCard.vue — fully read, 140 lines"
    - "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue — fully read, 320 lines"
    - "frontend/app/composables/optimizer/types.ts — fully read, 48 lines"
    - "frontend/app/lib/api/types/optimizer.ts — fully read, 139 lines"
    - "frontend/app/lib/api/user/optimizer-pantry.ts — fully read, 88 lines"
    - "frontend/app/pages/admin/setup.vue — read first 80 lines (stepper pattern)"
    - "frontend/app/composables/use-announcements.ts — fully read, 136 lines"
    - "frontend/app/lang/messages/en-US.json — optimizer section lines 1484-1561"
  known_patterns:
    - "Vuetify responsive: `const { smAndDown } = useDisplay()` in script setup, then v-if/v-else or :class in template"
    - "Touch detection: `window.matchMedia('(pointer: coarse)').matches` for pointer type"
    - "v-stepper: v-model drives step, v-stepper-header with v-stepper-item per step, v-stepper-window with v-stepper-window-item per step"
    - "Expiration text: discrete tier logic (expired/today/N days), not smooth curves"
    - "Sort pattern: client-side Array.sort() after API fetch, not server-side ordering"
    - "API client: add route constant, add method to existing class, no new class needed for on-hand-count"
    - "Alembic migration: hand-written single-op, chain via down_revision to current head"
    - "Config field pipeline: migration → model column → Pydantic field → TS interface → composable/component"
  decisions_made:
    - "Accordion not carousel for mobile grid: Codex validated — better for scan-heavy meal planning, discoverability, accessibility"
    - "Server-side onboarding flag not localStorage: Codex validated — cross-device state belongs on server, matches announcements pattern"
    - "Non-blocking banner not auto-redirect for onboarding: less disruptive, planner is usable without completing wizard"
    - "Extract shared expiration helpers: avoids duplication between PantryItemRow and OptimizerRecipeCard"
    - "expirationWarningDays on OptimizerConfig: per-household, avoids touching upstream user model"
    - "No daily notification: Mealie uses Apprise event bus (webhook-style), no scheduled job infrastructure"
    - "D4 is stretch goal: implement D1-D3 first, D4 can be deferred if time-constrained"
  warnings:
    - "PlanGrid responsive switch adds template complexity — consider extracting PlanGridMobile.vue if the v-if/v-else gets unwieldy"
    - "v-expansion-panels in PlanGrid mobile: test that slot-click/slot-drop events propagate correctly through panel expansion"
    - "Touch drag-drop removal: OptimizerRecipeCard.vue also has draggable='true' — needs conditional removal on touch devices"
    - "ConfigPanel embedded in wizard: verify it works standalone (currently used only in planner.vue)"
    - "On-hand-count endpoint: verify that IngredientFoodModel.on_hand field exists and is queryable (it's an upstream model)"
    - "Migration ordering: this migration must chain after the existing optimizer_config table creation migration"

open_questions:
  - question: "Should the mobile accordion show all days expanded by default, or only today?"
    blocking: false
    default_assumption: "Show today expanded, others collapsed — reduces initial scroll depth"
  - question: "Should the FAB sidebar toggle use v-bottom-sheet or v-navigation-drawer for the mobile sidebar?"
    blocking: false
    default_assumption: "v-bottom-sheet — more natural on mobile, doesn't require full-height drawer"
  - question: "Should the onboarding wizard be accessible after completion (for re-configuration)?"
    blocking: false
    default_assumption: "Yes — /optimizer/setup always works, but the nav link and banner hide after completion"
  - question: "Should expiration sorting persist across sessions or always apply on load?"
    blocking: false
    default_assumption: "Always apply on load — no persisted sort preference needed"
  - question: "Does IngredientFoodModel.on_hand exist as a queryable boolean field?"
    blocking: true
    default_assumption: "Yes — it's referenced in the import-on-hand endpoint which already works. Verify during implementation."

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Codex validated two key architectural decisions:
    1. **Accordion over carousel for mobile**: Confirmed — meal planning is scan-heavy, not slide-heavy.
       Users need to see where they are in the week, jump to specific days, and compare without
       hidden off-screen state. Suggested optional sticky day-chip row above accordion for fast nav.
    2. **Server-side onboarding flag over localStorage**: Confirmed — cross-device product state
       belongs server-side, matching the existing announcements pattern (lastReadAnnouncement).
       Recommended split: server stores completion flag, localStorage stores in-progress draft step.

    Concerns noted:
    - Consider adding `onboardingVersion` field alongside `onboardingCompleted` for future-proofing
      (if wizard steps change, can re-trigger for existing users). Low priority — not blocking.
    - Verify IngredientFoodModel.on_hand field accessibility from optimizer service layer.

    Overall verdict: CONCERNS (minor — proceed with medium confidence, note version field as future enhancement).
```
