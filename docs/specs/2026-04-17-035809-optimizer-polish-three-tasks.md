```yaml
spec_metadata:
  goal: |
    1. Centralize planner diff equality (medium) — The field comparison logic (recipeId, entryType, date, existingEntryId) is duplicated in both
       hasUnsavedChanges and savePlan() in use-optimizer-planner.ts. Next time a compared field is added, it's easy to update one but not the other. Extract a
       shared draftEntryChanged(a, b) helper.
    2. Type the _deduct_items() tuple protocol (low) — The shared helper takes list[tuple[UUID4, float, object | None, UUID4 | None]] which is positional and
       fragile. Replacing with a NamedTuple or small dataclass (e.g., DeductionItem(food_id, quantity, unit_obj, original_unit_id)) would make it safer to evolve.
    3. Add test coverage for new paths (low) — No tests currently exercise:
       - RepositoryGeneric.get_many() (batch fetch, empty input, missing IDs)
       - The orphaned FK guard skip path in _deduct_items()
       - Planner diff detection for date/entryType field changes
  constraints:
    - "Fork isolation: new optimizer code stays under `mealie/.../optimizer/` and `frontend/app/**/optimizer/`; only test files may land outside those roots."
    - "Modified upstream files list in CLAUDE.md must stay minimal — no new upstream edits beyond the files already tracked."
    - "Backend tuple-typing refactor must preserve external behavior of `_deduct_items`, `deduct_recipe`, `deduct_shopping_items` (pure internal transport change)."
    - "Frontend diff-helper extraction must preserve the exact truthiness of `hasUnsavedChanges` and the create/update/delete partitioning of `savePlan()` — refactor only, no behavior change."
    - "Use existing fixtures (`session`, per-group repositories) for repository tests; do not introduce new testing infrastructure."
  non_goals:
    - "Redesigning the DraftPlanEntry shape or the meal-plan save semantics."
    - "Changing the `_deduct_items` algorithm, unit-conversion logic, or orphaned-FK guard behavior."
    - "Exhaustive integration tests for the shopping-list deduct round trip — covered elsewhere."
    - "Adding API-level tests for the planner save flow."
  timestamp: "2026-04-17T03:58:09"
  confidence: high
  survey_consumed: false

current_state:
  summary: |
    Two small code-quality frictions plus a test-coverage gap in the optimizer fork. The planner composable duplicates the
    per-field equality check between `hasUnsavedChanges` and `savePlan()`. The shared `_deduct_items` helper in the pantry
    service uses a positional 4-tuple for internal transport. Three new code paths landed in recent commits without direct
    tests: `RepositoryGeneric.get_many()` (shared), the orphaned-FK skip in `_deduct_items`, and planner diff detection.
  relevant_files:
    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      purpose: "Owns DraftPlanEntry type, loadedEntriesSnapshot, hasUnsavedChanges (lines 113–131), and savePlan() (lines 355–414)."
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/types.ts"
      purpose: "Existing shared optimizer domain types (RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring). Already imported by use-optimizer-planner.ts."
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/scoring-engine.test.ts"
      purpose: "Reference vitest pattern for pure-module tests in this directory."
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/use-expiration-helpers.test.ts"
      purpose: "Second reference vitest pattern (simpler pure helper + test pair)."
      reuse_potential: high
    - path: "mealie/services/optimizer/pantry.py"
      purpose: "Hosts _deduct_items (lines 311–363), deduct_recipe (365–379), deduct_shopping_items (381–398). The tuple protocol is declared at line 313."
      reuse_potential: high
    - path: "mealie/repos/repository_generic.py"
      purpose: "Declares get_many() at lines 181–199 (batch fetch by PK or named column, tenant-scoped, missing IDs silently excluded)."
      reuse_potential: high
    - path: "tests/integration_tests/test_repository_factory.py"
      purpose: "Existing repository tests using session fixture and per-group repos. Reference patterns at lines 131–143 (ingredient_foods tenant scope), 172–177 (webhooks), 287–294 (shopping lists)."
      reuse_potential: high
    - path: "tests/unit_tests/services_tests/test_pantry_service.py"
      purpose: "Existing pantry-service tests with _make_food/_make_unit/_make_pantry_item factories (lines 14–67). CalculateDeficitTests class is the direct pattern."
      reuse_potential: high
  patterns_identified:
    - "Pure-helper extraction pattern: colocated helper module + `*.test.ts` (see scoring-engine, use-expiration-helpers)."
    - "Shared types are consolidated in `frontend/app/composables/optimizer/types.ts`, not scattered across composables."
    - "Pantry service unit tests construct ad-hoc `PantryService` via `object.__new__` when no DB is needed (test_pantry_service.py line 82), bypassing the repos requirement."
    - "Repository integration tests use `session` fixture plus `get_repositories(session, group_id=...)` to build per-tenant repos, and assert direct equality between returned schema and input schema."
    - "Snake_case Python fields ↔ camelCase TS: DraftPlanEntry is frontend-only (no backend mirror), so renaming its exports has no cross-boundary impact."

gaps:
  exists:
    - component: "Vitest runner for composables/optimizer"
      location: "frontend/app/composables/optimizer/*.test.ts"
      notes: "New planner-diff.test.ts will be picked up automatically by `task ui:test`."
    - component: "Session + per-tenant repo fixtures for integration tests"
      location: "tests/integration_tests/test_repository_factory.py + tests/conftest"
      notes: "Reuse the `session` fixture and `get_repositories(session, group_id=..., household_id=...)` construction pattern already present in the same file."
    - component: "PantryService unit-test harness without DB"
      location: "tests/unit_tests/services_tests/test_pantry_service.py:70–86"
      notes: "Reuse `object.__new__(PantryService)` + manual `converter` assignment for any method that does not touch `self.repos` or `self.pantry_items`."
  partial:
    - component: "Diff logic for DraftPlanEntry"
      location: "frontend/app/composables/optimizer/use-optimizer-planner.ts:113–131 and 381–413"
      missing: "Shared helper `draftEntryFieldsChanged(a, b)` that both sites delegate to. Today each site spells out the field list inline."
    - component: "DeductionItem record type"
      location: "mealie/services/optimizer/pantry.py:311–398"
      missing: "Named record replacing the positional 4-tuple; all three sites (declaration + 2 construction points) must migrate atomically."
    - component: "Repository-level tests for get_many()"
      location: "tests/integration_tests/test_repository_factory.py"
      missing: "Empty-input, batch-fetch, missing-ID, tenant-scope, and named-key cases for get_many()."
    - component: "Pantry-service coverage for orphaned-FK skip"
      location: "tests/unit_tests/services_tests/test_pantry_service.py"
      missing: "Test class exercising the `source_unit_id is None and pantry_unit_id is None and original_unit_id is not None` branch at pantry.py:335–337."
    - component: "Planner-diff field sensitivity tests"
      location: "frontend/app/composables/optimizer/"
      missing: "A `planner-diff.test.ts` module verifying the helper flips on each compared field."
  missing:
    - component: "DraftPlanEntry type ownership"
      rationale: "DraftPlanEntry is today defined inside the stateful composable. For the diff helper to live in a separate pure module without creating a wrong-direction import (helper → composable), the type must move to a shared location first."

specification:
  files:
    - path: "frontend/app/composables/optimizer/types.ts"
      action: modify
      purpose: "Relocate DraftPlanEntry here so it can be imported by both the composable and the new pure-diff helper without creating a reverse dependency."
      signature: |
        // Add (copy verbatim from use-optimizer-planner.ts lines 10–22):
        export interface DraftPlanEntry {
          localId: string;
          date: string;
          entryType: PlanEntryType;
          order: number;
          recipeId: string | null;
          recipeName: string | null;
          recipeSlug: string | null;
          existingEntryId: number | null;
          groupId: string | null;
          userId: string | null;
          householdId: string | null;
        }
        // PlanEntryType must also be imported here:
        //   import type { PlanEntryType } from "~/lib/api/types/meal-plan";
      depends_on:
        - "~/lib/api/types/meal-plan (PlanEntryType)"
      acceptance_criteria:
        - "DraftPlanEntry interface exported from types.ts is structurally identical to the previous in-composable definition."
        - "use-optimizer-planner.ts imports DraftPlanEntry from './types' and no longer declares it locally."
        - "`task ui:check` (type-check + lint) passes."

    - path: "frontend/app/composables/optimizer/planner-diff.ts"
      action: create
      purpose: "Single pure helper that checks whether the mutable payload fields of two DraftPlanEntry records differ. Used by both the unsaved-changes detector and the update-partitioning in savePlan."
      signature: |
        import type { DraftPlanEntry } from "./types";

        /** Fields that represent mutable payload carried to the backend (not identity/bookkeeping). */
        export const DRAFT_PAYLOAD_FIELDS = ["recipeId", "entryType", "date"] as const;

        /**
         * Returns true when any mutable payload field differs between two draft entries.
         * Does NOT compare existingEntryId (used as identity/match key by callers).
         * Identity+length concerns (slot membership, array size) are checked by the caller.
         */
        export function draftEntryFieldsChanged(a: DraftPlanEntry, b: DraftPlanEntry): boolean;
      depends_on:
        - "./types (DraftPlanEntry)"
      acceptance_criteria:
        - "Pure module — no Vue/Nuxt/composables imports."
        - "Returns true when exactly one of recipeId, entryType, date differs; false when all three match (regardless of existingEntryId, localId, order, or recipe display fields)."
        - "DRAFT_PAYLOAD_FIELDS is a readonly tuple so call sites can iterate for debug/logging without drift."

    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      action: modify
      purpose: "Delegate both diff sites to draftEntryFieldsChanged; drop the inline field-by-field comparisons."
      signature: |
        // Top of file:
        import type { DraftPlanEntry } from "./types";        // moved
        import { draftEntryFieldsChanged } from "./planner-diff";

        // hasUnsavedChanges (lines 113–131) becomes:
        const hasUnsavedChanges: ComputedRef<boolean> = computed(() => {
          const draft = draftEntries.value;
          const snapshot = loadedEntriesSnapshot;
          const allKeys = new Set([...draft.keys(), ...snapshot.keys()]);
          for (const key of allKeys) {
            const draftArr = draft.get(key) ?? [];
            const snapArr = snapshot.get(key) ?? [];
            if (draftArr.length !== snapArr.length) return true;
            for (let i = 0; i < draftArr.length; i++) {
              if (draftArr[i].existingEntryId !== snapArr[i].existingEntryId) return true;
              if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;
            }
          }
          return false;
        });

        // savePlan() update branch (lines 394–411) becomes:
        const snapEntry = snapArr.find(s => s.existingEntryId === draftEntry.existingEntryId);
        if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry)) {
          toUpdate.push({ id: draftEntry.existingEntryId, payload: { ... } });
        }
      depends_on:
        - "./types"
        - "./planner-diff"
      acceptance_criteria:
        - "No remaining inline `recipeId !==` / `entryType !==` / `date !==` comparisons between DraftPlanEntry values in this file."
        - "Behavior of hasUnsavedChanges is unchanged: still flips when arrays change length, when existingEntryId drifts (e.g. after save), or when any payload field changes."
        - "savePlan() still partitions into the same toCreate/toUpdate/toDelete sets on representative fixtures."
        - "`task ui:check` and `task ui:test` pass."

    - path: "frontend/app/composables/optimizer/planner-diff.test.ts"
      action: create
      purpose: "Unit tests for draftEntryFieldsChanged covering each compared field and the negative case."
      signature: |
        import { describe, it, expect } from "vitest";
        import { draftEntryFieldsChanged } from "./planner-diff";
        import type { DraftPlanEntry } from "./types";

        function makeEntry(overrides: Partial<DraftPlanEntry> = {}): DraftPlanEntry { ... }

        describe("draftEntryFieldsChanged", () => {
          it("returns false for identical entries");
          it("returns true when recipeId differs (including null → string)");
          it("returns true when entryType differs (e.g., 'breakfast' vs 'dinner')");
          it("returns true when date differs");
          it("returns false when only existingEntryId differs");   // identity, not payload
          it("returns false when only localId / order / recipeName / recipeSlug differ");  // display-only
        });
      depends_on:
        - "./planner-diff"
        - "./types"
      acceptance_criteria:
        - "Six test cases above all pass under `task ui:test`."
        - "Test file does not import from use-optimizer-planner.ts."

    - path: "mealie/services/optimizer/pantry.py"
      action: modify
      purpose: "Replace the positional 4-tuple transport with a NamedTuple record at all three sites; behavior is unchanged."
      signature: |
        from typing import NamedTuple
        # ... existing imports ...

        class DeductionItem(NamedTuple):
            """Internal transport for _deduct_items. Positional kept compatible with prior tuple shape."""
            food_id: UUID4
            quantity: float
            unit_obj: object | None            # resolved IngredientUnit (or None)
            original_unit_id: UUID4 | None     # raw FK column value; non-None with unit_obj=None implies orphaned FK

        class PantryService:
            ...
            def _deduct_items(
                self,
                items: list[DeductionItem],
                pantry_map: dict[UUID4, PantryItemOut],
            ) -> list[PantryItemOut]:
                """Unchanged body — iterate `for food_id, qty, unit_obj, original_unit_id in items:` still works."""
                ...

            def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
                # build list[DeductionItem] instead of list[tuple]
                ...

            def deduct_shopping_items(self, shopping_list_item_ids: list[UUID4]) -> list[PantryItemOut]:
                # build list[DeductionItem] instead of list[tuple]
                ...
      depends_on:
        - "typing.NamedTuple (stdlib)"
      acceptance_criteria:
        - "No `tuple[UUID4, float, object | None, UUID4 | None]` annotation remains in this module."
        - "Existing tests in tests/unit_tests/services_tests/test_pantry_service.py continue to pass unchanged (public behavior preserved)."
        - "`task py:check` passes (ruff + mypy/pyright config already in repo)."
        - "Destructuring `for food_id, qty, unit_obj, original_unit_id in items:` inside `_deduct_items` still binds as before (NamedTuple iteration order matches declaration order)."

    - path: "tests/unit_tests/services_tests/test_pantry_service.py"
      action: modify
      purpose: "Add a DeductItemsOrphanedFKTests class exercising the orphaned-FK skip path at pantry.py:335–337."
      signature: |
        class DeductItemsOrphanedFKTests:
            """Tests for _deduct_items orphaned-FK guard (pantry.py:335–337)."""

            def _service(self) -> PantryService:
                """Build a PantryService without a DB; replace pantry_items with a MagicMock for update(...)."""
                ...

            def test_orphaned_fk_skips_deduction(self):
                """
                Given a source DeductionItem whose unit_obj did not resolve (unit_obj=None) but
                whose original_unit_id IS set (FK column present), AND a pantry item with no unit,
                _deduct_items must NOT deduct — because equal `unit_id=None` on both sides is not a
                safe 'unitless vs unitless' match when the shopping item originally had a unit FK.
                Asserts:
                  - returned list is empty
                  - pantry_items.update is NOT called
                  - running_qty for the food is unchanged
                """

            def test_both_genuinely_unitless_deducts(self):
                """Control case: unit_obj=None AND original_unit_id=None on source, pantry unit=None → deduction proceeds."""
      depends_on:
        - "mealie.services.optimizer.pantry (PantryService, DeductionItem)"
        - "existing _make_food / _make_pantry_item factories (lines 14–67)"
      acceptance_criteria:
        - "Orphaned-FK test: `_deduct_items` returns `[]` and `self.pantry_items.update` is not called."
        - "Control test: `_deduct_items` returns 1 updated item and update is called exactly once."
        - "Tests import DeductionItem from mealie.services.optimizer.pantry (not from a private helper)."

    - path: "tests/integration_tests/test_repository_factory.py"
      action: modify
      purpose: "Add coverage for RepositoryGeneric.get_many(): empty input, batch fetch, missing IDs, tenant scoping, named-key lookup."
      signature: |
        def test_get_many_empty_input_returns_empty_list(session: Session):
            """values=[] short-circuits to []."""
            ...

        def test_get_many_returns_all_matching_ids(session: Session):
            """Seed N records, request all N by PK, assert set equality on returned IDs."""
            ...

        def test_get_many_silently_excludes_missing_ids(session: Session):
            """Mix existing + nonexistent UUIDs; missing ones omitted, no exception."""
            ...

        def test_get_many_respects_tenant_scoping(session: Session):
            """Create rows in group_1 and group_2; group_1_repos.get_many([...]) returns only group_1 rows."""
            # Pattern from lines 131–143 (ingredient_foods) + 287–294 (shopping lists).

        def test_get_many_supports_named_key(session: Session):
            """Pass `key="slug"` with Recipe repository; returns recipes whose slugs match. Reuse the slug-keyed pattern at lines 237–244."""
      depends_on:
        - "mealie.repos.all_repositories.get_repositories"
        - "existing factories in tests.utils.factories"
      acceptance_criteria:
        - "All five tests pass against the PostgreSQL test DB (`task py:test -- -k get_many`)."
        - "Assertions use set equality (not list equality), honoring the 'order is NOT guaranteed' contract in repository_generic.py:189."
        - "Tenant-scope test uses both group_1_repos and group_2_repos (per existing file convention) to prove isolation is symmetric."

handoff_to_deep_plan:
  skip_exploration:
    - "frontend/app/composables/optimizer/use-optimizer-planner.ts — diff locations already identified (113–131, 381–413)."
    - "mealie/services/optimizer/pantry.py — tuple declaration (313), callers (377, 396), orphaned-FK branch (335–337) already identified."
    - "mealie/repos/repository_generic.py — get_many signature/body already captured (181–199)."
    - "tests/unit_tests/services_tests/test_pantry_service.py — factories and harness pattern already captured (14–86)."
    - "tests/integration_tests/test_repository_factory.py — existing get_one tenant-scope patterns already captured (131–143, 172–177, 237–244, 287–294)."
    - "frontend/app/composables/optimizer/scoring-engine.test.ts + use-expiration-helpers.test.ts — vitest shape confirmed; no re-read needed."
  known_patterns:
    - "Pure helper + colocated .test.ts: apply for planner-diff.ts / planner-diff.test.ts (matches scoring-engine, use-expiration-helpers)."
    - "Shared optimizer TS types live in frontend/app/composables/optimizer/types.ts — extend, do not create a new planner-types.ts."
    - "Repository integration tests: build per-group repos with `get_repositories(session, group_id=...)`, seed via domain schemas, assert with get_one / (now) get_many."
    - "PantryService unit tests: `object.__new__(PantryService)` + manually set `converter` and, where needed, `pantry_items = MagicMock()` to bypass DB without touching PantryService.__init__."
    - "NamedTuple destructuring preserves positional compatibility: the existing `for a, b, c, d in items:` loop inside _deduct_items needs no change."
  decisions_made:
    - "Single diff helper (draftEntryFieldsChanged) instead of two near-duplicates: hasUnsavedChanges checks existingEntryId + length inline, then delegates payload comparison. Rationale: Codex CONCERN #2 — two exported helpers for two call sites is over-factored."
    - "DraftPlanEntry moves to types.ts rather than a new planner-types.ts. Rationale: Codex CONCERN #1 + existing directory convention (types.ts is already the shared optimizer types module)."
    - "NamedTuple over frozen dataclass for DeductionItem. Rationale: user's original suggestion mentions both; NamedTuple preserves positional destructuring at _deduct_items body with zero body changes and minimal ceremony."
    - "Pantry orphaned-FK test asserts behavior (no update call, empty return, quantity unchanged) rather than tuple/NamedTuple shape. Rationale: Codex CONCERN #5 — keep tests decoupled from internal transport representation."
    - "get_many tests use set equality and reuse existing session + per-group repo fixtures. Rationale: Codex recommendation — honor the documented 'order not guaranteed' contract and avoid introducing new fixtures."
  warnings:
    - "The `for food_id, qty, unit_obj, original_unit_id in items:` loop at pantry.py:324 relies on NamedTuple iteration. If deep-plan opts for @dataclass instead, that line must be rewritten to attribute access — do not change the transport type without also rewriting the loop."
    - "hasUnsavedChanges MUST keep the `draftArr[i].existingEntryId !== snapArr[i].existingEntryId` check inline. Rationale: after a save, the snapshot is rebuilt with fresh existingEntryId values; if the helper absorbed this field, saves would appear to produce unsaved changes forever."
    - "Do NOT add a `recipeName`/`recipeSlug` comparison to draftEntryFieldsChanged. Those are display-side denormalizations; they are derived from `recipeId` via recipeDataMap and would cause spurious diffs if the recipe data refreshes."
    - "The test `test_get_many_supports_named_key` must pick a repository whose model has a queryable alt-key column that is part of the schema (e.g., Recipe.slug). Avoid inventing a test-only model."
    - "`task py:migrate` is NOT required for this spec — no schema changes."

open_questions:
  - question: "Should `draftEntryFieldsChanged` also compare an as-yet-unused `notes` field that exists on ReadPlanEntry but not on DraftPlanEntry today?"
    blocking: false
    default_assumption: "No — DraftPlanEntry does not carry it today; adding it is out of scope and would expand the non-goals list."
  - question: "Should the orphaned-FK test also exercise the non-guarded control case (source has valid unit_obj but pantry unit is None) to lock down the trio of branches at pantry.py:335–349?"
    blocking: false
    default_assumption: "Add the two explicitly requested cases (orphaned FK skip + both-unitless). A third case is nice-to-have but not required by the user goal."
  - question: "For get_many tenant-scope tests, which repository to use (ingredient_foods, webhooks, shopping_lists, recipes)?"
    blocking: false
    default_assumption: "Mirror test_repository_factory.py conventions: use ingredient_foods for the group-scope case (matches lines 131–143) and recipes for the named-key case (matches slug at 237–244)."

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Codex returned CONCERNS (feasible, but over-factored in spots). Verbatim summary of the five issues and how this spec resolves each:

    1. `planner-diff.ts` is reasonable, but only if DraftPlanEntry ownership is cleaned up. A helper module importing DraftPlanEntry from the stateful composable creates a wrong-direction dependency.
       → Resolved: DraftPlanEntry is relocated to `frontend/app/composables/optimizer/types.ts` (the already-established shared types file); both the composable and the new helper import it from there.

    2. Two planner comparison helpers are probably not warranted for two call sites.
       → Resolved: spec ships ONE helper (`draftEntryFieldsChanged`, payload-only). `hasUnsavedChanges` keeps the existingEntryId and array-length checks inline where the identity semantics live.

    3. Applying one uniform helper everywhere is acceptable only if semantics are explicit.
       → Resolved: helper is explicitly named *FieldsChanged* and its docstring states that identity/length concerns are the caller's responsibility. DRAFT_PAYLOAD_FIELDS is exported so the semantic contract is self-documenting.

    4. `DeductionItem` is a good change, but frozen dataclass is not clearly better than NamedTuple.
       → Resolved: spec selects NamedTuple — it preserves the existing positional unpack at pantry.py:324 with zero body changes, matches the user's original wording, and is the lighter option.

    5. Pantry test should target behavior, not transport shape.
       → Resolved: orphaned-FK test asserts empty return list + `pantry_items.update` not called; it does not inspect the DeductionItem internals.

    Codex additionally validated the `get_many` test plan against the actual repository_generic.py contract (empty → [], order not guaranteed, missing IDs excluded, tenant scoping, arbitrary key), and endorsed set-equality assertions plus reuse of existing session + per-group repo fixtures. One specific recommendation adopted: use Recipe.slug for the named-key test (mirrors existing get_one slug assertions at lines 237–244), not an invented key.

    No INVALID findings. All remaining CONCERNS are addressed in the Decisions Made list; deep-plan can proceed with confidence=high.
```
