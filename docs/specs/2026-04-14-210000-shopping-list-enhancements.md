```yaml
spec_metadata:
  goal: "Stage C: Shopping List Enhancements — Verify auto-section assignment, deficit visualization, deduct-on-checkout + quick-add-to-pantry"
  constraints:
    - "Fork isolation: new code in optimizer/ dirs, minimal upstream file touches"
    - "Shopping list page is upstream code — modifications must be non-breaking"
    - "Pantry actions on checkout must be opt-in to avoid disrupting the simple check-off flow"
    - "All new backend endpoints live under existing /households/optimizer/pantry router"
  non_goals:
    - "Rewriting the shopping list page or its composable architecture"
    - "Auto-deduct without user confirmation (always opt-in)"
    - "Offline support for pantry integration (existing offline mode already degrades gracefully)"
    - "Batch operations (deduct all checked items at once) — future enhancement"
    - "Modifying the upstream ShoppingListService.bulk_create_items beyond what's already done"
  timestamp: "2026-04-14T21:00:00"
  confidence: low
  survey_consumed: false

current_state:
  summary: >
    The pantry tracker is complete with CRUD, deficit calculation, deduct-by-recipe, and import-on-hand.
    Shopping list pantry auto-check is already integrated at bulk_create_items (shopping_lists.py:178-184),
    which auto-checks fully-covered items and reduces partial quantities with notes. Auto-section assignment
    via find_matching_label (shopping_lists.py:145-152) assigns food.label_id to items, and the frontend
    groups items by label.name into collapsible sections. The check flow is:
    ShoppingListItem.toggleChecked() → emit("checked") → saveListItem() → shoppingListItemActions.updateItem().
  relevant_files:
    - path: "mealie/services/household_services/shopping_lists.py"
      purpose: "Shopping list service with bulk_create_items, find_matching_label, pantry auto-check integration"
      reuse_potential: high
    - path: "mealie/services/optimizer/pantry.py"
      purpose: "PantryService with check_shopping_items, deduct_recipe, calculate_deficit, import_from_on_hand"
      reuse_potential: high
    - path: "mealie/routes/optimizer/controller_pantry.py"
      purpose: "Pantry CRUD + deficit + deduct + import endpoints (100 lines)"
      reuse_potential: high
    - path: "mealie/schema/optimizer/pantry.py"
      purpose: "Pantry schemas including PantryDeductRequest, PantryDeficitReport, PantryItemCreate"
      reuse_potential: high
    - path: "frontend/app/pages/shopping-lists/[id].vue"
      purpose: "Shopping list detail page — renders items by label section, checked items, recipe refs"
      reuse_potential: medium
    - path: "frontend/app/components/Domain/ShoppingList/ShoppingListItem.vue"
      purpose: "Individual shopping list item — checkbox, display, edit, toggleChecked() emits 'checked'"
      reuse_potential: medium
    - path: "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts"
      purpose: "CRUD operations — saveListItem handles @checked events, check/uncheck all"
      reuse_potential: medium
    - path: "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-sorting.ts"
      purpose: "updateItemsByLabel groups unchecked items by label.name into sections"
      reuse_potential: low
    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      purpose: "PantryItemsApi, OptimizerConfigApi, OptimizerApi — existing API client"
      reuse_potential: high
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "TypeScript types for pantry, deficit, config"
      reuse_potential: high
  patterns_identified:
    - "BaseCrudController: all optimizer endpoints use the @controller(router) decorator pattern with cached_property for repo/mixins/service"
    - "MealieModel schemas: all request/response types extend MealieModel with snake_case → camelCase alias generation"
    - "Sub-composable pattern: shopping list page decomposes into use-shopping-list-{data,crud,labels,sorting,copy,recipes,state}.ts"
    - "Pantry auto-check: integrated via try/except in bulk_create_items — non-critical, degrades gracefully"
    - "Shopping list item actions: batched optimistic updates via useShoppingListItemActions composable"

gaps:
  exists:
    - component: "Auto-section assignment (C1)"
      location: "mealie/services/household_services/shopping_lists.py:145-152"
      notes: >
        find_matching_label() already assigns food.label_id to new items during bulk_create_items().
        The frontend updateItemsByLabel() in use-shopping-list-sorting.ts groups by item.label.name.
        This appears to work end-to-end. C1 is a verification task — confirm it works, document any gaps.
        The three-step label resolution is: (1) item already has label_id, (2) item.food has label_id,
        (3) fuzzy match on item.display text. This covers recipe-ingredient-added items (step 2) and
        manually-typed items (step 3).
    - component: "Pantry notes on shopping items"
      location: "mealie/services/optimizer/pantry.py:369-476"
      notes: >
        check_shopping_items() already adds notes like "Already have in pantry" and "need 8, have 5 cups in pantry"
        to items during bulk creation. These render via RecipeIngredientListItem.vue's note display.
        Deficit visualization (C2) builds on this existing note system.
    - component: "Deficit calculation endpoint"
      location: "mealie/routes/optimizer/controller_pantry.py:50-64"
      notes: >
        POST /deficit and POST /deficit/meal-plan already return PantryDeficitReport with items[],
        uncoveredItems[], totalItems, coveredCount, coveragePercent. C2 consumes this for the banner.
    - component: "Deduct-by-recipe"
      location: "mealie/services/optimizer/pantry.py:288-367"
      notes: >
        deduct_recipe() handles unit conversion, running quantities, and persistence. The new
        deduct-by-shopping-items method follows the same pattern but resolves food/qty/unit from
        ShoppingListItem instead of RecipeIngredient.
  partial:
    - component: "Deficit visualization on shopping list page (C2)"
      location: "frontend/app/pages/shopping-lists/[id].vue"
      missing: >
        No summary banner or visual indicators exist on the shopping list page. Pantry notes exist
        on items (from bulk creation) but there's no aggregated coverage summary. Need: (1) a composable
        to fetch deficit data for the list's recipe references, (2) a banner component showing coverage,
        (3) optional per-item chip for pantry-noted items.
    - component: "Pantry API client for shopping integration"
      location: "frontend/app/lib/api/user/optimizer-pantry.ts"
      missing: >
        Existing methods: calculateDeficit, deductRecipe, importFromOnHand.
        Need: deductShoppingItems(), quickAddToPantry() for the new endpoints.
  missing:
    - component: "Deduct-by-shopping-items endpoint (C3)"
      rationale: >
        The existing POST /deduct accepts a recipe_id and resolves ingredients server-side.
        C3 needs to deduct based on shopping list item IDs (different data source: ShoppingListItem
        has food_id, quantity, unit_id). New endpoint needed because the data flow is fundamentally
        different — items may not have recipe references, and quantities may have been adjusted by
        the user or by the auto-check logic.
    - component: "Quick-add-to-pantry endpoint (C3)"
      rationale: >
        No bulk pantry creation from shopping list data exists. The existing POST /pantry creates
        one item at a time. A dedicated quick-add endpoint accepts an array of {food_id, quantity,
        unit_id} and creates pantry items, skipping duplicates. This is needed for the checkout flow
        where multiple items may be added at once.
    - component: "Pantry action dialog after checkout (C3)"
      rationale: >
        The current check flow is immediate — toggleChecked() flips the boolean and saves.
        No post-check hook exists. A dialog or inline action needs to appear after check-off to offer
        deduct/quick-add options. This must be opt-in and non-blocking.
    - component: "Shopping list pantry composable (C2+C3)"
      rationale: >
        The sub-composable pattern requires a dedicated use-shopping-list-pantry.ts to encapsulate
        deficit fetching, deduct actions, and quick-add actions — keeping pantry logic isolated from
        the main CRUD composable.
    - component: "i18n keys for shopping list pantry integration"
      rationale: >
        New user-facing strings needed for: coverage banner, pantry action prompts, confirmation
        messages, quick-add labels.

specification:
  files:
    # === C1: Verification (no new code, just testing) ===
    # C1 is a verification task. No files to create or modify.
    # Acceptance: manually confirm at localhost that:
    #   1. Adding recipes to a shopping list assigns labels from food.label_id
    #   2. Items group into label sections on the shopping list page
    #   3. Items without food.label_id fall into "No Label" section
    #   4. Fuzzy match (step 3 of find_matching_label) catches manually typed items

    # === C2: Deficit Visualization ===

    - path: "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts"
      action: create
      purpose: "Composable encapsulating pantry integration for the shopping list page — deficit banner data, deduct/quick-add actions"
      signature: |
        import type { ShoppingListOut, ShoppingListItemOut } from "~/lib/api/types/household";
        import type { PantryDeficitReport, PantryItemOut } from "~/lib/api/types/optimizer";

        interface PantryCheckoutAction {
          itemId: string;
          foodId: string;
          foodName: string;
          quantity: number;
          unitId: string | null;
          unitName: string | null;
          /** true if food exists in pantry (deduct), false if not (quick-add) */
          existsInPantry: boolean;
        }

        interface ShoppingListPantryState {
          /** Aggregated deficit report for the shopping list */
          deficitReport: Ref<PantryDeficitReport | null>;
          /** Whether deficit data is loading */
          deficitLoading: Ref<boolean>;
          /** Coverage summary string, e.g. "8 of 12 items covered by pantry" */
          coverageSummary: ComputedRef<string>;
          /** Whether to show the coverage banner (false if no deficit data or no items) */
          showCoverageBanner: ComputedRef<boolean>;
          /** Pending pantry actions after item checkout */
          pendingActions: Ref<PantryCheckoutAction[]>;
          /** Whether the pantry action dialog is open */
          showPantryDialog: Ref<boolean>;
        }

        export function useShoppingListPantry(
          shoppingList: Ref<ShoppingListOut | null>,
        ): ShoppingListPantryState & {
          /** Fetch deficit data for the current list's recipe references */
          fetchDeficit(): Promise<void>;
          /** Called when an item is checked — determines if pantry action is available */
          onItemChecked(item: ShoppingListItemOut): Promise<void>;
          /** Execute deduct for selected items */
          executeDeduct(itemIds: string[]): Promise<void>;
          /** Execute quick-add for selected items */
          executeQuickAdd(items: Array<{ foodId: string; quantity: number; unitId: string | null }>): Promise<PantryItemOut[]>;
          /** Dismiss the pantry dialog without acting */
          dismissPantryDialog(): void;
        };
      depends_on:
        - "frontend/app/lib/api/user/optimizer-pantry.ts"
        - "frontend/app/lib/api/types/optimizer.ts"
        - "frontend/app/lib/api/types/household.ts"
      acceptance_criteria:
        - "fetchDeficit() calls POST /deficit with recipe IDs from shoppingList.recipeReferences"
        - "coverageSummary returns formatted string with covered/total counts"
        - "showCoverageBanner is false when deficitReport is null or shoppingList has no recipe references"
        - "onItemChecked() resolves whether item's food is in pantry and populates pendingActions"
        - "executeDeduct() calls the new deduct-shopping-items endpoint and returns updated items"
        - "executeQuickAdd() calls the new quick-add endpoint and returns created pantry items"

    - path: "frontend/app/pages/shopping-lists/[id].vue"
      action: modify
      purpose: "Add pantry coverage banner below the page header, above the item list"
      signature: |
        <!-- Add after BasePageTitle, before section v-if="!edit" -->
        <!-- Banner: v-if="showCoverageBanner" showing coverageSummary -->
        <!-- Uses v-alert or v-banner with info variant -->
        <!-- Wire useShoppingListPantry into the page via useShoppingListPage -->
      depends_on:
        - "frontend/app/composables/shopping-list-page/use-shopping-list-page.ts"
      acceptance_criteria:
        - "Banner appears below page title when shopping list has recipe references with deficit data"
        - "Banner shows 'X of Y items covered by pantry' with coverage percentage"
        - "Banner does not appear when shopping list has no recipe references"
        - "Banner does not break existing page layout or functionality"

    - path: "frontend/app/composables/shopping-list-page/use-shopping-list-page.ts"
      action: modify
      purpose: "Wire useShoppingListPantry into the main page composable and expose its state/methods"
      signature: |
        // Add import:
        import { useShoppingListPantry } from "./sub-composables/use-shopping-list-pantry";

        // Inside useShoppingListPage():
        const pantry = useShoppingListPantry(shoppingList);

        // Expose in return: ...pantry (or named exports)

        // Call pantry.fetchDeficit() after initial data load
      depends_on:
        - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts"
      acceptance_criteria:
        - "Pantry state (showCoverageBanner, coverageSummary) available to the page component"
        - "fetchDeficit called once after shopping list loads"
        - "Pantry integration does not affect existing shopping list functionality"

    # === C3: Deduct-on-Checkout + Quick-Add-to-Pantry ===

    - path: "mealie/schema/optimizer/pantry.py"
      action: modify
      purpose: "Add request schemas for deduct-by-shopping-items and quick-add-to-pantry"
      signature: |
        class ShoppingItemDeductRequest(MealieModel):
            """Request body for POST /deduct-shopping-items."""
            shopping_list_item_ids: list[UUID4]

        class PantryQuickAddItem(MealieModel):
            """Single item to add to pantry from shopping list."""
            food_id: UUID4
            quantity: float | None = None
            unit_id: UUID4 | None = None

        class PantryQuickAddRequest(MealieModel):
            """Request body for POST /quick-add."""
            items: list[PantryQuickAddItem]
      depends_on:
        - "mealie/schema/_mealie/mealie_model.py"
      acceptance_criteria:
        - "ShoppingItemDeductRequest validates non-empty list of UUIDs"
        - "PantryQuickAddItem requires food_id, optional quantity and unit_id"
        - "Schemas serialize to camelCase via Mealie's alias generator"

    - path: "mealie/services/optimizer/pantry.py"
      action: modify
      purpose: "Add deduct_shopping_items and quick_add methods to PantryService"
      signature: |
        def deduct_shopping_items(
            self,
            shopping_list_item_ids: list[UUID4],
        ) -> list[PantryItemOut]:
            """
            Deduct quantities from pantry based on shopping list items.

            For each shopping list item:
            - Look up the item by ID to get food_id, quantity, unit_id
            - Find matching pantry item by food_id
            - Apply same deduction rules as deduct_recipe (skip assume_enough, skip untracked, handle unit conversion)
            - Return updated pantry items
            """
            ...

        def quick_add_from_shopping(
            self,
            items: list[tuple[UUID4, float | None, UUID4 | None]],
            group_id: UUID4,
            household_id: UUID4,
        ) -> list[PantryItemOut]:
            """
            Create pantry items from shopping list data.

            For each (food_id, quantity, unit_id):
            - Skip if food_id already exists in pantry
            - Create PantryItemSave with provided values, defaults for other fields
            - Return created pantry items
            """
            ...
      depends_on:
        - "mealie/schema/household/group_shopping_list.py (ShoppingListItemOut for item lookup)"
        - "mealie/repos/repository_factory.py (AllRepositories for list_items repo access)"
      acceptance_criteria:
        - "deduct_shopping_items retrieves items from shopping list items repo by ID"
        - "deduct_shopping_items applies same unit conversion and quantity logic as deduct_recipe"
        - "deduct_shopping_items skips items without food_id, without pantry match, or with assume_enough"
        - "quick_add_from_shopping skips foods already in pantry (idempotent)"
        - "quick_add_from_shopping creates items with sensible defaults (is_staple=False, assume_enough=False)"

    - path: "mealie/routes/optimizer/controller_pantry.py"
      action: modify
      purpose: "Add deduct-shopping-items and quick-add endpoints to existing PantryItemController"
      signature: |
        @router.post("/deduct-shopping-items", response_model=list[PantryItemOut])
        def deduct_shopping_items(self, data: ShoppingItemDeductRequest) -> list[PantryItemOut]:
            """Deduct shopping list item quantities from pantry."""
            ...

        @router.post("/quick-add", response_model=list[PantryItemOut], status_code=201)
        def quick_add(self, data: PantryQuickAddRequest) -> list[PantryItemOut]:
            """Create pantry items from shopping list data."""
            ...
      depends_on:
        - "mealie/schema/optimizer/pantry.py (new schemas)"
        - "mealie/services/optimizer/pantry.py (new service methods)"
      acceptance_criteria:
        - "POST /households/optimizer/pantry/deduct-shopping-items returns updated pantry items"
        - "POST /households/optimizer/pantry/quick-add returns created pantry items (201)"
        - "Both endpoints require authentication and respect household isolation"
        - "Both endpoints appear in Swagger docs at localhost:9000/docs"
        - "Endpoint ordering: both POST endpoints placed before /{item_id} to avoid route conflict"

    - path: "frontend/app/lib/api/types/optimizer.ts"
      action: modify
      purpose: "Add TypeScript types for the new request/response schemas"
      signature: |
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
      depends_on:
        - "mealie/schema/optimizer/pantry.py (must match backend schemas)"
      acceptance_criteria:
        - "Types match backend schema field names (camelCase)"
        - "Optional fields use the same nullability as backend"

    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      action: modify
      purpose: "Add API client methods for deduct-shopping-items and quick-add"
      signature: |
        // Add to routes:
        pantryDeductShoppingItems: `${prefix}/households/optimizer/pantry/deduct-shopping-items`,
        pantryQuickAdd: `${prefix}/households/optimizer/pantry/quick-add`,

        // Add to PantryItemsApi:
        async deductShoppingItems(data: ShoppingItemDeductRequest): Promise<...> { ... }
        async quickAdd(data: PantryQuickAddRequest): Promise<...> { ... }
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "deductShoppingItems posts to /deduct-shopping-items and returns PantryItemOut[]"
        - "quickAdd posts to /quick-add and returns PantryItemOut[]"

    - path: "frontend/app/components/Domain/ShoppingList/ShoppingListPantryDialog.vue"
      action: create
      purpose: "Dialog shown after checking off items — offers deduct-from-pantry or quick-add-to-pantry"
      signature: |
        <script setup lang="ts">
        interface Props {
          modelValue: boolean;  // v-model for dialog visibility
          actions: PantryCheckoutAction[];  // items to act on
        }
        const emit = defineEmits<{
          (e: "update:modelValue", value: boolean): void;
          (e: "deduct", itemIds: string[]): void;
          (e: "quick-add", items: Array<{ foodId: string; quantity: number; unitId: string | null }>): void;
          (e: "dismiss"): void;
        }>();
        </script>
        <!-- BaseDialog with two sections:
             1. Items in pantry (deduct): checkbox list, "Deduct from pantry" button
             2. Items not in pantry (quick-add): checkbox list, "Add to pantry" button
             3. "Skip" button to dismiss -->
      depends_on:
        - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts"
      acceptance_criteria:
        - "Dialog opens with list of actionable items grouped by type (deduct vs. quick-add)"
        - "User can select/deselect individual items"
        - "Deduct button calls emit('deduct') with selected item IDs"
        - "Quick-add button calls emit('quick-add') with selected items"
        - "Skip button dismisses without action"
        - "Dialog does not block the check-off — item is already checked before dialog appears"

    - path: "frontend/app/components/Domain/ShoppingList/ShoppingListItem.vue"
      action: modify
      purpose: "Add pantry action indicator after item is checked off"
      signature: |
        <!-- Minimal change: add an emit or callback hook for pantry action.
             Option A: New emit 'pantry-action' fired after toggleChecked when item becomes checked.
             Option B: Expose a slot or prop for parent to inject pantry action trigger.
             Prefer Option A for simplicity. -->

        // In toggleChecked():
        function toggleChecked() {
          const updated = { ...model.value, checked: !model.value.checked } as ShoppingListItemOut;
          model.value = updated;
          emit("checked", updated);
          // No change here — the parent (shopping list page) handles pantry action via saveListItem flow
        }

        // No template changes needed in this component.
        // The pantry dialog is triggered from the page level after saveListItem completes.
      depends_on: []
      acceptance_criteria:
        - "Existing check-off behavior is unchanged"
        - "No visual changes to the ShoppingListItem component itself"

    - path: "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts"
      action: modify
      purpose: "Hook pantry action into saveListItem when an item transitions to checked"
      signature: |
        // Add parameter: onItemChecked callback from pantry composable
        // In saveListItem, after shoppingListItemActions.updateItem(item):
        //   if (item.checked && item.foodId) { onItemChecked(item); }
        // The callback is async but non-blocking — saveListItem does not await it
      depends_on:
        - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-pantry.ts"
      acceptance_criteria:
        - "saveListItem calls onItemChecked when item transitions from unchecked to checked"
        - "Does NOT call onItemChecked when item is unchecked"
        - "Does NOT call onItemChecked for items without food_id"
        - "The check-off is never blocked or delayed by the pantry action"

    - path: "frontend/app/lang/messages/en-US.json"
      action: modify
      purpose: "Add i18n keys for shopping list pantry integration"
      signature: |
        // Under "optimizer" key, add:
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
      depends_on: []
      acceptance_criteria:
        - "All new user-facing strings have i18n keys"
        - "Keys live under optimizer.shopping namespace (not shopping-list)"
        - "Pluralization uses pipe syntax for count-dependent strings"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/services/household_services/shopping_lists.py — analyzed find_matching_label (145-152), bulk_create_items (154-209), pantry integration (178-184)"
    - "mealie/services/optimizer/pantry.py — analyzed full file: get_pantry_map, calculate_deficit, deduct_recipe, check_shopping_items, import_from_on_hand"
    - "mealie/routes/optimizer/controller_pantry.py — analyzed full file: all endpoints, route ordering"
    - "mealie/schema/optimizer/pantry.py — analyzed full file: all schemas"
    - "frontend/app/pages/shopping-lists/[id].vue — analyzed full file: template structure, composable wiring, all destructured exports"
    - "frontend/app/components/Domain/ShoppingList/ShoppingListItem.vue — analyzed full file: toggleChecked flow, emit pattern"
    - "frontend/app/composables/shopping-list-page/use-shopping-list-page.ts — analyzed full file: sub-composable orchestration pattern"
    - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts — analyzed full file: saveListItem, checkAllItems, listItemFactory"
    - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-labels.ts — analyzed full file: label → section mapping"
    - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-sorting.ts — analyzed: updateItemsByLabel groups by label.name"
    - "frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-data.ts — analyzed: shoppingListItemActions.updateItem flow"
    - "frontend/app/lib/api/user/optimizer-pantry.ts — analyzed full file: routes, PantryItemsApi, OptimizerApi"
    - "frontend/app/lib/api/types/optimizer.ts — analyzed full file: all types"
    - "frontend/app/lib/api/types/household.ts — analyzed: ShoppingListItemOut, ShoppingListItemCreate, ShoppingListOut"
  known_patterns:
    - "Sub-composable pattern: each concern gets its own use-shopping-list-*.ts file, orchestrated by use-shopping-list-page.ts"
    - "BaseCrudController: POST endpoints must be ordered before /{item_id} to avoid route conflict (see controller_pantry.py:48 comment)"
    - "MealieModel schemas: snake_case fields auto-alias to camelCase for API serialization"
    - "Pantry deduction: use running_qty dict for in-memory accumulation, persist all changes at end (see deduct_recipe pattern)"
    - "Shopping list item actions: optimistic updates via useShoppingListItemActions — updateItem queues a batch, process() flushes to API"
    - "Deficit report: POST /deficit takes recipe_ids and returns PantryDeficitReport with items[], uncoveredItems[], coverage stats"
  decisions_made:
    - "C1 is verification-only: find_matching_label + updateItemsByLabel already provide auto-section assignment. No code changes expected."
    - "Deficit banner uses recipe references: the shopping list tracks which recipes contributed items (recipeReferences). We extract recipe_ids from those to call the existing deficit endpoint, rather than computing coverage per-item on the frontend."
    - "Pantry dialog is page-level, not item-level: triggered from saveListItem in the CRUD composable, displayed via the page template. This avoids modifying ShoppingListItem.vue's template."
    - "New endpoints extend existing controller: deduct-shopping-items and quick-add are added to PantryItemController, not a new controller. This keeps the /households/optimizer/pantry URL hierarchy."
    - "deduct_shopping_items resolves items from shopping list items repo: it needs access to ShoppingListItem records to get food_id/quantity/unit_id. The PantryService will need access to the list_items repository (available via AllRepositories)."
    - "Quick-add is idempotent: if food_id already exists in pantry, skip it. This prevents duplicates if the user triggers quick-add twice."
  warnings:
    - "Shopping list items repo access: PantryService currently only accesses pantry_items repo. deduct_shopping_items needs to read from shopping list items — use self.repos.group_shopping_list_item (confirmed at repository_factory.py:317)."
    - "Route ordering: the two new POST endpoints MUST be placed before the /{item_id} routes in controller_pantry.py to avoid FastAPI treating 'deduct-shopping-items' and 'quick-add' as item_id parameters."
    - "Upstream file touches: [id].vue and ShoppingListItem.vue are upstream files. Keep changes minimal — add one banner element and one callback hook respectively."
    - "Deficit report accuracy: the deficit endpoint compares recipe ingredients against pantry. But shopping list items may have been quantity-adjusted by auto-check or by the user. The banner shows recipe-level coverage, not shopping-list-item-level coverage. This is a known simplification — accurate enough for the 'X of Y covered' summary."
    - "Batch checkout: the current spec handles one item at a time (onItemChecked per item). If the user clicks 'Check All', this would fire N times. Consider debouncing or batching in the composable — collect actions over a short window, then show one dialog."

open_questions:
  - question: "Should the pantry dialog batch actions when 'Check All' is used, or show one dialog per item?"
    blocking: false
    default_assumption: "Batch: collect all checked items, show one dialog with all actionable items. Use a short debounce (300ms) in onItemChecked to accumulate items before showing the dialog."
  - question: "Should the deficit banner refresh after deduct/quick-add actions, or only on page load?"
    blocking: false
    default_assumption: "Refresh after any pantry mutation (deduct or quick-add) to keep the banner accurate."
  - question: "Should quick-add pre-fill expiration_date or use_priority from any source?"
    blocking: false
    default_assumption: "No — quick-add creates items with defaults (no expiration, use_priority='auto'). The user can edit the pantry item later."
  - question: "Does AllRepositories expose a shopping list items repository for PantryService to query?"
    blocking: false
    default_assumption: "RESOLVED: Yes — AllRepositories.group_shopping_list_item (repository_factory.py:317) returns HouseholdRepositoryGeneric[ShoppingListItemOut, ShoppingListItem]. PantryService can access it via self.repos.group_shopping_list_item."

agent_responses:
  codex_verdict: SKIPPED
  codex_notes: "Codex validation unavailable (model not supported error). Architecture review based on thorough manual codebase exploration. Key risk areas: (1) PantryService accessing shopping list items repo — verify AllRepositories exposes this, (2) route ordering for new POST endpoints, (3) upstream file modification scope."
```
