# Concept: Persist slotOverlapPenalty to Backend OptimizerConfig

## Problem Statement

The meal planner's complement scoring feature uses a `slotOverlapPenalty` weight to penalize recipe candidates that are too similar to recipes already placed in the active slot. For example, if a user places a chicken stir-fry as their dinner entree, the scoring engine should deprioritize other chicken dishes and promote vegetable sides, salads, or rice dishes as complement suggestions.

This weight is currently **client-side only** — it defaults to `0.7` in the Vue composable and resets to that default on every page reload. The user can adjust it via the ConfigPanel's "Complement Contrast" slider, but the adjustment is lost when they navigate away.

Every other scoring weight (overlap, pantry utilization, pantry urgency, protein diversity, category balance, rating) is persisted to the backend `optimizer_config` table and round-trips through the `GET/PUT /api/households/optimizer/config` endpoints. The slot overlap penalty is the only weight that doesn't persist, creating an inconsistent user experience.

## Current Architecture

### Backend (persisted weights)

**Database table**: `optimizer_config` (created by migration `2026-04-13-14.00.00_b2c3d4e5f6a7`)

Columns for scoring weights:
- `overlap_weight` (Float, default 1.0)
- `pantry_utilization_weight` (Float, default 0.6)
- `pantry_urgency_weight` (Float, default 0.8)
- `protein_diversity_weight` (Float, default 0.5)
- `category_balance_weight` (Float, default 0.3)
- `rating_weight` (Float, default 0.2)
- `prep_time_budget_minutes` (Integer, nullable)
- `perishable_label_keywords` (JSON array)
- `shelf_stable_label_keywords` (JSON array)

**No `slot_overlap_penalty_weight` column exists.**

**SQLAlchemy model**: `mealie/db/models/optimizer/config.py` — `OptimizerConfigModel` class with `mapped_column` for each weight above.

**Pydantic schemas**: `mealie/schema/optimizer/config.py`:
- `OptimizerConfigUpdate` — input schema for PUT endpoint (all fields with defaults)
- `OptimizerConfigSave` — extends Update, adds `group_id` and `household_id`
- `OptimizerConfigOut` — extends Update, adds `id`, `group_id`, `household_id`

**Repository**: `mealie/repos/optimizer/config.py` — `RepositoryOptimizerConfig` with `get_or_create_default()` that auto-creates a config row with defaults on first access.

**API endpoints**: `mealie/routes/optimizer/controller_config.py`:
- `GET /api/households/optimizer/config` → returns `OptimizerConfigOut`
- `PUT /api/households/optimizer/config` → accepts `OptimizerConfigUpdate`, returns `OptimizerConfigOut`

### Frontend (client-side workaround)

**TypeScript types**: `frontend/app/lib/api/types/optimizer.ts`:
- `OptimizerConfigUpdate` and `OptimizerConfigOut` mirror the backend schemas (camelCase)
- **No `slotOverlapPenaltyWeight` field** in either type

**Scoring types**: `frontend/app/composables/optimizer/types.ts`:
- `ScoringWeights` interface **does** have `slotOverlapPenalty: number`
- This field is populated from a local variable, not from the config API response

**Composable**: `frontend/app/composables/optimizer/use-optimizer-planner.ts`:
- `let currentSlotPenalty = 0.7` — a plain variable (not reactive, not API-backed)
- `mapConfigToWeights(cfg, currentSlotPenalty)` manually injects the local penalty into the scoring weights alongside the API-backed weights
- `setSlotOverlapPenalty(value)` updates the local variable and re-maps weights — **does not** call the config API
- The ConfigPanel has a separate emit path (`update-slot-penalty`) distinct from the backend config emit (`update`)

**ConfigPanel**: `frontend/app/components/optimizer/ConfigPanel.vue`:
- Has a separate `slotOverlapPenalty` prop and `update-slot-penalty` emit
- The 6 backend-persisted sliders use `@update` → `onConfigUpdate()` → `api.optimizer.config.updateConfig()`
- The slot penalty slider uses `@update-slot-penalty` → `onSlotPenaltyUpdate()` → `setSlotOverlapPenalty()` (local only)

**Planner page**: `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue`:
- `localSlotPenalty = ref(0.7)` — page-level state, disconnected from API
- `onSlotPenaltyUpdate(value)` updates the local ref and calls `setSlotOverlapPenalty()`
- On page load, the penalty always starts at 0.7 regardless of what the user previously set

### i18n keys (already exist)

- `optimizer.config.slot-overlap-penalty-weight`: "Complement Contrast" — label for the slider
- `optimizer.planner.slot-overlap-penalty-weight`: "Complement Contrast" — duplicate in planner namespace

## What Needs to Change

### 1. Alembic Migration

Add a `slot_overlap_penalty_weight` column to the `optimizer_config` table.

- **Type**: `Float`, `nullable=False`, `default=0.7`, `server_default="0.7"`
- **Pattern**: Identical to the existing weight columns (see `overlap_weight` etc.)
- **Migration revision chain**: Must set `down_revision` to the current head. Check `alembic heads` or look at the most recent migration file. The pantry `use_priority` migration (`2026-04-13-15.00.00_c3d4e5f6a7b8`) is the latest optimizer migration.
- **Downgrade**: `op.drop_column("optimizer_config", "slot_overlap_penalty_weight")`
- **Existing rows**: The `server_default="0.7"` ensures existing rows get the value automatically. No data backfill needed.

### 2. SQLAlchemy Model

In `mealie/db/models/optimizer/config.py`, add to `OptimizerConfigModel`:

```python
slot_overlap_penalty_weight: Mapped[float] = mapped_column(
    Float, nullable=False, default=0.7, server_default="0.7"
)
```

Place it after `rating_weight` to maintain the logical grouping of scoring weights.

### 3. Pydantic Schemas

In `mealie/schema/optimizer/config.py`, add to `OptimizerConfigUpdate`:

```python
slot_overlap_penalty_weight: float = 0.7
```

Since `OptimizerConfigSave` and `OptimizerConfigOut` both extend `OptimizerConfigUpdate`, they inherit the field automatically.

### 4. Frontend TypeScript Types

In `frontend/app/lib/api/types/optimizer.ts`, add to `OptimizerConfigUpdate`:

```typescript
slotOverlapPenaltyWeight: number;
```

`OptimizerConfigOut` extends `OptimizerConfigUpdate`, so it inherits automatically.

### 5. Composable Simplification

In `frontend/app/composables/optimizer/use-optimizer-planner.ts`:

- **Remove** `let currentSlotPenalty = 0.7` local variable
- **Remove** `setSlotOverlapPenalty()` function from the composable's return
- **Update** `mapConfigToWeights()` to read `cfg.slotOverlapPenaltyWeight` instead of accepting `currentSlotPenalty` as a parameter
- **Update** `loadData()` and `updateConfig()` calls that pass `currentSlotPenalty` — they should read from the config response instead
- The function signature simplifies from `mapConfigToWeights(cfg, currentSlotPenalty)` to `mapConfigToWeights(cfg)`

### 6. ConfigPanel Unification

In `frontend/app/components/optimizer/ConfigPanel.vue`:

- **Remove** the separate `slotOverlapPenalty` prop
- **Remove** the separate `update-slot-penalty` emit
- **Add** `slotOverlapPenaltyWeight` to `localConfig` (alongside the other weights)
- **Move** the slot penalty slider to use the same `localConfig` + debounced `onConfigChange` path as all other sliders
- The slider now round-trips through the same `@update → onConfigUpdate → api.optimizer.config.updateConfig()` pipeline

### 7. Planner Page Cleanup

In `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue`:

- **Remove** `localSlotPenalty` ref
- **Remove** `onSlotPenaltyUpdate()` handler
- **Remove** `:slot-overlap-penalty` and `@update-slot-penalty` bindings on ConfigPanel
- **Remove** `setSlotOverlapPenalty` from the composable destructure

## Why This Matters

1. **User experience**: The complement contrast setting is the only scoring weight that resets on reload. Users who tune it expect the setting to persist like all others.
2. **Code simplification**: The current implementation has a parallel state management path (local variable + separate prop + separate emit) just for this one weight. Persisting it eliminates ~30 lines of workaround code across 3 files.
3. **Consistency**: The ConfigPanel currently has 7 sliders that look identical but 6 persist and 1 doesn't. This is invisible to the user until they reload the page.

## Scope and Risk

- **Migration risk**: Low. Adding a nullable-false column with a server_default is safe for existing rows. No data transformation needed.
- **API compatibility**: The field has a default value in the Pydantic schema, so existing API clients that don't send `slotOverlapPenaltyWeight` will get `0.7` automatically.
- **Frontend risk**: Low. The changes simplify code by removing the workaround, not adding new complexity.
- **Testing**: The scoring engine tests already handle `slotOverlapPenalty` in the `ScoringWeights` interface. The backend config endpoint tests (if any) would need a new field in test fixtures.

## Files Involved

| File | Action | Description |
|------|--------|-------------|
| `mealie/alembic/versions/YYYY-MM-DD-HH.MM.SS_<revid>_add_slot_overlap_penalty_weight.py` | create | Migration to add column |
| `mealie/db/models/optimizer/config.py` | modify | Add `slot_overlap_penalty_weight` column |
| `mealie/schema/optimizer/config.py` | modify | Add `slot_overlap_penalty_weight` field to `OptimizerConfigUpdate` |
| `frontend/app/lib/api/types/optimizer.ts` | modify | Add `slotOverlapPenaltyWeight` to `OptimizerConfigUpdate` |
| `frontend/app/composables/optimizer/use-optimizer-planner.ts` | modify | Remove local penalty state, read from config |
| `frontend/app/components/optimizer/ConfigPanel.vue` | modify | Unify slider into standard config path |
| `frontend/app/pages/g/[groupSlug]/optimizer/planner.vue` | modify | Remove separate penalty handling |

## Related References

- Existing config migration: `mealie/alembic/versions/2026-04-13-14.00.00_b2c3d4e5f6a7_add_optimizer_config_table.py`
- Scoring engine (consumer of the weight): `frontend/app/composables/optimizer/scoring-engine.ts:scoreRecipes()` and `slotOverlapScore()`
- Original deferral decision: `docs/plans/2026-04-14-025420-optimizer-ui-revised.md` open question Q3
- Execution report noting the deferral: `docs/execution/2026-04-14-100000-optimizer-ui-revised.md`
