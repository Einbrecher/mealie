# Implementation Plan: Optimizer Foundation (Stage A)

Source: docs/plans/2026-04-13-232845-optimizer-foundation.md
Revised: 2026-04-13

<plan_metadata>
  <feature>Optimizer Foundation — Config API, use_priority, recipe-foods projection, scoring engine</feature>
  <source>docs/plans/2026-04-13-232845-optimizer-foundation.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>4</phases>
  <tasks>22</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Build the backend and frontend foundation for the meal plan optimizer: a per-household config API storing scoring weights, a `use_priority` field on pantry items, a lightweight recipe-foods projection endpoint for the scoring engine, and a pure TypeScript scoring engine with Vue composable wrapper. This is Stage A — no UI beyond API clients; the optimizer page and shopping list enhancements come in later stages.

## Changes from Original

<revision_summary>
<change type="dependency">
  Fixed hidden dependencies: 1.2 now depends on 1.1 (schemas reference model fields), 2.2 depends on 2.1, 1.6 depends on both 1.1 and 1.2. Prevents schema drift.
</change>
<change type="structural">
  Split task 3.2 (11 scoring functions, high risk) into three tasks: 3.2 (parsing/resolution helpers — 4 functions), 3.3 (individual scoring functions — 6 functions), 3.4 (scoreRecipes orchestrator). Composable moved to 3.5, tests to 3.6. Reduces blast radius per Codex recommendation.
</change>
<change type="clarity">
  Fixed get_or_create_default implementation: use `self.create()` (inherited from HouseholdRepositoryGeneric) instead of manual session.add()/commit(). Manual approach skips session.refresh() and may return objects without auto-generated fields.
</change>
<change type="clarity">
  Fixed JSON column server_default: must be the full keyword list (JSON-encoded), not "[]". Otherwise database-level inserts get empty keyword lists while Python-level inserts get the full defaults.
</change>
<change type="clarity">
  Documented that PUT /config is full-replacement semantics. Frontend must always send the complete config object. TypeScript OptimizerConfigOut fields are required (not optional) to enforce this.
</change>
<change type="clarity">
  Clarified prepTime weight: prepTimeScore is a hard filter (0.0 = excluded, 1.0 = passes). Since all surviving candidates score 1.0, including prepTime in the weighted sum adds a constant that doesn't affect ranking. The orchestrator excludes it from the weighted sum and treats it as a pre-filter only.
</change>
<change type="clarity">
  Addressed type duplication between RecipeFoodData (scoring composable) and RecipeFoodProjection (API types). Added mapping guidance in task 3.5.
</change>
<change type="clarity">
  Made acceptance criteria testable with specific commands. Replaced "significantly smaller" with measurable threshold. Replaced "concurrent creation" with specific test approach.
</change>
<change type="clarity">
  Fixed task count metadata: original said 16, actual count was 20. Revised plan has 22 (after 3.2 split).
</change>
<change type="clarity">
  Added missing `from datetime import datetime` import to task 2.5.
</change>
</revision_summary>

## Prerequisites

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
  <verification>Run `cd frontend && npx vitest --version`</verification>
</prereq>
</prerequisites>

---

## Phase 1: Backend — Optimizer Config

<phase id="1" name="Optimizer Config API">

### 1.1 Create OptimizerConfigModel

<task id="1.1" status="pending" depends="" risk="low">
<context>
Create the SQLAlchemy model for per-household optimizer scoring weights at `mealie/db/models/optimizer/config.py`.

**Pattern to follow**: Copy the structure of `mealie/db/models/optimizer/pantry.py` (PantryItemModel). The new model has:
- Table name: `optimizer_config`
- PK: `id` (GUID, default=GUID.generate)
- Tenant FKs: `group_id` (FK to groups.id, not null, indexed), `household_id` (FK to households.id, not null, indexed)
- Weight columns (all `Float`, not null, with `server_default`):
  - `overlap_weight` (default 1.0)
  - `pantry_utilization_weight` (default 0.6)
  - `pantry_urgency_weight` (default 0.8)
  - `protein_diversity_weight` (default 0.5)
  - `category_balance_weight` (default 0.3)
  - `rating_weight` (default 0.2)
- Optional column: `prep_time_budget_minutes` (Integer, nullable, no default)
- JSON columns for configurable label classification:
  - `perishable_label_keywords: Mapped[list[str]]` — JSON list of case-insensitive substrings that identify perishable food labels.
    Default: `["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"]`
  - `shelf_stable_label_keywords: Mapped[list[str]]` — JSON list of case-insensitive substrings for shelf-stable labels.
    Default: `["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]`
  - Use `mapped_column(JSON, nullable=False)` with a Python-side `default` factory returning the list.
  - **Important**: Set `server_default` to the JSON-encoded full default list string (e.g., `server_default='["vegetable","fruit","dairy","egg","meat","poultry","fish","seafood","herb"]'`), NOT `"[]"`. This ensures database-level inserts get the same defaults as Python-level inserts.
- `__table_args__`: `UniqueConstraint("household_id", name="optimizer_config_household_key")`
- Use `@auto_init()` decorator on `__init__`

**Column pattern**: `mapped_column(Float, nullable=False, default=1.0, server_default="1.0")`. The `server_default` must be a string. Import `JSON` from `sqlalchemy`.

Also update `mealie/db/models/optimizer/__init__.py` to add `from .config import *` after the existing `from .pantry import *` line.
</context>

<subtasks>
- [ ] Create `mealie/db/models/optimizer/config.py` with OptimizerConfigModel
- [ ] Add `from .config import *` to `mealie/db/models/optimizer/__init__.py`
</subtasks>

<acceptance>
- `python -c "from mealie.db.models.optimizer.config import OptimizerConfigModel; print('OK')"` succeeds
- `python -c "from mealie.db.models.optimizer import OptimizerConfigModel; print('OK')"` succeeds
- Model has 6 weight columns + prep_time_budget_minutes + 2 JSON keyword columns + id, group_id, household_id (12 columns total)
- UniqueConstraint on household_id is defined in `__table_args__`
- JSON column `server_default` values match the full Python default lists (not empty arrays)
</acceptance>
</task>

### 1.2 Create config schemas

<task id="1.2" status="pending" depends="1.1" risk="low">
<context>
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

**Note on defaults**: All weight fields MUST have defaults. This ensures `OptimizerConfigUpdate` can be used as a PUT body where the frontend sends all fields. The Pydantic defaults match the model defaults. `model_dump()` on a full update payload includes all fields — this is correct for full-replacement PUT semantics.
</context>

<subtasks>
- [ ] Create `mealie/schema/optimizer/config.py` with OptimizerConfigUpdate, OptimizerConfigSave, OptimizerConfigOut
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer.config import OptimizerConfigUpdate, OptimizerConfigSave, OptimizerConfigOut; print('OK')"` succeeds
- `OptimizerConfigUpdate()` validates successfully with all defaults populated
- `OptimizerConfigSave` extends Update with group_id and household_id (UUID4 required fields)
- `OptimizerConfigOut` has `from_attributes=True` for ORM mapping
- Field names match OptimizerConfigModel column names exactly (task 1.1)
</acceptance>
</task>

### 1.3 Create RepositoryOptimizerConfig

<task id="1.3" status="pending" depends="1.1, 1.2" risk="medium">
<context>
Create the repository for optimizer config at `mealie/repos/optimizer/config.py`.

**Pattern to follow**: `mealie/repos/optimizer/pantry.py` (RepositoryPantryItem).

```python
from sqlalchemy.exc import IntegrityError

from mealie.db.models.optimizer.config import OptimizerConfigModel
from mealie.repos.repository_generic import HouseholdRepositoryGeneric
from mealie.schema.optimizer.config import OptimizerConfigOut, OptimizerConfigSave


class RepositoryOptimizerConfig(HouseholdRepositoryGeneric[OptimizerConfigOut, OptimizerConfigModel]):
    def get_or_create_default(self) -> OptimizerConfigOut:
        """Return the household's config, creating with defaults if none exists."""
        result = self.session.execute(
            select(self.model).filter_by(household_id=self.household_id)
        ).scalars().one_or_none()

        if result:
            return self.schema.model_validate(result)

        # Create with defaults using the inherited create() method.
        # This handles session.add() + commit() + refresh() properly.
        save_data = OptimizerConfigSave(
            group_id=self.group_id,
            household_id=self.household_id,
        )
        try:
            return self.create(save_data)
        except IntegrityError:
            # Concurrent request already created the row — re-query
            self.session.rollback()
            result = self.session.execute(
                select(self.model).filter_by(household_id=self.household_id)
            ).scalars().one()
            return self.schema.model_validate(result)
```

**Why `self.create()` instead of manual session ops**: The inherited `create()` method (from `RepositoryGeneric`, line 181 of `repository_generic.py`) handles `session.add()` + `commit()` + `refresh()` + schema validation. Manual `session.add()` + `session.commit()` would skip `refresh()`, leaving auto-generated fields (like `id`) unpopulated on the returned object.

**Also add** `from sqlalchemy import select` to imports.

The file `mealie/repos/optimizer/__init__.py` already exists (verified). No changes needed there.
</context>

<subtasks>
- [ ] Create `mealie/repos/optimizer/config.py` with RepositoryOptimizerConfig
- [ ] Implement `get_or_create_default` using `self.create()` with IntegrityError handling
</subtasks>

<acceptance>
- `get_or_create_default()` returns OptimizerConfigOut with all default weights and a valid `id` field on first call
- Subsequent calls for the same household return the same config row (idempotent)
- `python -c "from mealie.repos.optimizer.config import RepositoryOptimizerConfig; print('OK')"` succeeds
</acceptance>
</task>

### 1.4 Register repo in repository_factory.py

<task id="1.4" status="pending" depends="1.3" risk="low">
<context>
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
</context>

<subtasks>
- [ ] Add 3 imports to repository_factory.py
- [ ] Add `optimizer_config` cached_property under Optimizer section
</subtasks>

<acceptance>
- `task py:lint` passes on `mealie/repos/repository_factory.py`
- Grep confirms: `grep -n "optimizer_config" mealie/repos/repository_factory.py` shows the new property
</acceptance>
</task>

### 1.5 Create config controller

<task id="1.5" status="pending" depends="1.4" risk="low">
<context>
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
        return self.repos.optimizer_config.update(config.id, data)
```

**Semantics**: PUT is full replacement. The `update()` method calls `data.model_dump()` which includes ALL fields (since all have defaults in `OptimizerConfigUpdate`). The frontend must always send the complete config object. This is correct and intentional.

Also update `mealie/routes/optimizer/__init__.py` to import and include the config controller router:
```python
from . import controller_pantry, controller_config
router = APIRouter()
router.include_router(controller_pantry.router)
router.include_router(controller_config.router)
```
</context>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_config.py` with GET and PUT endpoints
- [ ] Update `mealie/routes/optimizer/__init__.py` to include controller_config.router
</subtasks>

<acceptance>
- GET /api/households/optimizer/config returns 200 with default weights on first call
- PUT /api/households/optimizer/config with full config body `{"overlap_weight": 2.0, "pantry_utilization_weight": 0.6, "pantry_urgency_weight": 0.8, "protein_diversity_weight": 0.5, "category_balance_weight": 0.3, "rating_weight": 0.2, "prep_time_budget_minutes": null, "perishable_label_keywords": ["vegetable","fruit","dairy","egg","meat","poultry","fish","seafood","herb"], "shelf_stable_label_keywords": ["spice","grain","pasta","canned","dried","frozen","oil","vinegar","condiment"]}` returns updated config
- Subsequent GET returns the updated overlap_weight value
- Different households get independent configs (test by switching auth tokens)
</acceptance>
</task>

### 1.6 Create Alembic migration for optimizer_config table

<task id="1.6" status="pending" depends="1.1, 1.2" risk="medium">
<context>
Create an Alembic migration that creates the `optimizer_config` table.

**Pattern to follow**: `mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py`

**Steps**:
1. Generate the migration: `cd mealie && alembic revision --autogenerate -m "add optimizer config table"`
   - If autogenerate doesn't work, create manually
2. The migration's `down_revision` must be `"a1b2c3d4e5f6"` (the pantry items migration)
3. Verify the upgrade function creates:
   - Table `optimizer_config` with all columns matching OptimizerConfigModel
   - GUID type for id, group_id, household_id (use `mealie.db.migration_types.GUID()`)
   - Float columns for weights with `server_default` values as strings: `"1.0"`, `"0.6"`, `"0.8"`, `"0.5"`, `"0.3"`, `"0.2"`
   - Integer column for prep_time_budget_minutes (nullable)
   - JSON columns for keyword lists. **Critical**: `server_default` must be the full JSON-encoded default list, not `"[]"`. Example:
     ```python
     sa.Column("perishable_label_keywords", sa.JSON(), nullable=False,
               server_default='["vegetable","fruit","dairy","egg","meat","poultry","fish","seafood","herb"]')
     sa.Column("shelf_stable_label_keywords", sa.JSON(), nullable=False,
               server_default='["spice","grain","pasta","canned","dried","frozen","oil","vinegar","condiment"]')
     ```
   - ForeignKeyConstraints to groups.id and households.id
   - UniqueConstraint on household_id named `optimizer_config_household_key`
   - Indexes on group_id and household_id
4. Verify the downgrade function drops the table

**File naming convention**: `YYYY-MM-DD-HH.MM.SS_<revision_id>_<slug>.py` — use the auto-generated timestamp and revision ID.
</context>

<subtasks>
- [ ] Generate or create Alembic migration file
- [ ] Verify upgrade creates optimizer_config table with all columns, constraints, and indexes
- [ ] Verify JSON column server_defaults are full keyword lists (not empty arrays)
- [ ] Verify downgrade drops the table
- [ ] Run `cd mealie && alembic upgrade head` and verify table exists in database
- [ ] Run `cd mealie && alembic downgrade -1` and verify table is removed
</subtasks>

<acceptance>
- Migration chains from a1b2c3d4e5f6 (pantry items)
- `alembic upgrade head` succeeds and optimizer_config table exists
- `alembic downgrade -1` removes the table cleanly
- All weight columns have correct server_default values
- JSON columns have server_default matching the full keyword lists
</acceptance>

<rollback risk="medium">
Run `cd mealie && alembic downgrade -1` to remove the table. If migration is partially applied, manually drop the optimizer_config table.
</rollback>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `cd mealie && alembic upgrade head` succeeds (optimizer_config table created)
- [ ] GET /api/households/optimizer/config returns 200 with default weights
- [ ] PUT /api/households/optimizer/config updates weights and returns updated values
- [ ] `task py:lint` passes with no errors in new files
- [ ] `python -c "from mealie.db.models.optimizer import OptimizerConfigModel; print('OK')"` succeeds
</verification>
<gate>Config API is fully operational with GET-or-create and PUT-update semantics. Migration is reversible.</gate>
</checkpoint>

</phase>

---

## Phase 2: Backend — use_priority + Recipe-Foods Projection

<phase id="2" name="use_priority and Projection Endpoint" depends="1">

### 2.1 Add use_priority column to PantryItemModel

<task id="2.1" status="pending" depends="" risk="low">
<context>
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
</context>

<subtasks>
- [ ] Add `use_priority` column to PantryItemModel
- [ ] Add CheckConstraint to __table_args__
- [ ] Verify imports include CheckConstraint and String
</subtasks>

<acceptance>
- `grep -n "use_priority" mealie/db/models/optimizer/pantry.py` shows the column definition
- `grep -n "pantry_item_use_priority_check" mealie/db/models/optimizer/pantry.py` shows the constraint
- PantryItemModel has use_priority column with default "auto"
</acceptance>
</task>

### 2.2 Add use_priority to pantry schemas

<task id="2.2" status="pending" depends="2.1" risk="low">
<context>
Add `use_priority` field to the pantry Pydantic schemas at `mealie/schema/optimizer/pantry.py`.

**What to add** to `PantryItemCreate`:
```python
from typing import Literal  # add to imports

use_priority: Literal["auto", "high", "low"] = "auto"
```

This field will be inherited by `PantryItemSave`, `PantryItemUpdate`, `PantryItemUpdateBulk`, and `PantryItemOut` through the schema chain (they all extend PantryItemCreate directly or indirectly).

**Verify the inheritance chain**: Create -> Save (adds tenant IDs), Create -> Update (adds id), Update -> UpdateBulk, Create -> Out (adds id + relationships). Adding to Create propagates to all.
</context>

<subtasks>
- [ ] Add `Literal` import to pantry schema file
- [ ] Add `use_priority` field to PantryItemCreate class
- [ ] Verify field propagates to Save, Update, UpdateBulk, and Out schemas
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer.pantry import PantryItemCreate; PantryItemCreate(food_id='00000000-0000-0000-0000-000000000001', name='test', use_priority='high'); print('OK')"` succeeds
- `python -c "from mealie.schema.optimizer.pantry import PantryItemCreate; PantryItemCreate(food_id='00000000-0000-0000-0000-000000000001', name='test', use_priority='invalid')"` raises ValidationError
- `grep -n "use_priority" mealie/schema/optimizer/pantry.py` shows the field
</acceptance>
</task>

### 2.3 Create Alembic migration for use_priority column

<task id="2.3" status="pending" depends="1.6, 2.1" risk="medium">
<context>
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
</context>

<subtasks>
- [ ] Generate or create migration file chained from Phase 1 migration
- [ ] Verify upgrade adds column with server_default and check constraint
- [ ] Verify downgrade removes constraint and column
- [ ] Run `cd mealie && alembic upgrade head` and verify column exists
</subtasks>

<acceptance>
- Migration chains from the optimizer_config migration (verify `down_revision` matches)
- Existing pantry_items rows get use_priority='auto' (verify: `SELECT use_priority FROM pantry_items LIMIT 1`)
- `alembic downgrade -1` removes column and constraint cleanly
</acceptance>

<rollback risk="medium">
Run `cd mealie && alembic downgrade -1` to remove the column. If CHECK constraint removal fails on some databases, manually drop it first.
</rollback>
</task>

### 2.4 Create RecipeFoodProjection schema

<task id="2.4" status="pending" depends="" risk="low">
<context>
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
</context>

<subtasks>
- [ ] Create `mealie/schema/optimizer/recipe_projection.py` with both schema classes
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer.recipe_projection import RecipeFoodProjection, RecipeFoodProjectionResponse; print('OK')"` succeeds
- RecipeFoodProjection has all 9 fields (recipe_id, slug, name, food_ids, category_ids, tag_ids, rating, total_time, last_made)
- RecipeFoodProjectionResponse wraps items list with unlinked_recipe_count integer
</acceptance>
</task>

### 2.5 Create RecipeProjectionService

<task id="2.5" status="pending" depends="2.4" risk="medium">
<context>
Create the service class at `mealie/services/optimizer/recipe_projection.py` that queries recipes and returns lightweight projections.

**Query pattern** (follow `mealie/services/optimizer/recipe_utils.py` for reference):

```python
from datetime import datetime

from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mealie.db.models.household.household_to_recipe import HouseholdToRecipe
from mealie.db.models.recipe.recipe import RecipeModel
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
            food_ids = list({
                ing.food_id for ing in recipe.recipe_ingredient
                if ing.food_id is not None
            })
            if not food_ids:
                unlinked_count += 1
                continue

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

**Key implementation notes**:
- `food_id` is nullable on RecipeIngredientModel — filter out None values
- Deduplicate food_ids per recipe (same food used twice counts once for scoring overlap)
- `last_made` comes from `HouseholdToRecipe` (per-household), NOT `RecipeModel.last_made` (global denormalized max). Pre-fetched into `last_made_map` to avoid N+1.
- Use `selectinload` (not `joinedload`) to avoid Cartesian product with multiple collections
- This query loads all group recipes at once — acceptable for typical household sizes (50-500 recipes). Not paginated.
- `from datetime import datetime` is required for the type annotation on `last_made_map`
</context>

<subtasks>
- [ ] Create `mealie/services/optimizer/recipe_projection.py` with RecipeProjectionService
- [ ] Implement get_all_recipe_food_projections with efficient selectinload query
- [ ] Handle nullable food_id, deduplicate food_ids, serialize last_made as ISO string
</subtasks>

<acceptance>
- `python -c "from mealie.services.optimizer.recipe_projection import RecipeProjectionService; print('OK')"` succeeds
- Service returns all group recipes as lightweight projections with food_ids deduplicated
- Recipes with zero food_ids excluded from items, counted in unlinked_recipe_count
- `grep -n "selectinload" mealie/services/optimizer/recipe_projection.py` confirms no N+1 queries
- last_made serialized as ISO string or None
</acceptance>
</task>

### 2.6 Create recipe-foods controller + update router

<task id="2.6" status="pending" depends="2.5, 1.5" risk="low">
<context>
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
</context>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_recipes.py`
- [ ] Update `mealie/routes/optimizer/__init__.py` to include controller_recipes
</subtasks>

<acceptance>
- GET /api/households/optimizer/recipe-foods returns 200 with RecipeFoodProjectionResponse JSON
- Response has `items` array and `unlinked_recipe_count` integer
- Each item has at most 9 fields (recipe_id, slug, name, food_ids, category_ids, tag_ids, rating, total_time, last_made) — verify this is lighter than a full recipe response (which includes instructions, notes, images, etc.)
- All three optimizer controllers (pantry, config, recipes) are registered: `grep -n "include_router" mealie/routes/optimizer/__init__.py` shows 3 lines
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] `cd mealie && alembic upgrade head` succeeds (both new migrations applied)
- [ ] Pantry CRUD round-trips use_priority field: POST with use_priority="high", GET returns "high"
- [ ] GET /api/households/optimizer/recipe-foods returns projection data
- [ ] Projection excludes recipes with zero food_ids
- [ ] Projection returns household-scoped last_made (not global RecipeModel.last_made)
- [ ] `task py:lint` passes
</verification>
<gate>All backend endpoints operational. Pantry items support use_priority with validation. Projection endpoint returns lightweight recipe data with household-scoped last_made, suitable for client-side scoring.</gate>
</checkpoint>

</phase>

---

## Phase 3: Frontend — TypeScript Scoring Engine

<phase id="3" name="Scoring Engine" depends="">

Note: Phase 3 has no backend dependencies — it can be developed in parallel with Phases 1-2. It only depends on type definitions.

### 3.1 Create scoring engine types

<task id="3.1" status="pending" depends="" risk="low">
<context>
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
  // Note: no prepTime weight. Prep time is a hard filter (exclude/include),
  // not a continuous score, so it doesn't participate in the weighted sum.
  // The prep time budget comes from OptimizerConfig.prep_time_budget_minutes.
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

**Design notes**:
- These types have ZERO Vue/Nuxt dependencies — they are plain TypeScript interfaces.
- `RecipeFoodData` is structurally identical to `RecipeFoodProjection` in the API types (task 4.1) but lives in the scoring domain. The composable (task 3.5) maps API responses to this type. Keeping them separate allows the scoring engine to remain decoupled from the API layer.
- `ScoringWeights` intentionally excludes `prepTime` as a weight. The `prepTimeScore` function acts as a hard filter (0.0 = excluded, 1.0 = included). Since all surviving candidates score 1.0, a weight on it would add a constant to all scores without affecting ranking. The prep time budget is passed separately to `scoreRecipes`.
</context>

<subtasks>
- [ ] Create directory `frontend/app/composables/optimizer/` if needed
- [ ] Create `frontend/app/composables/optimizer/types.ts` with all 5 interfaces
</subtasks>

<acceptance>
- `grep -c "export interface" frontend/app/composables/optimizer/types.ts` outputs 5
- ScoringWeights has 8 fields (6 numeric weights + 2 keyword arrays), NO prepTime weight
- RecipeFoodData has 9 fields matching RecipeFoodProjection (camelCase)
- No Vue/Nuxt imports: `grep "import.*vue\|import.*nuxt" frontend/app/composables/optimizer/types.ts` returns empty
</acceptance>
</task>

### 3.2 Implement parsing and resolution helpers

<task id="3.2" status="pending" depends="3.1" risk="medium">
<context>
Create the scoring engine file at `frontend/app/composables/optimizer/scoring-engine.ts` and implement the first group of functions: parsing utilities and priority resolution.

**Critical**: This file must have ZERO Vue/Nuxt/browser dependencies. Only import from `./types`.

**Functions to implement** (all are pure — no side effects):

1. **`parseTimeToMinutes(totalTime: string | null): number | null`**
   - Parse free-form time strings like "30 Minutes", "1 Hour 15 Minutes", "1.5 Hours"
   - Return minutes as number, or null if unparseable
   - Handle: "X Minutes", "X Hours", "X Hours Y Minutes", "X Hour Y Minutes"
   - Case-insensitive matching
   - Implementation: use regex like `/(\d+(?:\.\d+)?)\s*hour/i` and `/(\d+)\s*min/i`

2. **`normalizedRating(rating: number | null): number`**
   - Return rating / 5.0, or 0.5 if null (neutral default)
   - Clamp to [0.0, 1.0]

3. **`resolveEffectivePriority(item: PantryItemScoring, perishableKeywords: string[], shelfStableKeywords: string[]): "high" | "low"`**
   - If usePriority !== "auto", return it directly
   - Auto-resolution rules (checked in order):
     - If expirationDate is set and <= 5 days away -> "high"
     - If labelName matches any perishableKeywords (case-insensitive substring) -> "high"
     - If labelName matches any shelfStableKeywords (case-insensitive substring) -> "low"
     - Otherwise -> "high" (safe default — prefer to use up)
   - The keyword lists come from `ScoringWeights.perishableLabelKeywords` / `shelfStableLabelKeywords`

4. **`expirationMultiplier(daysToExpiry: number | null): number`**
   - null (no expiration) -> 1.0
   - 7+ days -> 1.0
   - 3-6 days -> 1.5
   - 1-2 days -> 2.0
   - 0 or negative (expired) -> 2.5
</context>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/scoring-engine.ts`
- [ ] Implement `parseTimeToMinutes` with regex-based parsing
- [ ] Implement `normalizedRating` with clamping
- [ ] Implement `resolveEffectivePriority` with keyword matching
- [ ] Implement `expirationMultiplier` with tiered thresholds
- [ ] Verify zero Vue/Nuxt imports
</subtasks>

<acceptance>
- All 4 functions are exported from the file
- `parseTimeToMinutes("30 Minutes")` returns 30, `parseTimeToMinutes("1 Hour 15 Minutes")` returns 75, `parseTimeToMinutes(null)` returns null
- `normalizedRating(5)` returns 1.0, `normalizedRating(null)` returns 0.5
- `resolveEffectivePriority` returns explicit priority when not "auto", uses keyword matching for "auto"
- `expirationMultiplier(null)` returns 1.0, `expirationMultiplier(0)` returns 2.5
- `grep "import.*vue\|import.*nuxt" frontend/app/composables/optimizer/scoring-engine.ts` returns empty
</acceptance>
</task>

### 3.3 Implement individual scoring functions

<task id="3.3" status="pending" depends="3.2" risk="medium">
<context>
Add the individual scoring functions to `frontend/app/composables/optimizer/scoring-engine.ts` (the file created in task 3.2).

**Functions to implement** (all are pure — no side effects):

1. **`overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number`**
   - Return fraction of candidate's foods that appear in the planned set
   - If candidate has no foods, return 0
   - Range: [0.0, 1.0]

2. **`pantryCoverageScore(candidateFoodIds: string[], pantryFoodIds: Set<string>): number`**
   - Return fraction of candidate's foods present in pantry
   - The `pantryFoodIds` set should already exclude assume_enough items (caller pre-filters in scoreRecipes)
   - Range: [0.0, 1.0]

3. **`pantryUrgencyScore(candidateFoodIds: string[], pantryMap: Map<string, PantryItemScoring>, perishableKeywords: string[], shelfStableKeywords: string[]): { score: number; matches: PantryMatchDetail[] }`**
   - For each candidate food found in pantryMap:
     - Resolve effective priority via `resolveEffectivePriority(item, perishableKeywords, shelfStableKeywords)`
     - Calculate days to expiry from item.expirationDate
     - priority_weight: high=1.0, low=0.3
     - Score contribution = priority_weight * expirationMultiplier(daysToExpiry)
   - Final score = sum of contributions / candidateFoodIds.length
   - Skip items with assumeEnough=true
   - Return both score and matches array (for UI annotation)

4. **`proteinDiversityScore(candidateTagIds: string[], plannedProteinTags: Map<string, number>): number`**
   - Penalize if candidate shares tags with frequently-planned entries
   - 1.0 if no overlap with planned tags, decreasing with more overlap
   - If candidate has no tags, return 0.5 (neutral)

5. **`categoryBalanceScore(candidateCategoryIds: string[], plannedCategoryCounts: Map<string, number>): number`**
   - Bonus for underrepresented categories
   - 1.0 if category not yet planned, decreasing with count
   - If candidate has no categories, return 0.5 (neutral)

6. **`prepTimeScore(totalTime: string | null, budgetMinutes: number | null): number`**
   - Parse totalTime using parseTimeToMinutes
   - If no budget (null), return 1.0
   - If parsed minutes <= budget, return 1.0
   - If exceeds budget, return 0.0 (hard filter — recipe will be excluded by orchestrator)
   - If unparseable, return 1.0 (don't penalize missing data)
</context>

<subtasks>
- [ ] Implement `overlapScore` with set intersection
- [ ] Implement `pantryCoverageScore` with set intersection
- [ ] Implement `pantryUrgencyScore` with priority resolution and expiration weighting
- [ ] Implement `proteinDiversityScore` with overlap penalty
- [ ] Implement `categoryBalanceScore` with underrepresentation bonus
- [ ] Implement `prepTimeScore` as hard filter
</subtasks>

<acceptance>
- All 6 functions are exported from the file
- `overlapScore(["a","b"], new Set(["a"]))` returns 0.5
- `pantryCoverageScore(["a","b"], new Set(["a","b"]))` returns 1.0
- `pantryUrgencyScore` returns `{ score, matches }` with correct priority/expiry weighting
- `prepTimeScore("30 Minutes", 60)` returns 1.0, `prepTimeScore("90 Minutes", 60)` returns 0.0
- Functions with empty inputs return documented defaults (0, 0.5, or 1.0 as specified)
</acceptance>
</task>

### 3.4 Implement scoreRecipes orchestrator

<task id="3.4" status="pending" depends="3.3" risk="high">
<context>
Add the `scoreRecipes` orchestrator function to `frontend/app/composables/optimizer/scoring-engine.ts`.

This function ties together all individual scoring functions:

```typescript
export function scoreRecipes(
  candidates: RecipeFoodData[],
  plannedRecipes: RecipeFoodData[],
  pantryItems: PantryItemScoring[],
  weights: ScoringWeights,
  prepTimeBudget: number | null,
): ScoredRecipe[]
```

**Implementation steps**:

1. **Build derived data structures**:
   - `plannedFoodIds: Set<string>` — union of all food_ids from plannedRecipes
   - `plannedProteinTags: Map<string, number>` — count of each tag across planned recipes
   - `plannedCategoryCounts: Map<string, number>` — count of each category across planned recipes
   - `pantryFoodIds: Set<string>` — food_ids from pantryItems WHERE `assumeEnough === false`
   - `pantryMap: Map<string, PantryItemScoring>` — keyed by foodId, WHERE `assumeEnough === false`

2. **Score each candidate**:
   - Skip candidates with zero foodIds
   - Compute prepTimeScore first — if 0.0, exclude candidate entirely (hard filter)
   - Compute all other scores using individual functions
   - `totalScore = weights.overlap * overlapScore + weights.pantryCoverage * pantryCoverageScore + weights.pantryUrgency * urgencyResult.score + weights.proteinDiversity * proteinDiversityScore + weights.categoryBalance * categoryBalanceScore + weights.rating * normalizedRating`
   - **Note**: prepTimeScore is NOT included in the weighted sum. It acts only as a pre-filter. All surviving candidates would score 1.0, so including it would add a constant that doesn't affect ranking.
   - Collect breakdown (all individual scores keyed by factor name) and pantryMatches

3. **Sort by totalScore descending**

4. **Return ScoredRecipe[]**

**Edge cases**:
- Cold start (zero planned recipes): plannedFoodIds is empty, so overlapScore=0 for all. Recipes rank by pantry coverage, urgency, and rating.
- All pantry items are assume_enough: pantryFoodIds is empty, so pantryCoverageScore=0 and pantryUrgencyScore=0 for all.
</context>

<subtasks>
- [ ] Implement data structure builders (plannedFoodIds, pantryMap, etc.)
- [ ] Implement per-candidate scoring loop with prepTime pre-filter
- [ ] Implement weighted sum (excluding prepTime)
- [ ] Implement sorting and ScoredRecipe construction
- [ ] Verify zero-food candidates are excluded
- [ ] Verify prepTime-exceeding candidates are excluded
</subtasks>

<acceptance>
- `scoreRecipes` returns `ScoredRecipe[]` sorted by totalScore descending
- Recipes with zero foodIds are excluded from results
- Recipes exceeding prepTimeBudget are excluded from results
- Cold start (zero planned): all candidates get overlapScore=0, ranked by pantry+rating
- All assume_enough pantry items: coverage=0, urgency=0 for all
- Breakdown record contains named scores for each factor
- pantryMatches contains PantryMatchDetail for each matched pantry item
</acceptance>

<rollback risk="high">
If the orchestrator has bugs, comment out the body and return an empty array. Individual scoring functions (tasks 3.2-3.3) remain usable independently. Debug using the unit tests (task 3.6).
</rollback>
</task>

### 3.5 Create Vue composable wrapper

<task id="3.5" status="pending" depends="3.4" risk="low">
<context>
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

**Data flow note**: The API types (`RecipeFoodProjection` in task 4.1) and the scoring types (`RecipeFoodData`) are structurally identical. When the page/component calls the API, the response can be passed directly to `setCandidates()` — TypeScript structural typing means no explicit mapping is needed as long as the field names match. Both use camelCase. Verify that the field names in `RecipeFoodProjection` (task 4.1) match `RecipeFoodData` (task 3.1) exactly.

This composable owns no data-fetching logic — callers provide data via setters.
</context>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/use-optimizer-scoring.ts`
- [ ] Verify default ScoringWeights match OptimizerConfig backend defaults
</subtasks>

<acceptance>
- scoredRecipes is a ComputedRef that recomputes when any input ref changes (verify: set candidates, check scoredRecipes.value updates)
- Composable delegates all logic to scoring-engine.ts pure functions
- No direct API calls — data is provided by callers
- `grep "import.*from.*vue" frontend/app/composables/optimizer/use-optimizer-scoring.ts` shows only vue imports (not nuxt/fetch)
</acceptance>
</task>

### 3.6 Write scoring engine unit tests

<task id="3.6" status="pending" depends="3.4" risk="low">
<context>
Create comprehensive unit tests at `frontend/app/composables/optimizer/scoring-engine.test.ts` using Vitest.

**Test structure** — at least 2 test cases per function plus integration edge cases:

```typescript
import { describe, it, expect } from "vitest";
import {
  parseTimeToMinutes,
  overlapScore,
  pantryCoverageScore,
  pantryUrgencyScore,
  proteinDiversityScore,
  categoryBalanceScore,
  normalizedRating,
  prepTimeScore,
  resolveEffectivePriority,
  expirationMultiplier,
  scoreRecipes,
} from "./scoring-engine";
```

**Required test cases**:

1. `parseTimeToMinutes`: "30 Minutes"->30, "1 Hour"->60, "1 Hour 15 Minutes"->75, null->null, "garbage"->null
2. `overlapScore`: no overlap->0, full overlap->1.0, partial->fraction, empty candidate->0
3. `pantryCoverageScore`: all in pantry->1.0, none in pantry->0, partial->fraction
4. `pantryUrgencyScore`: high-priority expiring item->high score, low-priority->lower score, assume_enough items not in pantryMap
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
    - prepTime is NOT in the weighted sum (verify by checking totalScore doesn't include a prepTime component)
</context>

<subtasks>
- [ ] Create `frontend/app/composables/optimizer/scoring-engine.test.ts`
- [ ] Write test cases for all 11 function groups
- [ ] Run tests with `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts`
- [ ] All tests pass
</subtasks>

<acceptance>
- All scoring functions have at least 2 test cases each
- Edge cases from spec are covered (especially cold start, assume_enough, prep time filter)
- Tests pass: `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts` exits 0
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts` — all tests pass
- [ ] scoring-engine.ts has zero Vue/Nuxt imports: `grep -c "import.*vue\|import.*nuxt" frontend/app/composables/optimizer/scoring-engine.ts` returns 0
- [ ] use-optimizer-scoring.ts imports only from vue and local files
- [ ] `task ui:lint` passes on new files
</verification>
<gate>Scoring engine is complete with full test coverage. Composable provides reactive wrapper. No framework dependencies in core logic.</gate>
</checkpoint>

</phase>

---

## Phase 4: Frontend — API Clients, Types, i18n

<phase id="4" name="Frontend Integration" depends="1, 2">

### 4.1 Add config and projection types to optimizer.ts

<task id="4.1" status="pending" depends="" risk="low">
<context>
Add new TypeScript interfaces to the existing file `frontend/app/lib/api/types/optimizer.ts`.

**Append after the existing PantryDeductRequest interface**:

```typescript
// --- Optimizer Config ---

export interface OptimizerConfigUpdate {
  overlapWeight: number;
  pantryUtilizationWeight: number;
  pantryUrgencyWeight: number;
  proteinDiversityWeight: number;
  categoryBalanceWeight: number;
  ratingWeight: number;
  prepTimeBudgetMinutes: number | null;
  perishableLabelKeywords: string[];
  shelfStableLabelKeywords: string[];
}

export interface OptimizerConfigOut extends OptimizerConfigUpdate {
  id: string;
  groupId: string;
  householdId: string;
}

// --- Recipe-Foods Projection ---

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

**Important**: `OptimizerConfigUpdate` fields are all REQUIRED (not optional with `?`). This enforces full-replacement PUT semantics — the frontend must always send the complete config object. `OptimizerConfigOut` extends it, so all weight fields are guaranteed present in responses.

**Type alignment**: `RecipeFoodProjection` field names must exactly match `RecipeFoodData` in `frontend/app/composables/optimizer/types.ts` (task 3.1) for structural typing compatibility. Verify: recipeId, slug, name, foodIds, categoryIds, tagIds, rating, totalTime, lastMade — all match.
</context>

<subtasks>
- [ ] Add OptimizerConfigUpdate and OptimizerConfigOut interfaces (fields required, not optional)
- [ ] Add RecipeFoodProjection and RecipeFoodProjectionResponse interfaces
- [ ] Verify RecipeFoodProjection field names match RecipeFoodData (task 3.1) exactly
</subtasks>

<acceptance>
- All 4 new interfaces are exported from the file
- `OptimizerConfigUpdate` has NO optional (`?`) fields — all required
- `RecipeFoodProjection` field names match `RecipeFoodData` exactly (verify by diffing the two interfaces)
- `task ui:lint` passes
</acceptance>
</task>

### 4.2 Add usePriority to PantryItem types

<task id="4.2" status="pending" depends="" risk="low">
<context>
Add `usePriority` field to the existing PantryItem interfaces in `frontend/app/lib/api/types/optimizer.ts`.

**Modify PantryItemCreate** (around line 10) to add:
```typescript
usePriority?: "auto" | "high" | "low";
```

This will be inherited by PantryItemUpdate and PantryItemOut through the `extends` chain.
</context>

<subtasks>
- [ ] Add `usePriority` field to PantryItemCreate interface
- [ ] Verify PantryItemUpdate and PantryItemOut inherit it
</subtasks>

<acceptance>
- `grep "usePriority" frontend/app/lib/api/types/optimizer.ts` shows the field
- Type is correctly narrowed to the 3 valid string literals
</acceptance>
</task>

### 4.3 Add API clients for config and recipe-foods

<task id="4.3" status="pending" depends="4.1" risk="low">
<context>
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

**Note**: `updateConfig` accepts `OptimizerConfigUpdate` which has ALL fields required (not optional). This means the frontend must always send the full config. The typical flow: GET config -> display all fields in a form -> user edits some fields -> PUT the complete form data. This prevents accidental reset of unmodified fields to defaults.

`getRecipeFoods` is on OptimizerApi directly (not a sub-client) because it's a single read-only endpoint.
</context>

<subtasks>
- [ ] Add BaseAPI import and new type imports
- [ ] Add config and recipeFoods routes
- [ ] Create OptimizerConfigApi class extending BaseAPI
- [ ] Extend OptimizerApi with config sub-client and getRecipeFoods method
- [ ] Store requests instance in OptimizerApi for getRecipeFoods
</subtasks>

<acceptance>
- `grep "getConfig\|updateConfig\|getRecipeFoods" frontend/app/lib/api/user/optimizer-pantry.ts` shows all 3 methods
- `task ui:lint` passes
- TypeScript compiles without errors
</acceptance>
</task>

### 4.4 Add i18n keys

<task id="4.4" status="pending" depends="" risk="low">
<context>
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
</context>

<subtasks>
- [ ] Add use-priority, priority-auto, priority-high, priority-low keys to optimizer.pantry
- [ ] Add optimizer.config namespace with all 10 keys
</subtasks>

<acceptance>
- `python -c "import json; d=json.load(open('frontend/app/lang/messages/en-US.json')); print(d['optimizer']['pantry']['use-priority'])"` outputs "Priority"
- `python -c "import json; d=json.load(open('frontend/app/lang/messages/en-US.json')); print(d['optimizer']['config']['title'])"` outputs "Optimizer Settings"
- JSON is valid: `python -c "import json; json.load(open('frontend/app/lang/messages/en-US.json')); print('Valid JSON')"` succeeds
- Existing pantry keys are preserved
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] TypeScript compiles without errors: `cd frontend && npx tsc --noEmit` or `task ui:lint`
- [ ] All new interfaces are exported from optimizer.ts
- [ ] PantryItemCreate includes usePriority field
- [ ] OptimizerApi has config sub-client and getRecipeFoods method
- [ ] i18n JSON is valid and all keys resolve
- [ ] RecipeFoodProjection field names match RecipeFoodData exactly
</verification>
<gate>Frontend API clients match all backend endpoints. Types are complete and consistent. i18n keys are ready for Stage B UI work.</gate>
</checkpoint>

</phase>

---

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="high">
  <description>Alembic migration fails on upgrade or produces incorrect table schema</description>
  <mitigation>Run `alembic upgrade head` and `alembic downgrade -1` round-trip for each migration before proceeding to the next phase. Verify JSON column server_defaults manually.</mitigation>
  <detection>Migration command exits non-zero, or `\d optimizer_config` in psql shows wrong column types/defaults</detection>
</risk>
<risk id="R2" likelihood="medium" impact="medium">
  <description>Scoring engine produces incorrect rankings due to subtle bugs in weighted sum calculation</description>
  <mitigation>Comprehensive unit tests (task 3.6) cover each function independently and the orchestrator with known inputs/outputs. The orchestrator is separated into its own task (3.4) for focused testing.</mitigation>
  <detection>Unit tests fail, or manual inspection of scoreRecipes output with known test data shows unexpected ordering</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>Concurrent GET requests to config endpoint race on get_or_create_default</description>
  <mitigation>IntegrityError catch with rollback and re-query (task 1.3). UniqueConstraint on household_id prevents duplicate rows.</mitigation>
  <detection>500 errors on GET /api/households/optimizer/config under concurrent load</detection>
</risk>
<risk id="R4" likelihood="low" impact="medium">
  <description>Frontend sends partial config on PUT, resetting unmodified fields to defaults</description>
  <mitigation>TypeScript OptimizerConfigUpdate has all fields required (not optional). Frontend must GET then PUT the complete object. Documented in tasks 1.5 and 4.3.</mitigation>
  <detection>Config values unexpectedly reset to defaults after a PUT that only intended to change one field</detection>
</risk>
</risks>

## Final Validation

<final_validation>
<verification>
- [ ] `cd mealie && alembic upgrade head` applies both new migrations cleanly
- [ ] `cd mealie && alembic downgrade` to pre-optimizer-config state works cleanly
- [ ] GET /api/households/optimizer/config returns default config (verify all 9 fields present)
- [ ] PUT /api/households/optimizer/config with full body updates and returns config
- [ ] POST /api/households/optimizer/pantry with use_priority="high" round-trips correctly
- [ ] GET /api/households/optimizer/recipe-foods returns projection data with items array
- [ ] `task py:lint` passes
- [ ] `task py:test` passes (no regressions)
- [ ] `task ui:lint` passes
- [ ] `cd frontend && npx vitest run app/composables/optimizer/scoring-engine.test.ts` — all tests pass
- [ ] No regressions in existing pantry CRUD endpoints
</verification>
<acceptance>
Stage A is complete when: (1) Config API stores and returns per-household scoring weights including keyword lists, (2) pantry items support use_priority with validation, (3) recipe-foods projection endpoint returns lightweight recipe data with household-scoped last_made, (4) pure TypeScript scoring engine scores recipes with full test coverage, (5) frontend API clients can call all new endpoints with correct types, (6) all existing functionality is preserved.
</acceptance>
</final_validation>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/plans/2026-04-13-232845-optimizer-foundation.md">
  <question>Should the projection endpoint support pagination for very large recipe collections (1000+ recipes)?</question>
  <default_assumption>No pagination for Stage A. The projection is lightweight (~200 bytes per recipe). For 500 recipes, response is ~100KB — well within acceptable limits. Re-evaluate if real-world usage shows issues.</default_assumption>
  <impact>Memory and response time for large groups. Typical household: 50-500 recipes.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/plans/2026-04-13-232845-optimizer-foundation.md">
  <question>Should GET /households/optimizer/config create a default row (write-on-read), or should the frontend handle missing config by using client-side defaults?</question>
  <default_assumption>GET creates default row (upsert-on-read). Simpler frontend code. The IntegrityError catch in get_or_create_default handles concurrent races.</default_assumption>
  <impact>Affects API semantics and frontend complexity.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/plans/2026-04-13-232845-optimizer-foundation.md">
<resolved original_question="Should food_ids in the projection be deduplicated per recipe?">
  <resolution>Yes — deduplicate. The scoring engine measures ingredient overlap by food identity, not by ingredient instance count. Deduplication is correct for set intersection scoring.</resolution>
</resolved>
<resolved original_question="Should the scoring engine normalize total_time on the backend?">
  <resolution>No — keep parsing client-side in Stage A. parseTimeToMinutes handles common formats and gracefully returns null for unparseable values (score 1.0 = not penalized).</resolution>
</resolved>
<resolved original_question="How should the scoring engine classify food labels as perishable vs. shelf-stable?">
  <resolution>Configurable keyword lists stored as JSON columns on OptimizerConfigModel. Shipped with sensible defaults. Users customize via config PUT endpoint.</resolution>
</resolved>
<resolved original_question="Should RecipeFoodProjection include household-scoped last_made or global?">
  <resolution>Household-scoped from HouseholdToRecipe join table. Pre-fetched in single query.</resolution>
</resolved>
</resolved_from_source>

<resolved_from_source source="docs/plans/2026-04-13-232845-optimizer-foundation.md (revision review)">
<resolved original_question="Should prepTime be included as a weight in the scoring weighted sum?">
  <resolution>No. prepTimeScore is a binary hard filter (0.0 = excluded, 1.0 = included). All surviving candidates score 1.0, so including prepTime weight in the weighted sum adds a constant that doesn't affect relative ranking. Prep time budget is passed as a separate parameter to scoreRecipes, and prepTimeScore acts as a pre-filter only. Removed prepTime from ScoringWeights interface.</resolution>
</resolved>
<resolved original_question="Should OptimizerConfigUpdate TypeScript fields be optional or required?">
  <resolution>Required. PUT semantics are full replacement. The frontend must always send the complete config object. Making fields optional would allow partial sends that reset unmodified fields to Pydantic defaults on the backend. The correct flow: GET full config -> edit -> PUT full config.</resolution>
</resolved>
</resolved_from_source>
