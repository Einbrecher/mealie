```yaml
spec_metadata:
  goal: "Persist the slotOverlapPenalty scoring weight to the backend optimizer_config table, eliminating the client-side-only workaround so the Complement Contrast slider value survives page reloads like all other scoring weights."
  constraints:
    - "Must follow existing weight column pattern (Float, NOT NULL, server_default)"
    - "Migration must chain off current head c3d4e5f6a7b8 (add_pantry_use_priority)"
    - "All code stays in optimizer/ subdirectories per fork isolation rules"
    - "API must remain backwards-compatible — existing clients that omit the new field get default 0.7"
    - "No new upstream file modifications"
  non_goals:
    - "Validating weight range (min/max clamping) on the backend — not done for any other weight"
    - "Adding per-user config (config is per-household, consistent with existing design)"
    - "Changing the scoring algorithm itself — only persisting the weight"
    - "Adding backend tests for the config endpoint (none exist currently)"
  timestamp: "2026-04-14T16:49:25"
  confidence: low
  survey_consumed: false

current_state:
  summary: "The optimizer_config table persists 6 scoring weights via a standard column→model→schema→TS-type→composable pipeline. The slotOverlapPenalty weight uses a parallel client-side-only path: a local variable in use-optimizer-planner.ts, a separate prop/emit on ConfigPanel, and a separate ref in planner.vue. The scoring engine already consumes slotOverlapPenalty from the ScoringWeights interface — it doesn't care where the value originates."
  relevant_files:
    - path: "mealie/db/models/optimizer/config.py"
      purpose: "SQLAlchemy model for optimizer_config table — defines all weight columns"
      reuse_potential: high
    - path: "mealie/schema/optimizer/config.py"
      purpose: "Pydantic schemas (Update/Save/Out) for config API"
      reuse_potential: high
    - path: "mealie/repos/optimizer/config.py"
      purpose: "Repository with get_or_create_default() — auto-creates config row with defaults"
      reuse_potential: high
    - path: "mealie/routes/optimizer/controller_config.py"
      purpose: "GET/PUT /api/households/optimizer/config endpoints"
      reuse_potential: high
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "TypeScript interfaces mirroring backend schemas (camelCase)"
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      purpose: "Main planner composable — contains the client-side workaround (currentSlotPenalty, mapConfigToWeights with 2 params, setSlotOverlapPenalty)"
      reuse_potential: high
    - path: "frontend/app/components/optimizer/ConfigPanel.vue"
      purpose: "Config slider panel — has separate slotOverlapPenalty prop/emit path"
      reuse_potential: high
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue"
      purpose: "Planner page — has localSlotPenalty ref and onSlotPenaltyUpdate handler"
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/types.ts"
      purpose: "ScoringWeights interface — already has slotOverlapPenalty field (consumer, not changed)"
      reuse_potential: high
    - path: "frontend/app/composables/optimizer/scoring-engine.ts"
      purpose: "scoreRecipes() — consumes weights.slotOverlapPenalty (consumer, not changed)"
      reuse_potential: high
    - path: "mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py"
      purpose: "Latest migration in optimizer chain — new migration's down_revision"
      reuse_potential: medium
  patterns_identified:
    - "Weight column pattern: Float, nullable=False, default=X, server_default='X' — used for all 6 existing weights"
    - "Schema inheritance: OptimizerConfigSave and OptimizerConfigOut extend OptimizerConfigUpdate — new fields auto-propagate"
    - "Config round-trip: GET loads config → composable maps to ScoringWeights → PUT saves config → composable re-maps"
    - "ConfigPanel debounced emit: localConfig reactive copy + 500ms debounce → emit('update') → parent calls updateConfig()"

gaps:
  exists:
    - component: "Config API endpoints"
      location: "mealie/routes/optimizer/controller_config.py"
      notes: "GET/PUT endpoints are generic — they serialize whatever fields the schema defines. No endpoint changes needed."
    - component: "Repository get_or_create_default"
      location: "mealie/repos/optimizer/config.py"
      notes: "Creates default rows using OptimizerConfigSave() which inherits defaults. Adding the field to OptimizerConfigUpdate with default=0.7 propagates automatically."
    - component: "Frontend API client"
      location: "frontend/app/lib/api/user/optimizer-pantry.ts"
      notes: "OptimizerConfigApi.getConfig() and updateConfig() are generic — they pass whatever the TS types define. No changes needed."
    - component: "Scoring engine consumer"
      location: "frontend/app/composables/optimizer/scoring-engine.ts:267"
      notes: "Already reads weights.slotOverlapPenalty. No changes needed — only the source of the value changes."
    - component: "ScoringWeights interface"
      location: "frontend/app/composables/optimizer/types.ts:8"
      notes: "Already has slotOverlapPenalty field. No changes needed."
    - component: "i18n keys"
      location: "frontend/app/lang/messages/en-US.json"
      notes: "optimizer.config.slot-overlap-penalty-weight key already exists."
  partial: []
  missing:
    - component: "Database column"
      rationale: "optimizer_config table has no slot_overlap_penalty_weight column. Must be added via Alembic migration."
    - component: "SQLAlchemy model field"
      rationale: "OptimizerConfigModel has no slot_overlap_penalty_weight mapped column."
    - component: "Pydantic schema field"
      rationale: "OptimizerConfigUpdate has no slot_overlap_penalty_weight field."
    - component: "TypeScript type field"
      rationale: "OptimizerConfigUpdate interface has no slotOverlapPenaltyWeight property."

specification:
  files:
    - path: "mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py"
      action: create
      purpose: "Alembic migration to add slot_overlap_penalty_weight column to optimizer_config table"
      signature: |
        """add slot overlap penalty weight

        Revision ID: d4e5f6a7b8c9
        Revises: c3d4e5f6a7b8
        Create Date: 2026-04-14 17:00:00.000000
        """

        revision = "d4e5f6a7b8c9"
        down_revision: str | None = "c3d4e5f6a7b8"

        def upgrade():
            # op.add_column("optimizer_config", sa.Column("slot_overlap_penalty_weight", sa.Float(), nullable=False, server_default="0.7"))
            ...

        def downgrade():
            # op.drop_column("optimizer_config", "slot_overlap_penalty_weight")
            ...
      depends_on:
        - "mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py"
      acceptance_criteria:
        - "Running `alembic upgrade head` adds the column with default 0.7"
        - "Existing rows in optimizer_config receive 0.7 via server_default"
        - "Running `alembic downgrade -1` removes the column cleanly"

    - path: "mealie/db/models/optimizer/config.py"
      action: modify
      purpose: "Add slot_overlap_penalty_weight mapped column to OptimizerConfigModel"
      signature: |
        # Add after rating_weight (line 32):
        slot_overlap_penalty_weight: Mapped[float] = mapped_column(
            Float, nullable=False, default=0.7, server_default="0.7"
        )
      depends_on:
        - "mealie/alembic/versions/2026-04-14-17.00.00_d4e5f6a7b8c9_add_slot_overlap_penalty_weight.py"
      acceptance_criteria:
        - "OptimizerConfigModel has slot_overlap_penalty_weight column after rating_weight"
        - "Column definition matches the pattern of other weight columns (Float, nullable=False, default, server_default)"

    - path: "mealie/schema/optimizer/config.py"
      action: modify
      purpose: "Add slot_overlap_penalty_weight field to OptimizerConfigUpdate"
      signature: |
        class OptimizerConfigUpdate(MealieModel):
            # ... existing fields ...
            rating_weight: float = 0.2
            slot_overlap_penalty_weight: float = 0.7  # ADD after rating_weight
            prep_time_budget_minutes: int | None = None
            # ... rest unchanged ...
      depends_on:
        - "mealie/db/models/optimizer/config.py"
      acceptance_criteria:
        - "OptimizerConfigUpdate has slot_overlap_penalty_weight with default 0.7"
        - "OptimizerConfigSave and OptimizerConfigOut inherit the field automatically"
        - "GET /api/households/optimizer/config returns slotOverlapPenaltyWeight in response"
        - "PUT with or without slotOverlapPenaltyWeight works (default kicks in)"

    - path: "frontend/app/lib/api/types/optimizer.ts"
      action: modify
      purpose: "Add slotOverlapPenaltyWeight to OptimizerConfigUpdate TypeScript interface"
      signature: |
        export interface OptimizerConfigUpdate {
          // ... existing fields ...
          ratingWeight: number;
          slotOverlapPenaltyWeight: number;  // ADD after ratingWeight
          prepTimeBudgetMinutes: number | null;
          // ... rest unchanged ...
        }
      depends_on:
        - "mealie/schema/optimizer/config.py"
      acceptance_criteria:
        - "OptimizerConfigUpdate has slotOverlapPenaltyWeight: number"
        - "OptimizerConfigOut inherits the field via extends"

    - path: "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      action: modify
      purpose: "Remove client-side slot penalty workaround — read from config instead"
      signature: |
        # REMOVE: let currentSlotPenalty = 0.7 (line 189)
        # REMOVE: setSlotOverlapPenalty function (lines 466-472)
        # REMOVE: setSlotOverlapPenalty from UsePlannerReturn interface (line 44)
        # REMOVE: setSlotOverlapPenalty from return object (line 500)

        # CHANGE mapConfigToWeights signature:
        function mapConfigToWeights(cfg: OptimizerConfigOut): ScoringWeights {
            return {
                # ... existing mappings ...
                slotOverlapPenalty: cfg.slotOverlapPenaltyWeight,  # was: currentSlotPenalty parameter
                # ...
            };
        }

        # CHANGE all call sites from mapConfigToWeights(cfg, currentSlotPenalty) to mapConfigToWeights(cfg):
        # - loadData() line 222
        # - updateConfig() line 456
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "No local currentSlotPenalty variable exists"
        - "No setSlotOverlapPenalty function exists"
        - "mapConfigToWeights takes only cfg parameter"
        - "slotOverlapPenalty in ScoringWeights is populated from cfg.slotOverlapPenaltyWeight"
        - "UsePlannerReturn interface no longer has setSlotOverlapPenalty"

    - path: "frontend/app/components/optimizer/ConfigPanel.vue"
      action: modify
      purpose: "Unify slot penalty slider into the standard config debounced-emit path"
      signature: |
        # REMOVE from defineProps: slotOverlapPenalty: number (line 117)
        # REMOVE from defineEmits: (e: "update-slot-penalty", value: number): void (line 122)
        # REMOVE: localSlotPenalty ref (line 128)
        # REMOVE: penaltyDebounceTimer (line 131)
        # REMOVE: watcher for props.slotOverlapPenalty (lines 149-151)
        # REMOVE: onSlotPenaltyChange function (lines 163-167)

        # Props becomes:
        defineProps<{
          config: OptimizerConfigOut | null;
        }>()

        # Emits becomes:
        defineEmits<{
          (e: "update", config: OptimizerConfigUpdate): void;
        }>()

        # ADD slotOverlapPenaltyWeight to localConfig initialization in watch:
        watch(() => props.config, (newConfig) => {
          if (newConfig) {
            localConfig.value = {
              # ... existing fields ...
              slotOverlapPenaltyWeight: newConfig.slotOverlapPenaltyWeight,  # ADD
              # ...
            };
          }
        }, { immediate: true });

        # CHANGE slot penalty slider from v-model="localSlotPenalty" @update:model-value="onSlotPenaltyChange"
        # TO: v-model="localConfig.slotOverlapPenaltyWeight" @update:model-value="onConfigChange"
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
      acceptance_criteria:
        - "ConfigPanel has only one prop: config"
        - "ConfigPanel has only one emit: update"
        - "Slot penalty slider uses localConfig.slotOverlapPenaltyWeight and onConfigChange"
        - "All 7 sliders follow the same reactive + debounced emit path"

    - path: "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue"
      action: modify
      purpose: "Remove separate slot penalty handling — ConfigPanel now handles it via standard config path"
      signature: |
        # REMOVE from composable destructure: setSlotOverlapPenalty (line 174)
        # REMOVE: localSlotPenalty ref (line 180)
        # REMOVE: onSlotPenaltyUpdate function (lines 252-255)

        # CHANGE ConfigPanel binding from:
        #   <ConfigPanel :config="config" :slot-overlap-penalty="localSlotPenalty"
        #     @update="onConfigUpdate" @update-slot-penalty="onSlotPenaltyUpdate" />
        # TO:
        #   <ConfigPanel :config="config" @update="onConfigUpdate" />
      depends_on:
        - "frontend/app/components/optimizer/ConfigPanel.vue"
        - "frontend/app/composables/optimizer/use-optimizer-planner.ts"
      acceptance_criteria:
        - "No localSlotPenalty ref exists"
        - "No onSlotPenaltyUpdate function exists"
        - "No setSlotOverlapPenalty in composable destructure"
        - "ConfigPanel binding has no :slot-overlap-penalty or @update-slot-penalty"
        - "Adjusting the Complement Contrast slider persists across page reloads"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/db/models/optimizer/config.py — fully read, all 53 lines inspected"
    - "mealie/schema/optimizer/config.py — fully read, all 33 lines inspected"
    - "mealie/repos/optimizer/config.py — fully read, all 33 lines. No changes needed."
    - "mealie/routes/optimizer/controller_config.py — fully read, all 21 lines. No changes needed."
    - "frontend/app/lib/api/types/optimizer.ts — fully read, all 124 lines"
    - "frontend/app/lib/api/user/optimizer-pantry.ts — fully read, all 76 lines. No changes needed."
    - "frontend/app/composables/optimizer/types.ts — fully read, all 48 lines. No changes needed."
    - "frontend/app/composables/optimizer/use-optimizer-planner.ts — fully read, all 506 lines"
    - "frontend/app/components/optimizer/ConfigPanel.vue — fully read, all 169 lines"
    - "frontend/app/pages/g/[groupSlug]/optimizer/planner.vue — fully read, all 328 lines"
    - "frontend/app/composables/optimizer/scoring-engine.ts — lines 170-280 inspected (slotOverlapScore + scoreRecipes). No changes needed."
    - "mealie/alembic/versions/2026-04-13-15.00.00_c3d4e5f6a7b8_add_pantry_use_priority.py — fully read, migration pattern reference"
  known_patterns:
    - "Weight column: Float, nullable=False, default=X, server_default='X' — copy from rating_weight"
    - "Schema field: simple typed field with default on OptimizerConfigUpdate — inherited by Save/Out"
    - "TS type field: camelCase number property in interface — inherited by OptimizerConfigOut via extends"
    - "ConfigPanel slider: v-model on localConfig property + @update:model-value='onConfigChange' + debounce 500ms"
    - "Migration revision chain: down_revision must be c3d4e5f6a7b8"
  decisions_made:
    - "Column name slot_overlap_penalty_weight: follows existing snake_case weight naming, maps to camelCase slotOverlapPenaltyWeight via Mealie's auto-alias config"
    - "Default 0.7: matches the existing client-side default. No behavioral change for users."
    - "No validation/clamping: consistent with all other weight fields, which have no min/max constraints"
    - "No repository changes: get_or_create_default() uses OptimizerConfigSave() which inherits defaults from OptimizerConfigUpdate"
    - "No API endpoint changes: controller is generic, serializes whatever the schema defines"
    - "No scoring engine changes: scoring-engine.ts reads from ScoringWeights.slotOverlapPenalty, which is populated by mapConfigToWeights — only the data source changes"
  warnings:
    - "The scoring-engine.test.ts has slotOverlapPenalty: 0.7 in its defaultWeights() helper — this is already correct and needs no change, but verify it still passes"
    - "The migration revision ID d4e5f6a7b8c9 is a placeholder — Alembic generate may produce a different ID"
    - "If any other branch adds a migration with down_revision=c3d4e5f6a7b8 before this ships, there will be a head conflict"
    - "The ConfigPanel watch for props.config must include slotOverlapPenaltyWeight in the localConfig initialization — if missed, the slider will show 0 or undefined on load"

open_questions:
  - question: "Should the migration use alembic revision --autogenerate or be hand-written?"
    blocking: false
    default_assumption: "Hand-written, matching the style of the existing use_priority migration (simpler, more predictable)"
  - question: "Should we add backend validation (min=0, max=2) to match the slider range?"
    blocking: false
    default_assumption: "No — none of the other 6 weights have backend validation. The slider enforces the range on the frontend."

agent_responses:
  codex_verdict: SKIPPED
  codex_notes: "Codex validation unavailable — model not supported with current account configuration. Specification proceeds at low confidence. Manual review recommended for: (1) migration revision chain correctness, (2) Pydantic model_config from_attributes=True handling of new field, (3) no hidden consumers of setSlotOverlapPenalty beyond the 3 files identified."
```
