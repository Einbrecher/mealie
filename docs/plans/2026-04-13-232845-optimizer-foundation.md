# Implementation Plan: Optimizer Foundation (Stage A)
Source: docs/specs/2026-04-13-190951-optimizer-foundation.md
Created: 2026-04-13

<plan_metadata>
  <feature>Optimizer Foundation — Config API, use_priority, recipe-foods projection, scoring engine</feature>
  <source_doc>docs/specs/2026-04-13-190951-optimizer-foundation.md</source_doc>
  <total_phases>4</total_phases>
  <total_tasks>16</total_tasks>
  <critical_path>1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 2.6 (router update) → 4.3</critical_path>
  <status>draft</status>
</plan_metadata>

## Overview

Build the backend and frontend foundation for the meal plan optimizer: a per-household config API storing scoring weights, a `use_priority` field on pantry items, a lightweight recipe-foods projection endpoint for the scoring engine, and a pure TypeScript scoring engine with Vue composable wrapper. This is Stage A — no UI beyond API clients; the optimizer page and shopping list enhancements come in later stages.

## Dependencies & Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>Python 3.12 + FastAPI dev environment with Alembic migrations working</description>
  <verification>Run `task py:postgres` and verify API starts on localhost:9000</verification>
</prereq>
<prereq id="P2" type="environment" verified="true">
  <description>Frontend dev environment with Nuxt/Vue/TypeScript/Vitest</description>
  <verification>Run `task ui` and verify dev server starts on localhost:3000</verification>
</prereq>
<prereq id="P3" type="data" verified="true">
  <description>Existing pantry_items table with Alembic migration a1b2c3d4e5f6 as current head</description>
  <verification>Check `mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py` exists</verification>
</prereq>
<prereq id="P4" type="library" verified="true">
  <description>Vitest available for frontend unit tests</description>
  <verification>Run `npx vitest --version` in frontend/</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend — Optimizer Config

<phase id="1" name="Optimizer Config API">

### 1.1 Create OptimizerConfigModel

<task id="1.1" status="pending" depends="" risk="low">
<description>
Create the SQLAlchemy model for per-household optimizer scoring weights at `mealie/db/models/optimizer/config.py`.

**Pattern to follow**: Copy the structure of `mealie/db/models/optimizer/pantry.py` (PantryItemModel). The new model has:
- Table name: `optimizer_config`
- PK: `id` (GUID, default=GUID.generate)
- Tenant FKs: `group_id` (FK → groups.id, not null, indexed), `household_id` (FK → households.id, not null, indexed)
- Weight columns (all `Float`, not null, with `server_default`):
  - `overlap_weight` (default 1.0)
  - `pantry_utilization_weight` (default 0.6)
  - `pantry_urgency_weight` (default 0.8)
  - `protein_diversity_weight` (default 0.5)
  - `category_balance_weight` (default 0.3)
  - `rating_weight` (default 0.2)
- Optional column: `prep_time_budget_minutes` (Integer, nullable, no default)
- JSON columns for configurable label classification:
  - `perishable_label_keywords: Mapped[list[str]]` — JSON list of case-insensitive substrings that identify perishable food labels. Default: `["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"]`
  - `shelf_stable_label_keywords: Mapped[list[str]]` — JSON list of case-insensitive substrings for shelf-stable labels. Default: `["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]`
  - Use `mapped_column(JSON, nullable=False, default=list, server_default="[]")` pattern. Set the Python `default` to a factory returning the default list. Override `server_default` with the JSON-encoded default list string.
- `__table_args__`: `UniqueConstraint("household_id", name="optimizer_config_household_key")`
- Use `@auto_init()` decorator on `__init__`

**Important**: Use `mapped_column(Float, nullable=False, default=1.0, server_default="1.0")` pattern for weight columns. The `server_default` must be a string. For JSON columns, import `JSON` from `sqlalchemy` and use `mapped_column(JSON, nullable=False)` with a Python-side default factory.

Also update `mealie/db/models/optimizer/__init__.py` to add `from .config import *` after the existing `from .pantry import *` line.
</description>

<subtasks>
- [ ] Create `mealie/db/models/optimizer/config.py` with OptimizerConfigModel
- [ ] Add `from .config import *` to `mealie/db/models/optimizer/__init__.py`
</subtasks>

<acceptance>
- `from mealie.db.models.optimizer.config import OptimizerConfigModel` succeeds
- `from mealie.db.models.optimizer import OptimizerConfigModel` succeeds
- Model has all 7 weight/budget columns plus 2 JSON keyword columns plus id, group_id, household_id
- UniqueConstraint on household_id is defined
</acceptance>
</task>

### 1.2 Create config schemas

<task id="1.2" status="pending" depends="" risk="low">
<description>
Create Pydantic v2 schemas for the optimizer config API at `mealie/schema/optimizer/config.py`.

**Pattern to follow**: The schema chain in `mealie/schema/optimizer/pantry.py`. For config, the chain is simpler because config is a singleton (no Create, no pagination):

1. `OptimizerConfigUpdate(MealieModel)` — all weight fields with defaults, used as PUT request body:
   - `overlap_weight: float = 1.0`
   - `pantry_utilization_weight: float = 0.6`
   - `pantry_urgency_weight: float = 0.8`
   - `protein_diversity_weight: float = 0.5`
   - `category_balance_weight: float = 0.3`
   - `rating_weight: float = 0.2`
   - `prep_time_budget_minutes: int | None = None`
   - `perishable_label_keywords: list[str]` — default `["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"]`
   - `shelf_stable_label_keywords: list[str]` — default `["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]`

2. `OptimizerConfigSave(OptimizerConfigUpdate)` — adds `group_id: UUID4` and `household_id: UUID4` for internal creation

3. `OptimizerConfigOut(OptimizerConfigUpdate)` — adds `id: UUID4`, `group_id: UUID4`, `household_id: UUID4`, and `model_config = ConfigDict(from_attributes=True)`

Import `MealieModel` from `mealie.schema._mealie`, `UUID4` from `pydantic`, `ConfigDict` from `pydantic`.
</description>

<subtasks>
- [ ] Create `mealie/schema/optimizer/config.py` with OptimizerConfigUpdate, OptimizerConfigSave, OptimizerConfigOut
</subtasks>

<acceptance>
- All three schema classes are importable
- OptimizerConfigUpdate validates all weight fields with defaults
- OptimizerConfigSave extends Update with tenant IDs
- OptimizerConfigOut has from_attributes=True for ORM mapping
</acceptance>
</task>

### 1.3 Create RepositoryOptimizerConfig

<task id="1.3" status="pending" depends="1.1, 1.2" risk="medium">
<description>
Create the repository for optimizer config at `mealie/repos/optimizer/config.py`.

**Pattern to follow**: `mealie/repos/optimizer/pantry.py` (RepositoryPantryItem).

```python
class RepositoryOptimizerConfig(HouseholdRepositoryGeneric[OptimizerConfigOut, OptimizerConfigModel]):
```

Add a custom method `get_or_create_default(self) -> OptimizerConfigOut`:
1. Query for existing config matching the repo's `household_id` (use `self.session.execute(select(self.model).filter_by(household_id=self.household_id))`)
2. If found, return it mapped to `OptimizerConfigOut`
3. If not found, create a new `OptimizerConfigModel` with default weights, using `OptimizerConfigSave(group_id=self.group_id, household_id=self.household_id)` to build the save data, then use `self.session.add()` + `self.session.commit()` + return as `OptimizerConfigOut`

**Concurrency note**: The UniqueConstraint on household_id prevents duplicates. If two concurrent GET requests race, the second insert will hit the constraint and raise IntegrityError. Catch `sqlalchemy.exc.IntegrityError`, rollback, and re-query.

Also create `mealie/repos/optimizer/__init__.py` if it doesn't exist (it may not — check), or ensure config is importable.
</description>

<subtasks>
- [ ] Create `mealie/repos/optimizer/config.py` with RepositoryOptimizerConfig
- [ ] Implement `get_or_create_default` with IntegrityError handling
- [ ] Ensure `mealie/repos/optimizer/__init__.py` exists (create if needed)
</subtasks>

<acceptance>
- `get_or_create_default()` returns OptimizerConfigOut with all default weights on first call
- Subsequent calls return the same config (idempotent)
- Concurrent creation attempts don't raise unhandled exceptions
</acceptance>
</task>

### 1.4 Register repo in repository_factory.py

<task id="1.4" status="pending" depends="1.3" risk="low">
<description>
Register the new repository in `mealie/repos/repository_factory.py`.

**What to do**:
1. Add imports near the top of the file, adjacent to existing optimizer imports (around line 30 and 41):
   - `from mealie.db.models.optimizer.config import OptimizerConfigModel`
   - `from mealie.repos.optimizer.config import RepositoryOptimizerConfig`
   - `from mealie.schema.optimizer.config import OptimizerConfigOut`

2. Add a `cached_property` in the `AllRepositories` class, under the existing `# Optimizer` section (after the `pantry_items` property, around line 382):
   ```python
   @cached_property
   def optimizer_config(self) -> RepositoryOptimizerConfig:
       return RepositoryOptimizerConfig(
           self.session,
           PK_ID,
           OptimizerConfigModel,
           OptimizerConfigOut,
           group_id=self.group_id,
           household_id=self.household_id,
       )
   ```
</description>

<subtasks>
- [ ] Add 3 imports to repository_factory.py
- [ ] Add `optimizer_config` cached_property under Optimizer section
</subtasks>

<acceptance>
- `self.repos.optimizer_config` is accessible from controllers extending BaseCrudController
- `self.repos.optimizer_config.get_or_create_default()` works end-to-end
</acceptance>
</task>

### 1.5 Create config controller

<task id="1.5" status="pending" depends="1.4" risk="low">
<description>
Create the controller for optimizer config GET/PUT endpoints at `mealie/routes/optimizer/controller_config.py`.

**Pattern to follow**: `mealie/routes/optimizer/controller_pantry.py`, but simpler — only GET and PUT, no CRUD mixins.

```python
router = APIRouter(prefix="/households/optimizer/config", tags=["Optimizer: Config"])

@controller(router)
class OptimizerConfigController(BaseCrudController):

    @router.get("", response_model=OptimizerConfigOut)
    def get_config(self):
        return self.repos.optimizer_config.get_or_create_default()

    @router.put("", response_model=OptimizerConfigOut)
    def update_config(self, data: OptimizerConfigUpdate):
        config = self.repos.optimizer_config.get_or_create_default()
        # Update the existing config using repo's update method
        return self.repos.optimizer_config.update(config.id, data)
```

**Note**: The `update` method is inherited from `HouseholdRepositoryGeneric`. It takes (item_id, data). The `data` can be `OptimizerConfigUpdate` because the repo's generic typing handles the conversion.

Also update `mealie/routes/optimizer/__init__.py` to import and include the config controller router:
```python
from . import controller_pantry, controller_config
router = APIRouter()
router.include_router(controller_pantry.router)
router.include_router(controller_config.router)
```
</description>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_config.py` with GET and PUT endpoints
- [ ] Update `mealie/routes/optimizer/__init__.py` to include controller_config.router
</subtasks>

<acceptance>
- GET /api/households/optimizer/config returns 200 with default weights on first call
- PUT /api/households/optimizer/config with `{"overlap_weight": 2.0}` returns updated config
- Subsequent GET returns the updated value
- Different households get independent configs
</acceptance>
</task>

### 1.6 Create Alembic migration for optimizer_config table

<task id="1.6" status="pending" depends="1.1" risk="medium">
<description>
Create an Alembic migration that creates the `optimizer_config` table.

**Pattern to follow**: `mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py`

**Steps**:
1. Generate the migration: `cd mealie && alembic revision --autogenerate -m "add optimizer config table"`
   - If autogenerate doesn't work, create manually
2. The migration's `down_revision` must be `"a1b2c3d4e5f6"` (the pantry items migration)
3. Verify the upgrade function creates:
   - Table `optimizer_config` with all columns matching OptimizerConfigModel
   - GUID type for id, group_id, household_id (use `mealie.db.migration_types.GUID()`)
   - Float columns for weights with `server_default` values
   - Integer column for prep_time_budget_minutes (nullable)
   - JSON columns for perishable_label_keywords and shelf_stable_label_keywords with `server_default` set to JSON-encoded default lists
   - ForeignKeyConstraints to groups.id and households.id
   - UniqueConstraint on household_id
   - Indexes on group_id and household_id
4. Verify the downgrade function drops the table

**File naming convention**: `YYYY-MM-DD-HH.MM.SS_<revision_id>_<slug>.py` — use the auto-generated timestamp and revision ID.
</description>

<subtasks>
- [ ] Generate or create Alembic migration file
- [ ] Verify upgrade creates optimizer_config table with all columns, constraints, and indexes
- [ ] Verify downgrade drops the table
- [ ] Run `alembic upgrade head` and verify table exists in database
- [ ] Run `alembic downgrade -1` and verify table is removed
</subtasks>

<acceptance>
- Migration chains from a1b2c3d4e5f6 (pantry items)
- `alembic upgrade head` succeeds and optimizer_config table exists
- `alembic downgrade -1` removes the table cleanly
- All weight columns have correct server_default values
</acceptance>

<rollback risk="medium">
Run `alembic downgrade -1` to remove the table. If migration is partially applied, manually drop the optimizer_config table.
</rollback>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `alembic upgrade head` succeeds (optimizer_config table created)
- [ ] GET /api/households/optimizer/config returns 200 with default weights
- [ ] PUT /api/households/optimizer/config updates weights and returns updated values
- [ ] `task py:lint` passes with no errors in new files
- [ ] OptimizerConfigModel importable from mealie.db.models.optimizer
</verification>
<success_criteria>Config API is fully operational with GET-or-create and PUT-update semantics. Migration is reversible.</success_criteria>
</checkpoint>

</phase>

---

## Phase 2: Backend — use_priority + Recipe-Foods Projection

<phase id="2" name="use_priority and Projection Endpoint" depends="1">

### 2.1 Add use_priority column to PantryItemModel

<task id="2.1" status="pending" depends="" risk="low">
<description>
Add a `use_priority` column to the existing `PantryItemModel` at `mealie/db/models/optimizer/pantry.py`.

**What to add** (among the existing column definitions):
```python
from sqlalchemy import CheckConstraint  # add to existing imports if not present

use_priority: Mapped[str] = mapped_column(
    String, nullable=False, default="auto", server_default="auto",
)
```

**Also add** a CheckConstraint to `__table_args__` (it's a tuple — add before the closing parenthesis):
```python
CheckConstraint(
    "use_priority IN ('auto', 'high', 'low')",
    name="pantry_item_use_priority_check",
),
```

The `String` import should already exist. Add `CheckConstraint` to the sqlalchemy import if not present.
</description>

<subtasks>
- [ ] Add `use_priority` column to PantryItemModel
- [ ] Add CheckConstraint to __table_args__
- [ ] Verify imports include CheckConstraint and String
</subtasks>

<acceptance>
- PantryItemModel has use_priority column with default "auto"
- CheckConstraint validates only 'auto', 'high', 'low' values
</acceptance>
</task>

### 2.2 Add use_priority to pantry schemas

<task id="2.2" status="pending" depends="" risk="low">
<description>
Add `use_priority` field to the pantry Pydantic schemas at `mealie/schema/optimizer/pantry.py`.

**What to add** to `PantryItemCreate`:
```python
from typing import Literal  # add to imports

use_priority: Literal["auto", "high", "low"] = "auto"
```

This field will be inherited by `PantryItemSave`, `PantryItemUpdate`, `PantryItemUpdateBulk`, and `PantryItemOut` through the schema chain (they all extend PantryItemCreate directly or indirectly).

Verify the inheritance chain: Create → Save (adds tenant IDs), Create → Update (adds id), Update → UpdateBulk, Create → Out (adds id + relationships). Adding to Create propagates to all.
</description>

<subtasks>
- [ ] Add `Literal` import to pantry schema file
- [ ] Add `use_priority` field to PantryItemCreate class
- [ ] Verify field propagates to Save, Update, UpdateBulk, and Out schemas
</subtasks>

<acceptance>
- `PantryItemCreate(use_priority="high")` validates successfully
- `PantryItemCreate(use_priority="invalid")` raises ValidationError
- `PantryItemOut` includes use_priority in serialized output
</acceptance>
</task>

### 2.3 Create Alembic migration for use_priority column

<task id="2.3" status="pending" depends="1.6, 2.1" risk="medium">
<description>
Create an Alembic migration adding the `use_priority` column to the `pantry_items` table.

**Important**: This migration's `down_revision` must be the revision ID from the Phase 1 migration (task 1.6 — the optimizer_config table migration). This chains the two migrations.

**Steps**:
1. Generate: `cd mealie && alembic revision --autogenerate -m "add pantry use priority"`
2. Verify upgrade function:
   ```python
   op.add_column("pantry_items", sa.Column("use_priority", sa.String(), nullable=False, server_default="auto"))
   op.create_check_constraint("pantry_item_use_priority_check", "pantry_items", "use_priority IN ('auto', 'high', 'low')")
   ```
3. Verify downgrade function:
   ```python
   op.drop_constraint("pantry_item_use_priority_check", "pantry_items", type_="check")
   op.drop_column("pantry_items", "use_priority")
   ```

The `server_default="auto"` ensures existing rows get the default value without requiring a data migration.
</description>

<subtasks>
- [ ] Generate or create migration file chained from Phase 1 migration
- [ ] Verify upgrade adds column with server_default and check constraint
- [ ] Verify downgrade removes constraint and column
- [ ] Run `alembic upgrade head` and verify column exists
</subtasks>

<acceptance>
- Migration chains from the optimizer_config migration
- Existing pantry_items rows get use_priority='auto'
- New inserts with invalid values are rejected by CHECK constraint
- Downgrade removes column and constraint cleanly
</acceptance>

<rollback risk="medium">
Run `alembic downgrade -1` to remove the column. If CHECK constraint removal fails on some databases, manually drop it first.
</rollback>
</task>

### 2.4 Create RecipeFoodProjection schema

<task id="2.4" status="pending" depends="" risk="low">
<description>
Create the lightweight projection schema at `mealie/schema/optimizer/recipe_projection.py`.

This schema is NOT an ORM-mapped model — it's a response-only Pydantic schema constructed manually from query results.

```python
from pydantic import UUID4, ConfigDict
from mealie.schema._mealie import MealieModel

class RecipeFoodProjection(MealieModel):
    recipe_id: UUID4
    slug: str
    name: str
    food_ids: list[UUID4]       # deduplicated food IDs from recipe ingredients
    category_ids: list[UUID4]   # from recipe_category relationship
    tag_ids: list[UUID4]        # from tags relationship
    rating: float | None = None
    total_time: str | None = None       # raw string, e.g. "30 Minutes"
    last_made: str | None = None        # ISO datetime string or None
    model_config = ConfigDict(from_attributes=True)

class RecipeFoodProjectionResponse(MealieModel):
    items: list[RecipeFoodProjection]
    unlinked_recipe_count: int  # count of recipes with 0 food_ids (for UI hint)
```
</description>

<subtasks>
- [ ] Create `mealie/schema/optimizer/recipe_projection.py` with both schema classes
</subtasks>

<acceptance>
- RecipeFoodProjection serializes all fields needed by the scoring engine
- RecipeFoodProjectionResponse wraps items list with unlinked count
- Both classes are importable
</acceptance>
</task>

### 2.5 Create RecipeProjectionService

<task id="2.5" status="pending" depends="2.4" risk="medium">
<description>
Create the service class at `mealie/services/optimizer/recipe_projection.py` that queries recipes and returns lightweight projections.

**Query pattern** (follow `mealie/services/optimizer/recipe_utils.py` for reference):

```python
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.db.models.household.household_to_recipe import HouseholdToRecipe
from mealie.schema.optimizer.recipe_projection import RecipeFoodProjection, RecipeFoodProjectionResponse

class RecipeProjectionService:
    def __init__(self, session: Session, group_id: UUID4, household_id: UUID4) -> None:
        self.session = session
        self.group_id = group_id
        self.household_id = household_id

    def get_all_recipe_food_projections(self) -> RecipeFoodProjectionResponse:
        # Pre-fetch household-scoped last_made timestamps in a single query
        htr_stmt = (
            select(HouseholdToRecipe.recipe_id, HouseholdToRecipe.last_made)
            .where(HouseholdToRecipe.household_id == self.household_id)
        )
        htr_rows = self.session.execute(htr_stmt).all()
        last_made_map: dict[UUID4, datetime | None] = {
            row.recipe_id: row.last_made for row in htr_rows
        }

        stmt = (
            select(RecipeModel)
            .where(RecipeModel.group_id == self.group_id)
            .options(
                selectinload(RecipeModel.recipe_ingredient),
                selectinload(RecipeModel.recipe_category),
                selectinload(RecipeModel.tags),
            )
        )
        recipes = self.session.execute(stmt).scalars().all()

        items = []
        unlinked_count = 0
        for recipe in recipes:
            # Deduplicate food_ids, skip NULL food_ids
            food_ids = list({
                ing.food_id for ing in recipe.recipe_ingredient
                if ing.food_id is not None
            })
            if not food_ids:
                unlinked_count += 1
                continue

            # Use household-scoped last_made from HouseholdToRecipe
            household_last_made = last_made_map.get(recipe.id)

            items.append(RecipeFoodProjection(
                recipe_id=recipe.id,
                slug=recipe.slug,
                name=recipe.name,
                food_ids=food_ids,
                category_ids=[cat.id for cat in recipe.recipe_category],
                tag_ids=[tag.id for tag in recipe.tags],
                rating=recipe.rating,
                total_time=recipe.total_time,
                last_made=household_last_made.isoformat() if household_last_made else None,
            ))

        return RecipeFoodProjectionResponse(items=items, unlinked_recipe_count=unlinked_count)
```

**Key concerns**:
- `food_id` is nullable on RecipeIngredientModel — filter out None values
- Deduplicate food_ids per recipe (same food used twice counts once for scoring overlap)
- `last_made` comes from `HouseholdToRecipe` (per-household), NOT `RecipeModel.last_made` (global denormalized max). The `HouseholdToRecipe` table stores when *this household* last made each recipe. Pre-fetched in a single query into `last_made_map` to avoid N+1.
- Use `selectinload` (not `joinedload`) to avoid Cartesian product with multiple collections
- This query loads all group recipes at once — acceptable for typical household sizes (50-500 recipes). Not paginated.
</description>

<subtasks>
- [ ] Create `mealie/services/optimizer/recipe_projection.py` with RecipeProjectionService
- [ ] Implement get_all_recipe_food_projections with efficient selectinload query
- [ ] Handle nullable food_id, deduplicate food_ids, serialize last_made
</subtasks>

<acceptance>
- Returns all group recipes as lightweight projections
- food_ids are deduplicated per recipe, NULL food_ids excluded
- Recipes with zero food_ids excluded from items, counted in unlinked_recipe_count
- Uses selectinload (not N+1 queries)
- last_made serialized as ISO string or None
</acceptance>
</task>

### 2.6 Create recipe-foods controller + update router

<task id="2.6" status="pending" depends="2.5, 1.5" risk="low">
<description>
Create the controller for the recipe-foods projection endpoint at `mealie/routes/optimizer/controller_recipes.py`.

```python
from fastapi import APIRouter
from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.schema.optimizer.recipe_projection import RecipeFoodProjectionResponse
from mealie.services.optimizer.recipe_projection import RecipeProjectionService

router = APIRouter(prefix="/households/optimizer", tags=["Optimizer: Recipes"])

@controller(router)
class OptimizerRecipeController(BaseCrudController):
    @router.get("/recipe-foods", response_model=RecipeFoodProjectionResponse)
    def get_recipe_foods(self):
        service = RecipeProjectionService(self.session, self.group_id, self.household_id)
        return service.get_all_recipe_food_projections()
```

**Also update** `mealie/routes/optimizer/__init__.py` to include this controller:
```python
from . import controller_pantry, controller_config, controller_recipes

router = APIRouter()
router.include_router(controller_pantry.router)
router.include_router(controller_config.router)
router.include_router(controller_recipes.router)
```

Note: The router __init__ should already have controller_config from task 1.5. This task adds controller_recipes.
</description>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_recipes.py`
- [ ] Update `mealie/routes/optimizer/__init__.py` to include controller_recipes
</subtasks>

<acceptance>
- GET /api/households/optimizer/recipe-foods returns RecipeFoodProjectionResponse
- Response is significantly smaller than full recipe list
- All three optimizer controllers (pantry, config, recipes) are registered
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `alembic upgrade head` succeeds (both new migrations applied)
- [ ] Pantry CRUD round-trips use_priority field (create with "high", read back "high")
- [ ] GET /api/households/optimizer/recipe-foods returns projection data
- [ ] Projection excludes recipes with zero food_ids
- [ ] Projection returns household-scoped last_made (not global RecipeModel.last_made)
- [ ] `task py:lint` passes
</verification>
<success_criteria>All backend endpoints operational. Pantry items support use_priority. Projection endpoint returns lightweight recipe data with household-scoped last_made, suitable for client-side scoring.</success_criteria>
</checkpoint>

</phase>

---

## Phase 3: Frontend — TypeScript Scoring Engine

<phase id="3" name="Scoring Engine" depends="">

Note: Phase 3 has no backend dependencies — it can be developed in parallel with Phases 1-2. It only depends on type definitions.

### 3.1 Create scoring engine types

<task id="3.1" status="pending" depends="" risk="low">
<description>
Create TypeScript interfaces for the scoring engine at `frontend/app/composables/optimizer/types.ts`.

Create the directory `frontend/app/composables/optimizer/` if it doesn't exist.

**Interfaces to define**:

```typescript
export interface ScoringWeights {
  overlap: number;
  pantryCoverage: number;
  pantryUrgency: number;
  proteinDiversity: number;
  categoryBalance: number;
  rating: number;
  prepTime: number;
  perishableLabelKeywords: string[];
  shelfStableLabelKeywords: string[];
}

export interface RecipeFoodData {
  recipeId: string;
  slug: string;
  name: string;
  foodIds: string[];
  categoryIds: string[];
  tagIds: string[];
  rating: number | null;
  totalTime: string | null;
  lastMade: string | null;
}

export interface PantryMatchDetail {
  foodName: string;
  priority: "high" | "low";
  daysToExpiry: number | null;
}

export interface ScoredRecipe {
  recipeId: string;
  totalScore: number;
  breakdown: Record<string, number>;
  pantryMatches: PantryMatchDetail[];
}

export interface PantryItemScoring {
  foodId: string;
  foodName: string;
  labelName: string | null;
  usePriority: "auto" | "high" | "low";
  assumeEnough: boolean;
  expirationDate: string | null;  // ISO date string
}
```

These types have ZERO Vue/Nuxt dependencies — they are plain TypeScript interfaces.
</description>

<subtasks>
- [ ] Create directory `frontend/app/composables/optimizer/` if needed
- [ ] Create `frontend/app/composables/optimizer/types.ts` with all 5 interfaces
</subtasks>

<acceptance>
- All interfaces are exportable and importable
- ScoringWeights maps 1:1 to OptimizerConfigOut weight fields (camelCase)
- RecipeFoodData maps 1:1 to RecipeFoodProjection (camelCase)
- No Vue/Nuxt imports
</acceptance>
</task>

### 3.2 Implement scoring engine

<task id="3.2" status="pending" depends="3.1" risk="high">
<description>
Implement the pure scoring functions at `frontend/app/composables/optimizer/scoring-engine.ts`.

**Critical**: This file must have ZERO Vue/Nuxt/browser dependencies. Only import from `./types`.

**Functions to implement** (all are pure — no side effects):

1. **`parseTimeToMinutes(totalTime: string | null): number | null`**
   - Parse free-form time strings like "30 Minutes", "1 Hour 15 Minutes", "1.5 Hours"
   - Return minutes as number, or null if unparseable
   - Handle: "X Minutes", "X Hours", "X Hours Y Minutes", "X Hour Y Minutes"
   - Case-insensitive matching

2. **`overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number`**
   - Return fraction of candidate's foods that appear in the planned set
   - If candidate has no foods, return 0
   - Range: [0.0, 1.0]

3. **`pantryCoverageScore(candidateFoodIds: string[], pantryFoodIds: Set<string>): number`**
   - Return fraction of candidate's foods present in pantry
   - Exclude staple/assume_enough items (caller should pre-filter pantryFoodIds)
   - Range: [0.0, 1.0]

4. **`pantryUrgencyScore(candidateFoodIds: string[], pantryMap: Map<string, PantryItemScoring>): { score: number; matches: PantryMatchDetail[] }`**
   - For each candidate food in pantry: resolve effective priority, calculate expiration multiplier
   - Score = sum of (priority_weight x expiration_multiplier) / candidateFoodIds.length
   - priority_weight: high=1.0, low=0.3
   - Return matches for UI annotation
   - Skip items with assumeEnough=true

5. **`proteinDiversityScore(candidateTagIds: string[], plannedProteinTags: Map<string, number>): number`**
   - Penalize if candidate shares tags with frequently-planned entries
   - 1.0 if no overlap, decreasing with more overlap
   - If no tags, return 0.5 (neutral)

6. **`categoryBalanceScore(candidateCategoryIds: string[], plannedCategoryCounts: Map<string, number>): number`**
   - Bonus for underrepresented categories
   - 1.0 if category not yet planned, decreasing with count
   - If no categories, return 0.5 (neutral)

7. **`normalizedRating(rating: number | null): number`**
   - Return rating / 5.0, or 0.5 if null (neutral default)
   - Clamp to [0.0, 1.0]

8. **`prepTimeScore(totalTime: string | null, budgetMinutes: number | null): number`**
   - Parse totalTime using parseTimeToMinutes
   - If no budget, return 1.0
   - If parsed minutes <= budget, return 1.0
   - If exceeds budget, return 0.0 (hard filter)
   - If unparseable, return 1.0 (don't penalize missing data)

9. **`resolveEffectivePriority(item: PantryItemScoring, perishableKeywords: string[], shelfStableKeywords: string[]): "high" | "low"`**
   - If usePriority !== "auto", return it directly
   - Auto-resolution rules:
     - If expirationDate is set and <= 5 days away -> "high"
     - If labelName matches any perishableKeywords (case-insensitive substring) -> "high"
     - If labelName matches any shelfStableKeywords (case-insensitive substring) -> "low"
     - Otherwise -> "high" (safe default)
   - The keyword lists come from `ScoringWeights.perishableLabelKeywords` / `shelfStableLabelKeywords`, which are stored in the per-household OptimizerConfig and configurable by the user via the config API. Defaults: perishable=["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"], shelf-stable=["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]

10. **`expirationMultiplier(daysToExpiry: number | null): number`**
    - null (no expiration) -> 1.0
    - 7+ days -> 1.0
    - 3-6 days -> 1.5
    - 1-2 days -> 2.0
    - 0 or negative (expired) -> 2.5

11. **`scoreRecipes(candidates, plannedRecipes, pantryItems, weights, prepTimeBudget): ScoredRecipe[]`**
    - Build derived data structures (plannedFoodIds set, pantryMap, etc.)
    - Filter out assume_enough pantry items from coverage/urgency
    - Pass `weights.perishableLabelKeywords` and `weights.shelfStableLabelKeywords` through to `resolveEffectivePriority` calls
    - Score each candidate across all factors
    - totalScore = weighted sum of all factor scores
    - Sort descending by totalScore
    - Exclude candidates with zero foodIds
    - Exclude candidates where prepTimeScore = 0.0
</description>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/scoring-engine.ts`
- [ ] Implement parseTimeToMinutes with robust string parsing
- [ ] Implement all 8 individual scoring functions
- [ ] Implement resolveEffectivePriority with label heuristics
- [ ] Implement expirationMultiplier
- [ ] Implement scoreRecipes orchestrator function
- [ ] Verify zero Vue/Nuxt imports
</subtasks>

<acceptance>
- All functions are pure (no side effects, no imports beyond ./types)
- scoreRecipes returns ScoredRecipe[] sorted by totalScore descending
- Recipes exceeding prepTimeBudget are filtered out
- Zero-food recipes are excluded
- Cold start (zero planned recipes): overlap=0, rank by pantry+rating
- assume_enough pantry items excluded from coverage/urgency
- Auto-priority resolution follows documented rules
- parseTimeToMinutes handles common formats: "30 Minutes", "1 Hour", "1 Hour 15 Minutes"
</acceptance>
</task>

### 3.3 Create Vue composable wrapper

<task id="3.3" status="pending" depends="3.2" risk="low">
<description>
Create a thin Vue composable at `frontend/app/composables/optimizer/use-optimizer-scoring.ts` that wraps the pure scoring functions with reactive state.

```typescript
import { computed, ref, type ComputedRef } from "vue";
import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring } from "./types";
import { scoreRecipes } from "./scoring-engine";

export function useOptimizerScoring() {
  const candidates = ref<RecipeFoodData[]>([]);
  const plannedRecipes = ref<RecipeFoodData[]>([]);
  const pantryItems = ref<PantryItemScoring[]>([]);
  const weights = ref<ScoringWeights>({
    overlap: 1.0,
    pantryCoverage: 0.6,
    pantryUrgency: 0.8,
    proteinDiversity: 0.5,
    categoryBalance: 0.3,
    rating: 0.2,
    prepTime: 1.0,
    perishableLabelKeywords: ["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"],
    shelfStableLabelKeywords: ["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"],
  });
  const prepTimeBudget = ref<number | null>(null);

  const scoredRecipes: ComputedRef<ScoredRecipe[]> = computed(() =>
    scoreRecipes(
      candidates.value,
      plannedRecipes.value,
      pantryItems.value,
      weights.value,
      prepTimeBudget.value,
    )
  );

  return {
    scoredRecipes,
    setCandidates: (data: RecipeFoodData[]) => { candidates.value = data; },
    setPlannedRecipes: (data: RecipeFoodData[]) => { plannedRecipes.value = data; },
    setPantryItems: (items: PantryItemScoring[]) => { pantryItems.value = items; },
    setWeights: (w: ScoringWeights) => { weights.value = w; },
    setPrepTimeBudget: (minutes: number | null) => { prepTimeBudget.value = minutes; },
  };
}
```

This composable owns no data-fetching logic — callers provide data via setters.
</description>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/use-optimizer-scoring.ts`
- [ ] Verify scoredRecipes recomputes reactively when inputs change
</subtasks>

<acceptance>
- scoredRecipes is a ComputedRef that recomputes when any input ref changes
- Composable delegates all logic to scoring-engine.ts pure functions
- No direct API calls — data is provided by callers
</acceptance>
</task>

### 3.4 Write scoring engine unit tests

<task id="3.4" status="pending" depends="3.2" risk="low">
<description>
Create comprehensive unit tests at `frontend/app/composables/optimizer/scoring-engine.test.ts` using Vitest.

**Test structure** — at least 2 test cases per function plus integration edge cases:

```typescript
import { describe, it, expect } from "vitest";
import { overlapScore, pantryCoverageScore, ... } from "./scoring-engine";
```

**Required test cases**:

1. `parseTimeToMinutes`: "30 Minutes"->30, "1 Hour"->60, "1 Hour 15 Minutes"->75, null->null, "garbage"->null
2. `overlapScore`: no overlap->0, full overlap->1.0, partial->fraction, empty candidate->0
3. `pantryCoverageScore`: all in pantry->1.0, none in pantry->0, partial->fraction
4. `pantryUrgencyScore`: high-priority expiring item->high score, low-priority->lower score, assume_enough skipped
5. `proteinDiversityScore`: unique tags->1.0, all duplicated->low score, no tags->0.5
6. `categoryBalanceScore`: new category->1.0, overrepresented->lower, no categories->0.5
7. `normalizedRating`: 5->1.0, null->0.5, 0->0.0, 3->0.6
8. `prepTimeScore`: within budget->1.0, exceeds->0.0, no budget->1.0, unparseable->1.0
9. `resolveEffectivePriority`: explicit "high"->"high", "auto" expiring soon->"high", "auto" shelf-stable label->"low", "auto" unknown->"high", custom keyword list matches correctly
10. `expirationMultiplier`: null->1.0, 10->1.0, 5->1.5, 2->2.0, 0->2.5, -1->2.5
11. `scoreRecipes` integration:
    - Zero-food recipes excluded
    - Cold start (zero planned) — overlap=0, ranked by pantry+rating
    - 100% overlap produces high overlap score
    - All assume_enough pantry -> coverage=0, urgency=0
    - Prep time exceeding budget -> recipe filtered out
</description>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/scoring-engine.test.ts`
- [ ] Write test cases for all 11 function groups
- [ ] Run tests with `npx vitest run frontend/app/composables/optimizer/scoring-engine.test.ts`
- [ ] All tests pass
</subtasks>

<acceptance>
- All scoring functions have at least 2 test cases each
- Edge cases from spec are covered
- Tests pass with `npx vitest run` (or `task ui:test`)
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] All vitest tests pass for scoring engine
- [ ] scoring-engine.ts has zero Vue/Nuxt imports (verify with grep)
- [ ] use-optimizer-scoring.ts imports only from vue and local files
- [ ] `task ui:lint` passes on new files
</verification>
<success_criteria>Scoring engine is complete with full test coverage. Composable provides reactive wrapper. No framework dependencies in core logic.</success_criteria>
</checkpoint>

</phase>

---

## Phase 4: Frontend — API Clients, Types, i18n

<phase id="4" name="Frontend Integration" depends="1, 2">

### 4.1 Add config and projection types to optimizer.ts

<task id="4.1" status="pending" depends="" risk="low">
<description>
Add new TypeScript interfaces to the existing file `frontend/app/lib/api/types/optimizer.ts`.

**Append after the existing PantryDeductRequest interface** (after line 82):

```typescript
export interface OptimizerConfigUpdate {
  overlapWeight?: number;
  pantryUtilizationWeight?: number;
  pantryUrgencyWeight?: number;
  proteinDiversityWeight?: number;
  categoryBalanceWeight?: number;
  ratingWeight?: number;
  prepTimeBudgetMinutes?: number | null;
  perishableLabelKeywords?: string[];
  shelfStableLabelKeywords?: string[];
}

export interface OptimizerConfigOut extends OptimizerConfigUpdate {
  id: string;
  groupId: string;
  householdId: string;
}

export interface RecipeFoodProjection {
  recipeId: string;
  slug: string;
  name: string;
  foodIds: string[];
  categoryIds: string[];
  tagIds: string[];
  rating: number | null;
  totalTime: string | null;
  lastMade: string | null;
}

export interface RecipeFoodProjectionResponse {
  items: RecipeFoodProjection[];
  unlinkedRecipeCount: number;
}
```
</description>

<subtasks>
- [ ] Add OptimizerConfigUpdate and OptimizerConfigOut interfaces
- [ ] Add RecipeFoodProjection and RecipeFoodProjectionResponse interfaces
</subtasks>

<acceptance>
- All 4 new interfaces are exportable from the file
- TypeScript compiles without errors
</acceptance>
</task>

### 4.2 Add usePriority to PantryItem types

<task id="4.2" status="pending" depends="" risk="low">
<description>
Add `usePriority` field to the existing PantryItem interfaces in `frontend/app/lib/api/types/optimizer.ts`.

**Modify PantryItemCreate** (around line 10) to add:
```typescript
usePriority?: "auto" | "high" | "low";
```

This will be inherited by PantryItemUpdate and PantryItemOut through the `extends` chain.
</description>

<subtasks>
- [ ] Add `usePriority` field to PantryItemCreate interface
- [ ] Verify PantryItemUpdate and PantryItemOut inherit it
</subtasks>

<acceptance>
- PantryItemCreate, PantryItemUpdate, and PantryItemOut all include usePriority
- Type is correctly narrowed to the 3 valid string literals
</acceptance>
</task>

### 4.3 Add API clients for config and recipe-foods

<task id="4.3" status="pending" depends="4.1" risk="low">
<description>
Extend the existing file `frontend/app/lib/api/user/optimizer-pantry.ts` to add config and recipe-foods API clients.

**Step 1**: Add new imports at the top:
```typescript
import { BaseAPI } from "../base/base-clients";  // add BaseAPI import
import type {
  // ... existing imports ...
  OptimizerConfigOut,
  OptimizerConfigUpdate,
  RecipeFoodProjectionResponse,
} from "~/lib/api/types/optimizer";
```

**Step 2**: Add routes to the existing `routes` const:
```typescript
const routes = {
  // ... existing routes ...
  config: `${prefix}/households/optimizer/config`,
  recipeFoods: `${prefix}/households/optimizer/recipe-foods`,
};
```

**Step 3**: Add the OptimizerConfigApi class after PantryItemsApi:
```typescript
export class OptimizerConfigApi extends BaseAPI {
  async getConfig() {
    return await this.requests.get<OptimizerConfigOut>(routes.config);
  }

  async updateConfig(data: OptimizerConfigUpdate) {
    return await this.requests.put<OptimizerConfigOut>(routes.config, data);
  }
}
```

**Step 4**: Extend the OptimizerApi class:
```typescript
export class OptimizerApi {
  public pantry: PantryItemsApi;
  public config: OptimizerConfigApi;
  private requests: ApiRequestInstance;

  constructor(requests: ApiRequestInstance) {
    this.requests = requests;
    this.pantry = new PantryItemsApi(requests);
    this.config = new OptimizerConfigApi(requests);
  }

  async getRecipeFoods() {
    return await this.requests.get<RecipeFoodProjectionResponse>(routes.recipeFoods);
  }
}
```

Note: `getRecipeFoods` is on the OptimizerApi class directly (not a sub-client) because it's a single endpoint, not a CRUD resource. The `requests` instance needs to be stored as a private field.
</description>

<subtasks>
- [ ] Add BaseAPI import and new type imports
- [ ] Add config and recipeFoods routes
- [ ] Create OptimizerConfigApi class extending BaseAPI
- [ ] Extend OptimizerApi with config sub-client and getRecipeFoods method
- [ ] Store requests instance in OptimizerApi for getRecipeFoods
</subtasks>

<acceptance>
- `api.optimizer.config.getConfig()` calls GET /api/households/optimizer/config
- `api.optimizer.config.updateConfig(data)` calls PUT /api/households/optimizer/config
- `api.optimizer.getRecipeFoods()` calls GET /api/households/optimizer/recipe-foods
- TypeScript compiles without errors
</acceptance>
</task>

### 4.4 Add i18n keys

<task id="4.4" status="pending" depends="" risk="low">
<description>
Add i18n keys to `frontend/app/lang/messages/en-US.json` under the existing `"optimizer"` namespace.

The optimizer section starts at line 1484. Currently it has only the `"pantry"` sub-namespace (lines 1485-1500).

**Add** 4 new keys to the existing `"pantry"` block (before the closing `}` at line 1500):
```json
"use-priority": "Priority",
"priority-auto": "Auto",
"priority-high": "Use up",
"priority-low": "Low priority"
```

**Add** a new `"config"` sub-namespace after `"pantry"` (before the closing `}` of `"optimizer"` at line 1501):
```json
"config": {
  "title": "Optimizer Settings",
  "overlap-weight": "Ingredient Overlap",
  "pantry-utilization-weight": "Pantry Utilization",
  "pantry-urgency-weight": "Pantry Urgency",
  "protein-diversity-weight": "Protein Diversity",
  "category-balance-weight": "Category Balance",
  "rating-weight": "Recipe Rating",
  "prep-time-budget": "Prep Time Budget (minutes)",
  "perishable-label-keywords": "Perishable Label Keywords",
  "shelf-stable-label-keywords": "Shelf-Stable Label Keywords"
}
```
</description>

<subtasks>
- [ ] Add use-priority, priority-auto, priority-high, priority-low keys to optimizer.pantry
- [ ] Add optimizer.config namespace with all 8 keys
</subtasks>

<acceptance>
- All new i18n keys resolve in English
- Existing pantry keys are preserved
- JSON is valid (no trailing commas, proper nesting)
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] TypeScript compiles without errors (`task ui:lint` or `npx tsc --noEmit`)
- [ ] All new interfaces are exported from optimizer.ts
- [ ] PantryItemCreate includes usePriority field
- [ ] OptimizerApi has config sub-client and getRecipeFoods method
- [ ] i18n JSON is valid and all keys resolve
</verification>
<success_criteria>Frontend API clients match all backend endpoints. Types are complete. i18n keys are ready for Stage B UI work.</success_criteria>
</checkpoint>

</phase>

---

## Final Validation

<final_validation>
<verification>
- [ ] `alembic upgrade head` applies both new migrations cleanly
- [ ] `alembic downgrade` to pre-optimizer-config state works cleanly
- [ ] GET /api/households/optimizer/config returns default config
- [ ] PUT /api/households/optimizer/config updates and returns config
- [ ] POST /api/households/optimizer/pantry with use_priority="high" round-trips correctly
- [ ] GET /api/households/optimizer/recipe-foods returns projection data
- [ ] `task py:lint` passes
- [ ] `task py:test` passes (no regressions)
- [ ] `task ui:lint` passes
- [ ] Vitest scoring engine tests pass
- [ ] No regressions in existing pantry CRUD endpoints
</verification>
<acceptance>
Stage A is complete when: (1) Config API stores and returns per-household scoring weights, (2) pantry items support use_priority with validation, (3) recipe-foods projection endpoint returns lightweight recipe data, (4) pure TypeScript scoring engine scores recipes with full test coverage, (5) frontend API clients can call all new endpoints, (6) all existing functionality is preserved.
</acceptance>
</final_validation>

---

## Dependency Verification Log

<dependency_log>
<dependency name="SQLAlchemy" verified="true">
  <version>2.0.49</version>
  <verified_via>CLAUDE.md tech stack</verified_via>
  <notes>Mapped[], mapped_column, UniqueConstraint, CheckConstraint, Float, String, Integer all available in 2.0.x</notes>
</dependency>
<dependency name="Pydantic" verified="true">
  <version>2.12.5</version>
  <verified_via>CLAUDE.md tech stack</verified_via>
  <notes>MealieModel base class, ConfigDict, UUID4, Literal all available</notes>
</dependency>
<dependency name="FastAPI" verified="true">
  <version>0.135.3</version>
  <verified_via>CLAUDE.md tech stack</verified_via>
  <notes>APIRouter, response_model parameter available</notes>
</dependency>
<dependency name="Alembic" verified="true">
  <version>1.18.4</version>
  <verified_via>CLAUDE.md tech stack</verified_via>
  <notes>op.create_table, op.add_column, op.create_check_constraint available</notes>
</dependency>
<dependency name="mealie.db.migration_types.GUID" verified="true">
  <version>N/A (project internal)</version>
  <verified_via>Used in existing pantry migration a1b2c3d4e5f6</verified_via>
  <notes>Custom UUID type for Alembic migrations</notes>
</dependency>
<dependency name="HouseholdRepositoryGeneric" verified="true">
  <version>N/A (project internal)</version>
  <verified_via>Used by RepositoryPantryItem in mealie/repos/optimizer/pantry.py</verified_via>
  <notes>Provides CRUD operations with tenant isolation. Generic params: [SchemaOut, Model]</notes>
</dependency>
<dependency name="BaseCrudController" verified="true">
  <version>N/A (project internal)</version>
  <verified_via>Used by OptimizerPantryController in mealie/routes/optimizer/controller_pantry.py</verified_via>
  <notes>Provides user, group_id, household_id, repos, session properties</notes>
</dependency>
<dependency name="BaseAPI (frontend)" verified="true">
  <version>N/A (project internal)</version>
  <verified_via>Defined in frontend/app/lib/api/base/base-clients.ts line 16</verified_via>
  <notes>Abstract class with requests: ApiRequestInstance. For non-CRUD API clients.</notes>
</dependency>
<dependency name="Vitest" verified="true">
  <version>Unknown (installed in frontend)</version>
  <verified_via>Referenced in spec, standard Nuxt testing tool</verified_via>
  <notes>describe, it, expect API for unit tests</notes>
</dependency>
<dependency name="@auto_init decorator" verified="true">
  <version>N/A (project internal)</version>
  <verified_via>Used in PantryItemModel</verified_via>
  <notes>Auto-generates __init__ from mapped columns</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false">
  <question>Should the projection endpoint support pagination for very large recipe collections (1000+ recipes)?</question>
  <impact>Memory and response time for large groups. Typical household: 50-500 recipes.</impact>
  <default_assumption>No pagination for Stage A. The projection is lightweight (~200 bytes per recipe). For 500 recipes, response is ~100KB — well within acceptable limits. Re-evaluate if real-world usage shows issues.</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-13-190951-optimizer-foundation.md">
  <question>Should GET /households/optimizer/config create a default row (write-on-read), or should the frontend handle missing config by using client-side defaults?</question>
  <impact>Affects API semantics and frontend complexity.</impact>
  <default_assumption>GET creates default row (upsert-on-read). Simpler frontend code. The IntegrityError catch in get_or_create_default handles concurrent races. Codex noted this is atypical but acceptable for single-row config.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-13-190951-optimizer-foundation.md">
<resolved original_question="Should food_ids in the projection be deduplicated per recipe?">
  <resolution>Yes — deduplicate. The scoring engine measures ingredient overlap by food identity, not by ingredient instance count. A recipe using "chicken" twice still only contributes one food overlap match. The spec explicitly states "food_ids are deduplicated per recipe (same food used twice counts once)." Codex suggested preserving multiplicity, but the scoring model doesn't use counts — it uses set intersection. Deduplication is correct for this use case.</resolution>
</resolved>
<resolved original_question="Should the scoring engine normalize total_time on the backend?">
  <resolution>No — keep parsing client-side in Stage A. Adding a normalized column requires another migration and model change. The parseTimeToMinutes function handles common formats and gracefully returns null for unparseable values (which get score 1.0 = not penalized). Server-side normalization is a future optimization if the heuristic proves insufficient.</resolution>
</resolved>
<resolved original_question="How should the scoring engine classify food labels as perishable vs. shelf-stable for auto-priority resolution?">
  <resolution>Resolved during planning: use configurable keyword lists stored as JSON columns on OptimizerConfigModel (`perishable_label_keywords`, `shelf_stable_label_keywords`). Shipped with sensible defaults. Users can customize via config PUT endpoint. The scoring engine receives keywords from the config payload — no hardcoded lists in TypeScript. Codex confirmed this fits the existing "config stores all scoring knobs" pattern. Label IDs could replace keyword strings in a future iteration if localization becomes a concern.</resolution>
</resolved>
<resolved original_question="Should RecipeFoodProjection include household-scoped last_made or the global RecipeModel.last_made?">
  <resolution>Resolved during planning: use household-scoped last_made from the existing `HouseholdToRecipe` join table. The codebase already tracks per-household `last_made` — `RecipeModel.last_made` is just a denormalized max across all households. The projection service pre-fetches `HouseholdToRecipe.last_made` for the requesting household in a single query, keyed by recipe_id, avoiding N+1. The controller passes `self.household_id` to the service. Codex confirmed option C (direct household_id pass) as cleanest.</resolution>
</resolved>
</resolved_from_source>

---

## Plan Review Notes

<review_notes>
<codex_response>
**Findings**
- **High**: "GET creates default" is a write on read and can violate REST expectations, caching, and observability; it also complicates audits and retries. Recommendation: "Use GET to read only; create defaults in a migration or on first PUT, and keep GET idempotent."
- **High**: Recipe projection "single query with joined loads" risks N+1 expansion and memory blowups if many recipes/ingredients; also "deduplicated food_ids" can lose cardinality needed for scoring. Recommendation: "Use a projection query returning a flattened, bounded dataset and explicitly preserve per-ingredient counts."
- **Medium**: Two chained Alembic migrations across phases can break if backfilled data or app code runs between; especially for "use_priority" schema updates. Recommendation: "Combine related schema+data changes into one migration per deployable unit, and include server defaults for new non-null columns."
- **Medium**: "Label names for auto-priority are user-defined" implies heuristic classification; this can be unstable across locales and user customizations. Recommendation: "Store explicit use_priority on pantry items and avoid label-name heuristics in scoring."
- **Medium**: "total_time is a free-form string" makes scoring nondeterministic; parsing on client is fragile. Recommendation: "Normalize total_time on the backend (e.g., total_time_minutes) and expose it in the projection."

**Atomicity / hidden complexity**
- Task 1.3 (repo get_or_create_default) hides transactional concurrency handling.
- Task 2.5 (projection service) hides query tuning, pagination, and data-shape decisions.
- Task 3.2 (scoring functions) hides parsing and normalization of total_time and label heuristics.
</codex_response>

<changes_made>
**Round 1 (initial Codex review):**

1. **GET-creates-default concern (High)**: Acknowledged but retained per spec decision. The spec explicitly chose upsert-on-read for single-row config simplicity. Added IntegrityError handling to task 1.3 for concurrency safety. This is a pragmatic trade-off — the write is idempotent in effect, even if not in HTTP semantics.

2. **Projection query concern (High)**: Changed from `joinedload` to `selectinload` in task 2.5 to avoid Cartesian product with multiple collections (recipe_ingredient, recipe_category, tags). This prevents the N+1 expansion Codex warned about. Retained deduplication because the scoring model uses set intersection, not counts.

3. **Two chained migrations (Medium)**: Retained separate migrations per spec decision (independent rollback). Both use `server_default` so no data backfill is needed. They deploy together in practice.

4. **Label heuristics (Medium)**: Retained as documented fallback. The `use_priority` field exists for explicit overrides. Auto-resolution is a convenience, not the primary mechanism. Added case-insensitive substring matching for resilience.

5. **total_time parsing (Medium)**: Added `parseTimeToMinutes` as a dedicated utility function in task 3.2 (not in original spec). Unparseable values return null -> score 1.0 (don't penalize missing data). Server-side normalization deferred to future work.

6. **Hidden complexity (Atomicity)**: Expanded task 1.3 with explicit IntegrityError handling instructions. Expanded task 2.5 with full query implementation. Expanded task 3.2 into 7 subtasks with all function signatures.

**Round 2 (plan revision — Q1 and Q3 resolution):**

7. **Label heuristics → configurable (Q1)**: Replaced hardcoded perishable/shelf-stable keyword lists with JSON columns on OptimizerConfigModel (`perishable_label_keywords`, `shelf_stable_label_keywords`). Codex confirmed this fits the "config stores all scoring knobs" pattern. Added to: model (1.1), schema (1.2), migration (1.6), scoring types (3.1), scoring engine (3.2), composable defaults (3.3), frontend types (4.1). The scoring engine's `resolveEffectivePriority` now takes keyword lists as parameters instead of using hardcoded arrays.

8. **Household-scoped last_made (Q3)**: Switched from global `RecipeModel.last_made` to per-household `HouseholdToRecipe.last_made`. The codebase already has the `HouseholdToRecipe` join table with per-household timestamps. Codex confirmed option C (pass `household_id` directly to service). Implementation: `RecipeProjectionService.__init__` now takes `household_id`, pre-fetches all `HouseholdToRecipe.last_made` in one query into a lookup dict, uses that instead of `recipe.last_made`. Controller passes `self.household_id`. No extra migration needed — `HouseholdToRecipe` already exists.
</changes_made>
</review_notes>
