# Pantry Quantity Tracking — Implementation Status

**Date**: 2026-04-13
**Commit**: `39d2e449` on `mealie-next`
**Status**: Implemented and committed. Working end-to-end.

## What Was Built

A full pantry management system that tracks what you have at home, calculates deficits against recipe requirements, and integrates with the existing shopping list to auto-check covered items.

### Core Features (working)

1. **Pantry CRUD** — Add, edit, delete pantry items via UI and API. Each item has a food (from Mealie's food database or a custom name), optional quantity + unit, optional expiration date.

2. **"Always available" toggle** — Marks items like salt/pepper/oil that you never run out of. These bypass quantity checks entirely. When toggled, quantity and unit fields are disabled in the UI.

3. **Deficit calculation** — Given a list of recipe IDs, calculates what you need to buy. Handles 7 cases: no food ID (skip), no recipe quantity (covered), no pantry match (uncovered), always-available (covered), untracked quantity (covered), compatible units (calculate deficit), incompatible units (mark as conversion failed).

4. **Shopping list integration** — When you add a recipe to a shopping list:
   - Fully covered ingredients get auto-checked with note "Already have in pantry"
   - Partially covered ingredients have quantity reduced to the deficit with note "need X, have Y in pantry"
   - Unmatched ingredients are unaffected
   - The integration is wrapped in try/except so failures degrade gracefully without breaking shopping lists

5. **Frontend** — Pantry management page at `/g/{group}/optimizer/pantry` with sidebar navigation (fridge icon between Shopping Lists and Timeline). Auto-saves on field changes. Add/delete via dialogs.

### Architecture

All new code follows fork isolation rules in `optimizer/` subdirectories:

| Layer | File | Description |
|-------|------|-------------|
| Model | `mealie/db/models/optimizer/pantry.py` | `PantryItemModel` — SQLAlchemy model with group_id, household_id, food_id FKs, quantity, unit_id, assume_enough, is_staple, expiration_date. UniqueConstraint(household_id, food_id), CheckConstraint(food_id OR name NOT NULL) |
| Schema | `mealie/schema/optimizer/pantry.py` | 8 Pydantic schemas: Create/Save/Update/UpdateBulk/Out/Pagination + DeficitItem/DeficitReport |
| Repository | `mealie/repos/optimizer/pantry.py` | `RepositoryPantryItem` extends `HouseholdRepositoryGeneric` with `by_food_id` and `by_food_ids` methods |
| Service | `mealie/services/optimizer/pantry.py` | `PantryService` with `calculate_deficit` (7 rules, UnitConverter integration), `check_shopping_items`, helper methods for notes |
| Routes | `mealie/routes/optimizer/controller_pantry.py` | Class-based controller with 5 CRUD endpoints + POST /deficit |
| Migration | `mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py` | Creates pantry_items table |
| Frontend types | `frontend/app/lib/api/types/optimizer.ts` | TypeScript interfaces (manually created, should be regenerated) |
| Frontend API | `frontend/app/lib/api/user/optimizer-pantry.ts` | `PantryItemsApi` extends `BaseCRUDAPI`, registered on `UserApiClient` as `optimizer.pantry` |
| Frontend page | `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue` | Pantry management page |
| Frontend component | `frontend/app/components/optimizer/PantryItemRow.vue` | Row component with auto-save, always-available toggle |
| Tests | `tests/unit_tests/services_tests/test_pantry_service.py` | 12 unit tests covering all deficit rules + shopping item adjustment |
| Tests | `tests/integration_tests/user_household_tests/test_pantry_items.py` | 9 integration tests for API CRUD + validation + household isolation |

### Modified Upstream Files (minimal)

- `mealie/db/models/_all_models.py` — 1 line: `from .optimizer import *`
- `mealie/repos/repository_factory.py` — ~13 lines: imports + `pantry_items` cached_property on `AllRepositories`
- `mealie/routes/__init__.py` — 2 lines: import + include_router for optimizer
- `mealie/services/household_services/shopping_lists.py` — ~5 lines: pantry check call with try/except guard in `bulk_create_items`
- `frontend/app/components/Layout/DefaultLayout.vue` — 5 lines: sidebar nav link
- `frontend/app/lib/icons/icons.ts` — 2 lines: `mdiFridgeOutline` import + `pantry` icon
- `frontend/app/lib/api/client-user.ts` — 4 lines: `OptimizerApi` import + registration

### API Endpoints

All under `/api/households/optimizer/pantry`, require authentication:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List pantry items (paginated) |
| POST | `/` | Create pantry item (201) |
| POST | `/deficit` | Calculate deficit for given recipe IDs |
| GET | `/{item_id}` | Get one pantry item |
| PUT | `/{item_id}` | Update pantry item |
| DELETE | `/{item_id}` | Delete pantry item (204) |

### Deficit Calculation Rules

| # | Condition | Result |
|---|-----------|--------|
| 1 | Recipe ingredient has no food_id | Skip entirely |
| 2 | Recipe has no quantity (None or 0) | deficit=0, covered=True |
| 3 | No pantry match for food_id | deficit=recipe_qty, covered=False |
| 4 | assume_enough=True | deficit=0, covered=True |
| 5 | Pantry quantity is None (untracked) | deficit=0, covered=True |
| 6 | Both have quantity, units compatible | deficit=max(0, recipe-pantry), covered=(deficit==0) |
| 7 | Both have quantity, units incompatible | deficit=recipe_qty, conversion_failed=True, covered=False |

## Open Items / Future Work

### Should address soon

- **Regenerate TypeScript types** — Run `task dev:generate` to auto-generate `frontend/app/lib/api/types/optimizer.ts` from Pydantic schemas, replacing the manually created types.
- **N+1 recipe fetch in deficit endpoint** — `controller_pantry.py` loads each recipe individually in a loop. Should add a batch-by-ids method to `RepositoryRecipes` for when deficit is calculated against many recipes (e.g., full weekly meal plan).
- **Frontend i18n** — Pantry page uses English strings directly. Add translation keys.

### Feature backlog

- **Staple tag UI** — `is_staple` field exists in the database but was removed from the UI as confusing alongside "Always available." Should be resurfaced in an expandable tags/metadata section when there's a feature behind it (e.g., "show me what staples I'm running low on").
- **Bulk import from on_hand** — Migration path from Mealie's boolean `on_hand` mechanism to quantity-tracked pantry items. Users currently must manually add pantry items.
- **Meal plan deficit** — Accept a meal plan ID on the deficit endpoint instead of (or in addition to) individual recipe IDs. Thin wrapper that extracts recipe IDs from the plan.
- **Expiration awareness** — Optionally treat expired pantry items as unavailable in deficit calculation. Currently expiration_date is informational only.
- **Conversion failure UI** — Show a warning indicator on deficit report items where `conversion_failed=True` (units incompatible, e.g., "3 cloves" vs "50 grams").
- **Pantry deduction** — Automatically reduce pantry quantities when a recipe is cooked or a shopping trip is completed.

## Dev Environment Notes

- **Database**: PostgreSQL via `docker compose -f docker/docker-compose.dev.yml up -d`
- **Backend**: `DB_ENGINE=postgres POSTGRES_USER=mealie POSTGRES_PASSWORD=mealie POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_DB=mealie DATA_DIR=/tmp/mealie-test-data PRODUCTION=false API_PORT=9000 API_DOCS=True TOKEN_TIME=256 uv run python mealie/app.py`
- **Frontend**: `cd frontend && yarn dev` (requires corepack-enabled yarn, not Python yarn)
- **Default login**: `changeme@example.com` / `MyPassword`
- **Run unit tests**: `DATA_DIR=/tmp/mealie-test-data PRODUCTION=false uv run python -m pytest tests/unit_tests/services_tests/test_pantry_service.py -v`
- **WSL2 note**: Hot reload is unreliable on `/mnt/d/` — restart dev servers after code changes
- **uv warning**: `pyproject.toml` line 180 `add-bounds = "exact"` triggers a parse warning from uv — harmless, ignore it
