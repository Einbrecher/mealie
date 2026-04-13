# Implementation Plan: Pantry Quantity Tracking

Source: docs/specs/2026-04-13-041703-pantry-quantity-tracking.md
Created: 2026-04-13

<plan_metadata>
  <feature>Pantry Quantity Tracking with Deficit Calculation</feature>
  <source_doc>docs/specs/2026-04-13-041703-pantry-quantity-tracking.md</source_doc>
  <total_phases>7</total_phases>
  <total_tasks>16</total_tasks>
  <critical_path>1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 3.1 → 3.3 → 4.1 → 5.1 → 5.3</critical_path>
  <status>reviewed</status>
</plan_metadata>

## Overview

Extend the Phase 2 Pantry Tracker to support quantity tracking for pantry items with deficit calculation against recipe requirements. Adds a new `pantry_items` database table with quantity/unit fields and an `assume_enough` toggle that bypasses quantity checking. Integrates with the shopping list flow to auto-check covered items or reduce quantities for partial coverage. Includes full CRUD API, deficit calculation endpoint, and a frontend pantry management page.

## Dependencies & Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>Python 3.12 with FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2 installed</description>
  <verification>Run `task setup` — all backend dependencies are in pyproject.toml</verification>
</prereq>
<prereq id="P2" type="library" verified="true">
  <description>Pint unit registry (used by UnitConverter at mealie/services/parser_services/parser_utils/unit_utils.py)</description>
  <verification>Already a dependency — UnitConverter.__init__ creates UnitRegistry()</verification>
</prereq>
<prereq id="P3" type="data" verified="true">
  <description>ingredient_foods and ingredient_units tables exist with data</description>
  <verification>Tables defined in mealie/db/models/recipe/ingredient.py — IngredientFoodModel.__tablename__ = "ingredient_foods", IngredientUnitModel.__tablename__ = "ingredient_units"</verification>
</prereq>
<prereq id="P4" type="environment" verified="true">
  <description>Empty optimizer/ placeholder directories exist with __init__.py files</description>
  <verification>Verified: mealie/db/models/optimizer/__init__.py, mealie/schema/optimizer/__init__.py, mealie/repos/optimizer/__init__.py (empty or blank), mealie/routes/optimizer/__init__.py, mealie/services/optimizer/ all exist</verification>
</prereq>
<prereq id="P5" type="environment" verified="true">
  <description>Nuxt 4 frontend with Vuetify 4, Vue 3 Composition API</description>
  <verification>frontend/app/pages/g/[groupSlug]/optimizer/ exists with .gitkeep; frontend/app/components/optimizer/ exists with .gitkeep</verification>
</prereq>
</prerequisites>

## Phase 1: Database Layer

<phase id="1" name="Database Layer">

### 1.1 Create PantryItemModel

<task id="1.1" status="pending" depends="" risk="low">
<description>
Create the SQLAlchemy model for the `pantry_items` table at `mealie/db/models/optimizer/pantry.py`.

**Critical codebase patterns to follow** (verified via exploration):

1. **Inheritance**: `class PantryItemModel(SqlAlchemyBase, BaseMixins)` — imports from `mealie.db.models._model_base`
2. **GUID primary key override**: The base class defines `id` as `Integer`, so you MUST override it:
   ```python
   id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
   ```
3. **Auto-init decorator**: Use `@auto_init()` from `mealie.db.models._model_utils.auto_init` on `__init__(self, **_) -> None: ...`
4. **Timestamp columns**: `SqlAlchemyBase` already provides `created_at` and `update_at` (note: column name is `update_at`, NOT `updated_at` — there is a synonym). Do NOT re-declare these columns.
5. **Foreign keys**: Reference `households.id`, `ingredient_foods.id`, `ingredient_units.id`
6. **Relationships**: Define `food` and `unit` relationships with `uselist=False`

**Columns to define**:
- `id`: GUID PK (override base)
- `household_id`: GUID FK → households.id, NOT NULL, indexed
- `food_id`: GUID FK → ingredient_foods.id, nullable, indexed
- `name`: String, nullable (for items not in foods DB)
- `is_staple`: Boolean, default False
- `assume_enough`: Boolean, default False
- `quantity`: Float, nullable (null = untracked/boolean on_hand behavior)
- `unit_id`: GUID FK → ingredient_units.id, nullable
- `expiration_date`: Date, nullable

**Table constraints**:
- `UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key")` — prevents duplicate foods per household
- `CheckConstraint("food_id IS NOT NULL OR name IS NOT NULL", name="pantry_item_food_or_name_check")` — at least one identifier required

**Important**: Import relationship targets as strings to avoid circular imports:
```python
food: Mapped["IngredientFoodModel | None"] = relationship("IngredientFoodModel", uselist=False, foreign_keys=[food_id])
unit: Mapped["IngredientUnitModel | None"] = relationship("IngredientUnitModel", uselist=False, foreign_keys=[unit_id])
```

Also add `__all__ = ["PantryItemModel"]` at the top of the file for wildcard export.
</description>

<subtasks>
- [ ] Create file `mealie/db/models/optimizer/pantry.py`
- [ ] Define `PantryItemModel` class with all columns, constraints, and relationships
- [ ] Add `__all__` export
- [ ] Verify the file imports correctly: `python -c "from mealie.db.models.optimizer.pantry import PantryItemModel"`
</subtasks>

<acceptance>
- File exists at `mealie/db/models/optimizer/pantry.py`
- `PantryItemModel.__tablename__` equals `"pantry_items"`
- Model has UniqueConstraint on (household_id, food_id) and CheckConstraint on food_id/name
- Model has food and unit relationships with uselist=False
- `python -c "from mealie.db.models.optimizer.pantry import PantryItemModel; print(PantryItemModel.__tablename__)"` prints `pantry_items`
</acceptance>
</task>

### 1.2 Export PantryItemModel from optimizer package

<task id="1.2" status="pending" depends="1.1" risk="low">
<description>
Modify `mealie/db/models/optimizer/__init__.py` (currently empty/blank) to export PantryItemModel via wildcard import.

**File content should be**:
```python
from .pantry import *
```

This enables the `from .optimizer import *` in `_all_models.py` to pick up the model.
</description>

<subtasks>
- [ ] Edit `mealie/db/models/optimizer/__init__.py` to add `from .pantry import *`
</subtasks>

<acceptance>
- `python -c "from mealie.db.models.optimizer import PantryItemModel"` succeeds
</acceptance>
</task>

### 1.3 Register optimizer models in _all_models.py

<task id="1.3" status="pending" depends="1.2" risk="low">
<description>
Add optimizer model registration to `mealie/db/models/_all_models.py` so Alembic autogenerate discovers the new table.

**Current file** has these wildcard imports:
```python
from .group import *
from .labels import *
from .recipe import *
from .server import *
from .users import *
```

**Add this line** (maintain alphabetical order):
```python
from .optimizer import *
```

Place it between `.labels` and `.recipe` imports.

**Note**: `mealie/alembic/env.py` auto-discovers models via `import mealie.db.models._all_models`, so this single import line is all that's needed for Alembic to detect PantryItemModel.
</description>

<subtasks>
- [ ] Add `from .optimizer import *` to `mealie/db/models/_all_models.py`
</subtasks>

<acceptance>
- `python -c "import mealie.db.models._all_models"` succeeds without errors
- `from .optimizer import *` line present in the file
</acceptance>
</task>

### 1.4 Create Alembic migration

<task id="1.4" status="pending" depends="1.3" risk="medium">
<description>
Generate and verify the Alembic migration for the `pantry_items` table.

**Steps**:
1. Run `alembic revision --autogenerate -m "add pantry items table"` from the project root (or `task py:migrate` if that generates)
2. Verify the generated migration file creates the `pantry_items` table with all expected columns
3. The migration should use `mealie.db.migration_types.GUID()` for GUID columns (Alembic's env.py configures `user_module_prefix="mealie.db.migration_types."`)
4. Verify the migration includes:
   - All 9 data columns (id, household_id, food_id, name, is_staple, assume_enough, quantity, unit_id, expiration_date)
   - `created_at` and `update_at` timestamp columns (from base class)
   - Indexes on household_id and food_id
   - UniqueConstraint `pantry_item_household_food_key`
   - CheckConstraint `pantry_item_food_or_name_check`
   - Foreign keys to households, ingredient_foods, ingredient_units
5. Verify the downgrade drops the table

**Migration pattern** (from recent codebase migration `2026-03-27`):
```python
revision = "<auto-generated>"
down_revision = "4395a04f7784"  # latest existing migration
```

**Important**: The migration uses `batch_alter_table` for SQLite compatibility. For `create_table` operations, this is typically not needed — just use `op.create_table()` directly.

**Rollback**: If migration is wrong, delete the generated file and regenerate.
</description>

<subtasks>
- [ ] Run Alembic autogenerate to create migration
- [ ] Review generated migration for correctness (all columns, constraints, indexes)
- [ ] Edit migration if needed (add missing constraints, fix column types)
- [ ] Test migration: `alembic upgrade head` on a fresh/test database
- [ ] Test downgrade: `alembic downgrade -1`
</subtasks>

<acceptance>
- Migration file exists in `mealie/alembic/versions/`
- `alembic upgrade head` succeeds without errors
- `alembic downgrade -1` succeeds (drops pantry_items table)
- Database contains `pantry_items` table with correct schema after upgrade
</acceptance>

<rollback risk="medium">
Delete the generated migration file. Run `alembic downgrade -1` if it was already applied.
</rollback>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `python -c "from mealie.db.models.optimizer.pantry import PantryItemModel"` succeeds
- [ ] `python -c "import mealie.db.models._all_models"` succeeds
- [ ] Alembic migration applies cleanly
- [ ] Database has `pantry_items` table with all columns, indexes, constraints, and foreign keys
</verification>
<success_criteria>PantryItemModel is fully defined, registered for Alembic, and the migration creates the table correctly. The database layer is complete and ready for the schema/repository layers.</success_criteria>
</checkpoint>

</phase>

## Phase 2: Schema Layer

<phase id="2" name="Schema Layer" depends="1">

### 2.1 Create Pydantic schemas for pantry CRUD and deficit reporting

<task id="2.1" status="pending" depends="1.1" risk="low">
<description>
Create Pydantic schemas at `mealie/schema/optimizer/pantry.py` for pantry item CRUD operations and deficit reporting.

**Critical codebase patterns** (verified):

1. **Base class**: `MealieModel` from `mealie.schema._mealie.mealie_model` (not `BaseModel`)
2. **UpdatedAtField**: Use `from mealie.schema._mealie.mealie_model import UpdatedAtField` — this is a Field wrapper that handles the `update_at` ↔ `updatedAt` alias mapping:
   ```python
   updated_at: datetime | None = UpdatedAtField(None)
   ```
3. **loader_options**: Classmethod returning `list[LoaderOption]` for eager-loading relationships. Use `joinedload` for to-one relationships:
   ```python
   from sqlalchemy.orm import joinedload
   from mealie.db.models.optimizer.pantry import PantryItemModel
   
   @classmethod
   def loader_options(cls) -> list[LoaderOption]:
       return [
           joinedload(PantryItemModel.food),
           joinedload(PantryItemModel.unit),
       ]
   ```
4. **ConfigDict**: Use `model_config = ConfigDict(from_attributes=True)` on the Out schema for ORM serialization
5. **Existing schema types**: Import `IngredientFood` and `IngredientUnit` from `mealie.schema.recipe.recipe_ingredient` for nested serialization
6. **PaginationBase**: Import from `mealie.schema.response.pagination`, define as:
   ```python
   class PantryItemPagination(PaginationBase):
       items: list[PantryItemOut]
   ```

**Schemas to create**:

1. `PantryItemCreate` — input for creating pantry items
   - Fields: food_id (UUID4|None), name (str|None), is_staple (bool=False), assume_enough (bool=False), quantity (float|None), unit_id (UUID4|None), expiration_date (date|None)
   - `@model_validator(mode="after")` to reject when both food_id and name are None
   - `@model_validator(mode="after")` to note that when assume_enough=True, quantity is irrelevant (but allow it — don't strip it, just document the semantics)

2. `PantryItemSave(PantryItemCreate)` — adds `household_id: UUID4` (set by controller, not user input)

3. `PantryItemUpdate(PantryItemCreate)` — adds `id: UUID4`

4. `PantryItemUpdateBulk(PantryItemUpdate)` — for bulk operations (same as Update for now)

5. `PantryItemOut(PantryItemCreate)` — response schema
   - Adds: id (UUID4), household_id (UUID4), food (IngredientFood|None), unit (IngredientUnit|None), created_at (datetime|None), updated_at with UpdatedAtField
   - `model_config = ConfigDict(from_attributes=True)`
   - `loader_options()` classmethod

6. `PantryItemPagination(PaginationBase)` — paginated response

7. `PantryDeficitItem(MealieModel)` — single ingredient deficit analysis
   - Fields: food_id (UUID4|None), food_name (str), recipe_quantity (float), recipe_unit (IngredientUnit|None), pantry_quantity (float|None), pantry_unit (IngredientUnit|None), deficit (float), assume_enough (bool=False), covered (bool), conversion_failed (bool=False)

8. `PantryDeficitReport(MealieModel)` — full deficit report
   - Fields: items (list[PantryDeficitItem]), uncovered_items (list[PantryDeficitItem]), total_items (int), covered_count (int), coverage_percent (float)

Add `__all__` listing all schema class names.
</description>

<subtasks>
- [ ] Create file `mealie/schema/optimizer/pantry.py`
- [ ] Implement PantryItemCreate with model_validators
- [ ] Implement PantryItemSave, PantryItemUpdate, PantryItemUpdateBulk
- [ ] Implement PantryItemOut with loader_options, ConfigDict, UpdatedAtField
- [ ] Implement PantryItemPagination
- [ ] Implement PantryDeficitItem and PantryDeficitReport
- [ ] Add __all__ export
- [ ] Verify: `python -c "from mealie.schema.optimizer.pantry import PantryItemCreate, PantryItemOut, PantryDeficitReport"`
</subtasks>

<acceptance>
- All 8 schema classes defined and importable
- `PantryItemCreate(food_id=None, name=None)` raises ValidationError
- `PantryItemCreate(food_id=some_uuid)` succeeds
- `PantryItemCreate(name="Salt")` succeeds
- `PantryItemOut.loader_options()` returns list with joinedload for food and unit
- `PantryItemOut.model_config["from_attributes"]` is True
</acceptance>
</task>

### 2.2 Export pantry schemas from optimizer package

<task id="2.2" status="pending" depends="2.1" risk="low">
<description>
Modify `mealie/schema/optimizer/__init__.py` (currently empty) to export pantry schemas.

**File content**:
```python
from .pantry import *
```
</description>

<subtasks>
- [ ] Edit `mealie/schema/optimizer/__init__.py` to add `from .pantry import *`
</subtasks>

<acceptance>
- `python -c "from mealie.schema.optimizer import PantryItemCreate, PantryItemOut"` succeeds
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] All schema classes importable from `mealie.schema.optimizer`
- [ ] Validation rejects both-null food_id/name
- [ ] PantryItemOut has loader_options and from_attributes config
</verification>
<success_criteria>All Pydantic schemas defined, validated, and importable. Ready for repository and service layers.</success_criteria>
</checkpoint>

</phase>

## Phase 3: Repository Layer

<phase id="3" name="Repository Layer" depends="1,2">

### 3.1 Create RepositoryPantryItem

<task id="3.1" status="pending" depends="1.1,2.1" risk="low">
<description>
Create the data access layer at `mealie/repos/optimizer/pantry.py`.

**Critical codebase pattern** (verified):

`HouseholdRepositoryGeneric` at `mealie/repos/repository_generic.py` provides:
- Constructor: `(session, pk_name, Model, Schema, *, group_id, household_id)` — auto-scopes all queries by group_id AND household_id
- Inherited methods: `get_one(value, key=None)`, `page_all(pagination, override=None)`, `create(data)`, `update(match_value, new_data)`, `delete(value)`, `create_many(data)`, `update_many(data)`, `delete_many(values)`

**Custom methods to add**:

1. `by_food_id(food_id: UUID4) -> PantryItemOut | None`
   - Query: filter by food_id within the household scope (base class already filters by household_id)
   - Use `self.session.query(self.model).filter_by(food_id=food_id).one_or_none()` then convert to schema

2. `by_food_ids(food_ids: list[UUID4]) -> list[PantryItemOut]`
   - Query: filter where food_id IN food_ids within household scope
   - Used by deficit calculation to batch-load pantry items for multiple recipe ingredients

**Important**: Access `self.model` for the SQLAlchemy model class, `self.schema` for the Pydantic schema class. Use `self.session` for the database session. The base class's `_query()` method returns a pre-filtered query with group_id and household_id already applied.

```python
from mealie.repos.repository_generic import HouseholdRepositoryGeneric

class RepositoryPantryItem(HouseholdRepositoryGeneric[PantryItemOut, PantryItemModel]):
    ...
```
</description>

<subtasks>
- [ ] Create file `mealie/repos/optimizer/pantry.py`
- [ ] Implement RepositoryPantryItem with by_food_id and by_food_ids methods
- [ ] Verify import: `python -c "from mealie.repos.optimizer.pantry import RepositoryPantryItem"`
</subtasks>

<acceptance>
- RepositoryPantryItem extends HouseholdRepositoryGeneric
- by_food_id returns None when no match
- by_food_ids returns list filtered by food_ids within household scope
- All standard CRUD methods available via inheritance
</acceptance>
</task>

### 3.2 Create repos/optimizer/__init__.py export

<task id="3.2" status="pending" depends="3.1" risk="low">
<description>
The file `mealie/repos/optimizer/__init__.py` may not exist yet. Create or modify it to export the repository.

**File content**:
```python
from .pantry import RepositoryPantryItem

__all__ = ["RepositoryPantryItem"]
```
</description>

<subtasks>
- [ ] Create or edit `mealie/repos/optimizer/__init__.py`
</subtasks>

<acceptance>
- `python -c "from mealie.repos.optimizer import RepositoryPantryItem"` succeeds
</acceptance>
</task>

### 3.3 Register RepositoryPantryItem in AllRepositories

<task id="3.3" status="pending" depends="3.1,3.2" risk="medium">
<description>
Add the pantry repository as a `cached_property` on `AllRepositories` in `mealie/repos/repository_factory.py`.

**Exact pattern** (verified from existing code, e.g., `group_shopping_lists` at ~line 305):

```python
from functools import cached_property  # already imported

# Add these imports near the top of the file (with other model/repo/schema imports):
from mealie.db.models.optimizer.pantry import PantryItemModel
from mealie.repos.optimizer.pantry import RepositoryPantryItem
from mealie.schema.optimizer.pantry import PantryItemOut

# Add this cached_property to the AllRepositories class body:
@cached_property
def pantry_items(self) -> RepositoryPantryItem:
    return RepositoryPantryItem(
        self.session,
        PK_ID,
        PantryItemModel,
        PantryItemOut,
        group_id=self.group_id,
        household_id=self.household_id,
    )
```

**Where to place it**: After the existing household-scoped repositories (after `webhooks` property, before any closing class methods). Or logically group it with other household properties.

**PK_ID** is a constant defined in the same file: `PK_ID = "id"` (line ~82).
</description>

<subtasks>
- [ ] Add imports for PantryItemModel, RepositoryPantryItem, PantryItemOut
- [ ] Add `pantry_items` cached_property to AllRepositories class
- [ ] Verify: `python -c "from mealie.repos.repository_factory import AllRepositories; print(hasattr(AllRepositories, 'pantry_items'))"`
</subtasks>

<acceptance>
- AllRepositories has a `pantry_items` property
- Property returns RepositoryPantryItem scoped to group_id and household_id
- Property uses PK_ID as the primary key name
- No import errors when loading repository_factory module
</acceptance>

<rollback risk="medium">
This modifies a critical upstream file (repository_factory.py). If the edit breaks imports, remove the added import lines and cached_property. The rest of the codebase is unaffected since nothing references pantry_items yet.
</rollback>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `python -c "from mealie.repos.optimizer import RepositoryPantryItem"` succeeds
- [ ] `python -c "from mealie.repos.repository_factory import AllRepositories"` succeeds (no import errors)
- [ ] AllRepositories.pantry_items property exists and returns correct type
</verification>
<success_criteria>Repository layer is complete. Pantry items can be CRUD-operated via AllRepositories.pantry_items. Ready for service layer.</success_criteria>
</checkpoint>

</phase>

## Phase 4: Service Layer

<phase id="4" name="Service Layer" depends="3">

### 4.1 Create PantryService with deficit calculation

<task id="4.1" status="pending" depends="3.3" risk="medium">
<description>
Create the business logic service at `mealie/services/optimizer/pantry.py`.

**Service pattern** (verified from ShoppingListService):
- Constructor takes `repos: AllRepositories`
- Access repos via `self.repos.pantry_items`, `self.repos.ingredient_foods`, etc.
- No base class inheritance — plain class with composition

**UnitConverter usage** (verified from `mealie/services/parser_services/parser_utils/unit_utils.py`):
```python
from mealie.services.parser_services.parser_utils import UnitConverter

converter = UnitConverter()
# Check if conversion is possible:
can = converter.can_convert(standard_unit_1, standard_unit_2)  # returns bool
# Convert:
new_qty, new_unit = converter.convert(quantity, from_unit, to_unit)  # returns tuple[float, Unit]
```

**Important**: `can_convert` and `convert` accept `str | Unit` — use the unit's `standard_unit` field (from IngredientUnit schema) which maps to pint units. Many custom units won't have a standard_unit set, causing conversion to fail.

**Methods to implement**:

1. `__init__(self, repos: AllRepositories)` — store repos, create UnitConverter instance

2. `get_pantry_map(self) -> dict[UUID4, PantryItemOut]` — load all pantry items for household, return dict keyed by food_id (skip items with no food_id)

3. `calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None) -> PantryDeficitReport`

   **Deficit calculation rules** (from spec, with edge cases):
   - **No food_id on ingredient**: Skip — cannot match to pantry. Do NOT include in report.
   - **No pantry match**: deficit = recipe_qty, covered = False
   - **assume_enough = True**: covered = True, deficit = 0 (regardless of quantity)
   - **Pantry quantity is None** (untracked): covered = True, deficit = 0 (backward compat with boolean on_hand)
   - **Both have quantity + compatible units**: Convert to common unit, deficit = max(0, recipe_qty_converted - pantry_qty_converted). covered = (deficit == 0). **Floating-point tolerance**: use `round(deficit, 4)` before clamping to avoid precision artifacts (e.g., 2.0000000001 from pint conversion)
   - **Both have quantity + incompatible units** (including when either unit's `standard_unit` is None): deficit = recipe_qty, conversion_failed = True, covered = False
   - **Recipe has no quantity** (quantity=0 or None): deficit = 0, covered = True (nothing needed)

   **Critical: standard_unit gate** (from Codex review): Before attempting unit conversion, check that BOTH units have a non-None `standard_unit` field on their IngredientUnit schema. If either is None, treat as incompatible units (conversion_failed=True). The `UnitConverter.can_convert()` method operates on pint unit strings, and passing None will raise an exception.

   Build PantryDeficitItem for each processable ingredient. At the end, compute:
   - `uncovered_items = [item for item in items if not item.covered]`
   - `total_items = len(items)`
   - `covered_count = total_items - len(uncovered_items)`
   - `coverage_percent = (covered_count / total_items * 100) if total_items > 0 else 100.0`

4. `check_shopping_items(self, items: list[ShoppingListItemCreate]) -> list[ShoppingListItemCreate]`
   - Load pantry map once
   - For each item with a food_id that matches a pantry item:
     - If assume_enough or pantry quantity is None → set item.checked = True
     - If pantry has quantity and units are compatible:
       - Calculate deficit
       - If deficit <= 0 → set item.checked = True
       - If deficit > 0 → set item.quantity = deficit (reduce to what's still needed)
     - If units incompatible → leave unchanged (can't determine coverage)
   - Return modified items list

**Important**: RecipeIngredient schema (at `mealie/schema/recipe/recipe_ingredient.py`) has fields: `quantity` (float|None), `unit` (IngredientUnit|None), `food` (IngredientFood|None), `note` (str|None). Access food_id via `ingredient.food.id` and unit's standard_unit via `ingredient.unit.standard_unit` (if unit exists).

Create `mealie/services/optimizer/__init__.py` if it doesn't exist (may already exist as placeholder).
</description>

<subtasks>
- [ ] Create `mealie/services/optimizer/__init__.py` if needed (empty or with import)
- [ ] Create `mealie/services/optimizer/pantry.py`
- [ ] Implement PantryService.__init__
- [ ] Implement get_pantry_map
- [ ] Implement calculate_deficit with all edge cases
- [ ] Implement check_shopping_items
- [ ] Verify: `python -c "from mealie.services.optimizer.pantry import PantryService"`
</subtasks>

<acceptance>
- PantryService importable from mealie.services.optimizer.pantry
- calculate_deficit returns covered=True for items with assume_enough=True
- calculate_deficit returns covered=True for pantry items with null quantity
- calculate_deficit uses UnitConverter for unit conversion when both units have standard_unit
- calculate_deficit sets conversion_failed=True when units are incompatible
- calculate_deficit returns deficit=0 (not negative) when pantry has surplus
- check_shopping_items sets checked=True for fully covered items
- check_shopping_items reduces quantity to deficit for partially covered items
- check_shopping_items leaves items unchanged when no pantry match or conversion fails
</acceptance>

<rollback risk="medium">
If deficit calculation has bugs, the service can be updated in isolation — no other code depends on it yet until Phase 5 routes and Phase 6 shopping integration are added.
</rollback>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] PantryService importable without errors
- [ ] Manual or unit test of calculate_deficit with mock data covers all 6 deficit rules
- [ ] check_shopping_items correctly modifies items based on pantry state
</verification>
<success_criteria>Business logic for deficit calculation and shopping item adjustment is complete and correct. Ready for API route layer.</success_criteria>
</checkpoint>

</phase>

## Phase 5: API Routes

<phase id="5" name="API Routes" depends="4">

### 5.1 Create pantry controller

<task id="5.1" status="pending" depends="4.1" risk="medium">
<description>
Create the API controller at `mealie/routes/optimizer/controller_pantry.py`.

**IMPORTANT — Spec deviation**: The spec shows function-based route handlers, but the actual codebase uses **class-based controllers** with the `@controller(router)` decorator pattern. Follow the codebase pattern, not the spec.

**Controller pattern** (verified from `mealie/routes/households/controller_shopping_lists.py`):

```python
from functools import cached_property
from fastapi import APIRouter, Depends
from pydantic import UUID4
from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo

router = APIRouter(prefix="/households/optimizer/pantry", tags=["Optimizer: Pantry"])

@controller(router)
class PantryItemController(BaseCrudController):
    @cached_property
    def repo(self):
        return self.repos.pantry_items

    @cached_property
    def service(self):
        return PantryService(self.repos)

    @cached_property
    def mixins(self):
        return HttpRepo[PantryItemCreate, PantryItemOut, PantryItemUpdate](
            self.repo, self.logger,
        )
```

**Key details**:
- `BaseCrudController` (from `mealie/routes/_base/base_controllers.py`) extends `BaseUserController` which provides:
  - `self.user: PrivateUser` — authenticated user (injected via `Depends(get_current_user)`)
  - `self.group_id: UUID4` — from `self.user.group_id`
  - `self.household_id: UUID4` — from `self.user.household_id`
  - `self.repos: AllRepositories` — auto-scoped to user's group+household
  - `self.session: Session` — database session
  - `self.logger: Logger`
  - `self.publish_event()` — for event bus
- `HttpRepo` mixin provides get_one with 404 handling

**Route prefix consideration**: The spec says `/optimizer/pantry` but since this is household-scoped data, use `/households/optimizer/pantry` to be consistent with other household routes (e.g., `/households/shopping/lists`). The top-level `/api` prefix is added by `mealie/routes/__init__.py`.

**Endpoints to implement**:

1. `GET /` → PantryItemPagination — paginated list
   ```python
   @router.get("", response_model=PantryItemPagination)
   def get_all(self, q: PaginationQuery = Depends()):
       response = self.repo.page_all(pagination=q, override=PantryItemOut)
       response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
       return response
   ```

2. `POST /` → PantryItemOut (201) — create item
   - Accept PantryItemCreate, convert to PantryItemSave adding household_id from self.household_id
   - MealieModel provides a `.cast()` method for schema type conversion (verified in mealie/schema/_mealie/mealie_model.py). Use it:
     ```python
     save_data = data.cast(PantryItemSave, household_id=self.household_id)
     ```
     If `.cast()` doesn't support adding new fields, construct manually:
     ```python
     save_data = PantryItemSave(**data.model_dump(), household_id=self.household_id)
     ```
   - Call `self.repo.create(save_data)`

3. `GET /{item_id}` → PantryItemOut — get one
   - Use `self.mixins.get_one(item_id)` for 404 handling

4. `PUT /{item_id}` → PantryItemOut — update
   - Call `self.repo.update(item_id, data)`

5. `DELETE /{item_id}` → 204 — delete
   - Call `self.repo.delete(item_id)`

6. `POST /deficit` → PantryDeficitReport — deficit calculation
   - Accept `recipe_ids: list[UUID4]` in request body
   - Load recipes from `self.repos.recipes` (group-scoped, not household-scoped — use `get_repositories(self.session, group_id=self.group_id, household_id=None).recipes`)
   - Collect all recipe_ingredient lists
   - Call `self.service.calculate_deficit(all_ingredients)`
   - Return PantryDeficitReport

**Important for deficit endpoint**: Recipes are group-scoped (shared across households), but pantry items are household-scoped. The deficit endpoint needs to load recipes at the group level. See how ShoppingListService does this at line ~333 of shopping_lists.py:
```python
group_recipes_repo = get_repositories(self.repos.session, group_id=self.repos.group_id, household_id=None).recipes
```
</description>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_pantry.py`
- [ ] Implement PantryItemController with all 6 endpoints
- [ ] Handle household_id injection on create
- [ ] Handle recipe loading for deficit endpoint (group-scoped)
- [ ] Verify: `python -c "from mealie.routes.optimizer.controller_pantry import router"`
</subtasks>

<acceptance>
- Controller class extends BaseCrudController
- All endpoints use correct HTTP methods and status codes (201 create, no-content or success for delete)
- GET / supports PaginationQuery
- POST / adds household_id from authenticated user
- POST /deficit loads recipes and returns PantryDeficitReport
- All endpoints require authentication (via BaseCrudController)
</acceptance>
</task>

### 5.2 Register pantry controller in optimizer router

<task id="5.2" status="pending" depends="5.1" risk="low">
<description>
Modify `mealie/routes/optimizer/__init__.py` (currently empty) to aggregate the pantry controller router.

**File content**:
```python
from fastapi import APIRouter

from . import controller_pantry

router = APIRouter()
router.include_router(controller_pantry.router)
```

This follows the pattern from `mealie/routes/households/__init__.py`.
</description>

<subtasks>
- [ ] Edit `mealie/routes/optimizer/__init__.py`
</subtasks>

<acceptance>
- `python -c "from mealie.routes.optimizer import router"` succeeds
- Router includes the pantry controller routes
</acceptance>
</task>

### 5.3 Register optimizer router at top-level API

<task id="5.3" status="pending" depends="5.2" risk="medium">
<description>
Add the optimizer router to `mealie/routes/__init__.py`.

**Current file** imports and includes routers like:
```python
from . import (
    admin, app, auth, comments, explore, groups, households,
    organizers, parser, recipe, shared, unit_and_foods, users, validators,
)

router = APIRouter(prefix="/api")
router.include_router(app.router)
# ... more includes
```

**Changes**:
1. Add `optimizer` to the import tuple (maintain alphabetical order — between `organizers` and `parser`)
2. Add `router.include_router(optimizer.router)` after the existing include_router calls

**This is a modified upstream file** per CLAUDE.md — keep changes minimal.
</description>

<subtasks>
- [ ] Add `optimizer` to the import list in `mealie/routes/__init__.py`
- [ ] Add `router.include_router(optimizer.router)` call
- [ ] Verify: start the dev server and check that `/api/households/optimizer/pantry` endpoints appear in /docs
</subtasks>

<acceptance>
- Optimizer routes accessible at `/api/households/optimizer/pantry/*`
- No import errors when loading the routes module
- API documentation (Swagger/OpenAPI at /docs) shows the optimizer pantry endpoints
</acceptance>

<rollback risk="medium">
This modifies an upstream file. Remove the `optimizer` import and include_router line if it causes issues. No other changes needed.
</rollback>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] Start backend: `task py:postgres`
- [ ] API docs accessible at localhost:9000/docs showing optimizer/pantry endpoints
- [ ] `curl -X POST localhost:9000/api/households/optimizer/pantry -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"food_id": "...", "quantity": 2.0}'` returns 201
- [ ] `curl localhost:9000/api/households/optimizer/pantry` returns paginated list
- [ ] All CRUD operations work via API
</verification>
<success_criteria>Full REST API is operational. All CRUD endpoints and the deficit calculation endpoint respond correctly with proper authentication. Ready for shopping list integration.</success_criteria>
</checkpoint>

</phase>

## Phase 6: Shopping List Integration

<phase id="6" name="Shopping List Integration" depends="4">

### 6.1 Hook pantry checking into ShoppingListService

<task id="6.1" status="pending" depends="4.1" risk="high">
<description>
Modify `mealie/services/household_services/shopping_lists.py` to integrate pantry checking into the shopping list item creation flow.

**This modifies an upstream file** — per CLAUDE.md, keep changes to ~10 lines.

**Integration point** (verified at lines 154-223 of shopping_lists.py):

In the `bulk_create_items` method, after items are consolidated and merge-checked but before they're appended to `filtered_create_items`, apply pantry coverage.

**Current code flow** (lines 203-213):
```python
if merged or create_item.quantity < 0:
    continue

# create the item
if create_item.checked:
    # checked items should not have recipe references
    create_item.recipe_references = []
if auto_find_labels:
    create_item.label_id = self.find_matching_label(create_item)

filtered_create_items.append(create_item)
```

**Modified code** (insert between line 204 and line 206):
```python
if merged or create_item.quantity < 0:
    continue

# Pantry coverage: auto-check covered items, reduce partial coverage
from mealie.services.optimizer.pantry import PantryService
pantry_service = PantryService(self.repos)
filtered_for_pantry = pantry_service.check_shopping_items([create_item])
if filtered_for_pantry:
    create_item = filtered_for_pantry[0]

# create the item
...
```

**WAIT — Performance concern**: Creating PantryService inside the loop is inefficient. Better approach: apply pantry checking to ALL unmerged items at once, BEFORE the per-item loop.

**Revised approach** (~8 lines, inserted after line 177 `create_items = consolidated_create_items`):
```python
# Apply pantry coverage to consolidated items
from mealie.services.optimizer.pantry import PantryService
pantry_service = PantryService(self.repos)
create_items = pantry_service.check_shopping_items(create_items)
```

This is cleaner: 4 lines including import, applied once to the full batch. The `check_shopping_items` method handles the per-item logic internally.

**But there's a subtlety**: `check_shopping_items` modifies items by setting `checked=True` or reducing quantity. Items that are already `checked=True` will have their `recipe_references` cleared at line 208-209. This is correct behavior — checked items (pantry-covered) should not keep recipe references since they don't need to be purchased.

**Import placement**: Move the import to the top of the file with other service imports to avoid repeated import overhead. Add:
```python
from mealie.services.optimizer.pantry import PantryService
```
near the other imports at the top of the file.

Then in `bulk_create_items`, after line 177:
```python
# Apply pantry coverage: auto-check covered items, reduce partial quantities
create_items = PantryService(self.repos).check_shopping_items(create_items)
```

That's 1 import line + 2 lines in the method body = 3 lines total. Well within the ~10 line budget.
</description>

<subtasks>
- [ ] Add `from mealie.services.optimizer.pantry import PantryService` import to top of shopping_lists.py
- [ ] Add pantry coverage call in bulk_create_items after item consolidation (after line 177)
- [ ] Verify the import doesn't create circular dependencies
- [ ] Test: adding recipe ingredients to shopping list auto-checks pantry-covered items
</subtasks>

<acceptance>
- Shopping list items for pantry-covered ingredients (assume_enough=True or quantity sufficient) are auto-checked
- Shopping list items for partially covered ingredients have reduced quantities (deficit only)
- Items with no pantry match are completely unaffected
- Feature is non-destructive: user can uncheck auto-checked items in the UI
- Total changes to shopping_lists.py are ≤10 lines
- No circular import issues
</acceptance>

<rollback risk="high">
This modifies an upstream file that handles core shopping list functionality. If the integration causes issues:
1. Remove the import line
2. Remove the 2 lines in bulk_create_items
3. Shopping list behavior returns to pre-integration state
Keep a backup of the original file before editing.
</rollback>
</task>

### Phase 6 Checkpoint

<checkpoint phase="6">
<verification>
- [ ] Add a pantry item with food_id X, quantity 5, unit "cups"
- [ ] Add a recipe with ingredient food_id X, quantity 3 cups to a shopping list
- [ ] Verify the shopping list item is auto-checked (covered)
- [ ] Add a recipe with ingredient food_id X, quantity 8 cups to a shopping list
- [ ] Verify the shopping list item has quantity 3 (deficit: 8 - 5 = 3)
- [ ] Add a pantry item with assume_enough=True
- [ ] Verify related shopping list items are auto-checked regardless of quantity
- [ ] Add a recipe ingredient with no pantry match → item is unmodified
</verification>
<success_criteria>Shopping list integration works correctly for all coverage scenarios. Changes to upstream file are minimal (~3 lines).</success_criteria>
</checkpoint>

</phase>

## Phase 7: Frontend

<phase id="7" name="Frontend" depends="5">

### 7.1 Create pantry management page

<task id="7.1" status="pending" depends="5.3" risk="medium">
<description>
Create the pantry management page at `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue`.

**Frontend patterns** (verified from existing pages):

1. **Script setup**: Use `<script setup lang="ts">` with Vue 3 Composition API
2. **Page meta**: `definePageMeta({ middleware: ["group-only"] })` for auth
3. **SEO**: `useSeoMeta({ title: "Pantry" })`
4. **API calls**: Use `useApi()` composable or create a new composable for pantry API calls
5. **Vuetify**: Use v-data-table or v-list for the item list
6. **i18n**: Use `useI18n()` for translations (can add translation keys later; use English strings initially)

**Page functionality**:
- List all pantry items for the current household (paginated)
- "Add Item" button opens a dialog/form
- Each row shows: food name (or custom name), quantity + unit, staple badge, assume-enough indicator, expiry date
- Edit and delete actions per item
- Bulk actions (optional for v1): delete selected

**API endpoints to call**:
- `GET /api/households/optimizer/pantry` — list items
- `POST /api/households/optimizer/pantry` — create item
- `PUT /api/households/optimizer/pantry/{id}` — update item
- `DELETE /api/households/optimizer/pantry/{id}` — delete item

**Food search**: Use existing ingredient foods API for autocomplete: `GET /api/foods` or equivalent. Check existing components for food autocomplete patterns.

**Unit dropdown**: Use existing ingredient units API: `GET /api/units` or equivalent.

**Note**: The frontend infrastructure (API client, composables) may need a new composable for pantry API calls. Check if there's a pattern for creating API composables in the existing codebase.
</description>

<subtasks>
- [ ] Create `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue`
- [ ] Implement page with list/table of pantry items
- [ ] Implement add item dialog with food search, quantity, unit, assume-enough toggle
- [ ] Implement edit and delete functionality
- [ ] Create API composable for pantry CRUD if needed
- [ ] Test in browser: page loads, items display correctly
</subtasks>

<acceptance>
- Page accessible at `/g/{groupSlug}/optimizer/pantry`
- Page lists pantry items with food name, quantity, unit, and status indicators
- Add item form has food autocomplete, quantity input, unit dropdown, assume-enough toggle
- Edit and delete work correctly
- Page requires authentication (middleware)
</acceptance>
</task>

### 7.2 Create PantryItemRow component

<task id="7.2" status="pending" depends="7.1" risk="low">
<description>
Create a reusable pantry item row/card component at `frontend/app/components/optimizer/PantryItemRow.vue`.

**Component behavior**:
- Props: `item: PantryItemOut` (the pantry item data)
- Emits: `update(item)`, `delete(item)`
- Layout: [Food name] [Quantity input] [Unit dropdown] [Assume Enough checkbox] [Staple toggle] [Expiry picker] [Delete button]

**Assume Enough behavior**:
- When "Assume I have enough" checkbox is checked:
  - Quantity input becomes disabled and visually grayed out
  - Unit dropdown becomes disabled and visually grayed out
  - Show visual indicator (e.g., infinity symbol ∞ or "Always available" text)
- When unchecked: quantity and unit inputs are enabled

**Quantity input**: Accepts numeric values including decimals. Use `<v-text-field type="number" step="0.1">` or similar.

**This component can be extracted from the page component** — if the page template grows large, extract the per-item rendering into this component. If the page stays simple, this component may be merged into the page.
</description>

<subtasks>
- [ ] Create `frontend/app/components/optimizer/PantryItemRow.vue`
- [ ] Implement layout with all fields
- [ ] Implement assume-enough toggle behavior (disable/enable quantity and unit)
- [ ] Wire up emit events for update and delete
</subtasks>

<acceptance>
- Checking "Assume I have enough" disables and grays out quantity and unit fields
- Unchecking re-enables them
- Quantity accepts decimal values
- Component emits update and delete events correctly
</acceptance>
</task>

### 7.3 Add sidebar navigation for pantry

<task id="7.3" status="pending" depends="7.1" risk="medium">
<description>
Add a navigation link to the pantry page in the sidebar.

**Sidebar location** (verified): Navigation links are defined in `frontend/app/components/Layout/DefaultLayout.vue` in the `topLinks` computed property.

**Per CLAUDE.md**, the modified file is `AppSidebar.vue`, but the actual navigation data is in `DefaultLayout.vue`. Check both files — the sidebar component receives `topLink` and `secondaryLinks` as props.

**Add a new top-level item or nest under an "Optimizer" parent group**:

```typescript
{
  icon: $globals.icons.archive,  // or another suitable icon
  title: "Pantry",               // or i18n.t("optimizer.pantry")
  to: `/g/${groupSlug.value}/optimizer/pantry`,
  restricted: true,
}
```

**Placement**: After "Shopping Lists" and before "Timeline" in the topLinks array, or as a new "Optimizer" group with children.

**Important**: This modifies an upstream file. Keep the change minimal — just add the link object to the existing array.
</description>

<subtasks>
- [ ] Add pantry navigation link to sidebar in DefaultLayout.vue (or AppSidebar.vue per CLAUDE.md)
- [ ] Choose an appropriate icon from existing $globals.icons
- [ ] Verify: pantry link appears in sidebar when logged in
- [ ] Verify: clicking link navigates to /g/{groupSlug}/optimizer/pantry
</subtasks>

<acceptance>
- Pantry link visible in sidebar navigation
- Link navigates to the pantry page
- Link only visible when authenticated (restricted: true)
</acceptance>
</task>

### Phase 7 Checkpoint

<checkpoint phase="7">
<verification>
- [ ] Start frontend: `task ui`
- [ ] Navigate to pantry page via sidebar
- [ ] Create a pantry item with food, quantity, unit
- [ ] Toggle "Assume I have enough" — verify quantity/unit fields disable
- [ ] Edit an existing pantry item
- [ ] Delete a pantry item
- [ ] Verify no console errors
- [ ] Verify page works on page refresh (no SSR issues)
</verification>
<success_criteria>Frontend pantry page is fully functional. Users can manage pantry items with all CRUD operations, quantity tracking, and assume-enough toggle. Sidebar navigation works.</success_criteria>
</checkpoint>

</phase>

## Final Validation

<final_validation>
<verification>
- [ ] Backend starts without errors: `task py:postgres`
- [ ] Frontend starts without errors: `task ui`
- [ ] Alembic migration applies cleanly on fresh database
- [ ] Python linting passes: `task py:lint`
- [ ] Frontend linting passes: `task ui:lint`
- [ ] All existing tests pass: `task py:test` (no regressions)
- [ ] Frontend tests pass: `task ui:test` (no regressions)
- [ ] **End-to-end flow**: Create pantry item → Add recipe to shopping list → Verify auto-check works
- [ ] **Deficit flow**: POST /deficit with recipe_ids → Verify correct coverage report
- [ ] **Assume-enough flow**: Set assume_enough=True → Shopping list items auto-checked
- [ ] **Partial coverage flow**: Set pantry quantity less than recipe → Shopping list item quantity reduced to deficit
- [ ] Modified upstream files are minimal:
  - `mealie/routes/__init__.py` — 2 lines added (import + include_router)
  - `mealie/db/models/_all_models.py` — 1 line added (optimizer import)
  - `mealie/services/household_services/shopping_lists.py` — ~3 lines added (import + pantry check)
  - `frontend/app/components/Layout/DefaultLayout.vue` — ~5 lines added (nav link)
</verification>
<acceptance>Full pantry quantity tracking feature is operational end-to-end. All CRUD, deficit calculation, shopping list integration, and frontend management work correctly. No regressions in existing functionality. Upstream file modifications are minimal per fork isolation rules.</acceptance>
</final_validation>

## Dependency Verification Log

<dependency_log>
<dependency name="SqlAlchemyBase / BaseMixins" verified="true">
  <version>SQLAlchemy 2.0.49</version>
  <verified_via>Read mealie/db/models/_model_base.py — provides id (Integer PK), created_at, update_at columns</verified_via>
  <notes>id must be overridden with GUID type for non-integer PKs. update_at (not updated_at) is the actual column name — synonym exists.</notes>
</dependency>
<dependency name="@auto_init() decorator" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/db/models/_model_utils/auto_init.py — handles column assignment from kwargs, requires session in kwargs</verified_via>
  <notes>Used on __init__(self, **_) pattern. Handles relationship initialization automatically.</notes>
</dependency>
<dependency name="GUID type" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/db/models/_model_utils/guid.py — TypeDecorator using CHAR(32)/PostgreSQL UUID. generate() returns uuid4()</verified_via>
  <notes>Also exported from mealie.db.migration_types for Alembic migrations</notes>
</dependency>
<dependency name="HouseholdRepositoryGeneric" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/repos/repository_generic.py lines 499-517 — constructor takes (session, pk_name, Model, Schema, *, group_id, household_id)</verified_via>
  <notes>Auto-scopes queries by group_id AND household_id. Provides full CRUD methods.</notes>
</dependency>
<dependency name="AllRepositories" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/repos/repository_factory.py — cached_property pattern for all repos, PK_ID="id" constant at line 82</verified_via>
  <notes>Constructor: (session, *, group_id, household_id). Access via self.repos in controllers.</notes>
</dependency>
<dependency name="UnitConverter" verified="true">
  <version>pint (via UnitRegistry)</version>
  <verified_via>Read mealie/services/parser_services/parser_utils/unit_utils.py — can_convert(unit, to_unit) -> bool, convert(qty, unit, to_unit) -> tuple[float, Unit]</verified_via>
  <notes>Requires standard_unit field on IngredientUnit. Many custom units lack this, causing conversion_failed.</notes>
</dependency>
<dependency name="BaseCrudController" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/routes/_base/base_controllers.py — extends BaseUserController, provides self.user, self.repos, self.group_id, self.household_id, self.publish_event()</verified_via>
  <notes>Uses @controller(router) decorator pattern. self.repos auto-scoped to user's group+household.</notes>
</dependency>
<dependency name="@controller decorator" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Used in mealie/routes/households/controller_shopping_lists.py — @controller(router) on class</verified_via>
  <notes>Defined at mealie/routes/_base/controller.py. Wraps class as FastAPI dependency.</notes>
</dependency>
<dependency name="HttpRepo mixin" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Used in controller_shopping_lists.py line 110 — HttpRepo[Create, Read, Update](repo, logger)</verified_via>
  <notes>Provides get_one with 404 handling. Defined at mealie/routes/_base/mixins.py</notes>
</dependency>
<dependency name="MealieModel" verified="true">
  <version>Pydantic 2.12.5</version>
  <verified_via>Read mealie/schema/_mealie/mealie_model.py — base Pydantic model with loader_options() classmethod</verified_via>
  <notes>Has .cast() method for converting between schema types. UpdatedAtField() handles update_at alias mapping.</notes>
</dependency>
<dependency name="PaginationBase" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/schema/response/pagination.py — generic PaginationBase[DataT] with items, page, per_page, total</verified_via>
  <notes>Usage: class PantryItemPagination(PaginationBase): items: list[PantryItemOut]</notes>
</dependency>
<dependency name="ShoppingListService.bulk_create_items" verified="true">
  <version>N/A (internal)</version>
  <verified_via>Read mealie/services/household_services/shopping_lists.py lines 154-223 — integration point after line 177 (post-consolidation)</verified_via>
  <notes>Insert pantry check after consolidated_create_items assignment. ~3 lines total change.</notes>
</dependency>
</dependency_log>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should the deficit endpoint accept a meal plan ID instead of (or in addition to) a list of recipe IDs?</question>
  <impact>If yes, would need to load meal plan → extract recipe IDs → pass to deficit calc. Adds a thin wrapper endpoint.</impact>
  <default_assumption>Start with recipe_ids only; meal plan integration can be added later as a thin wrapper</default_assumption>
</question>
<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should pantry items with expired expiration_date be treated as unavailable (covered=False)?</question>
  <impact>Would change deficit calculation to treat expired items as absent. Could cause unexpected shopping list additions.</impact>
  <default_assumption>No — expiration is informational only in v1; user manages expired items manually</default_assumption>
</question>
<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>How should the UI handle items where conversion_failed=True? Show a warning icon?</question>
  <impact>UI/UX only — doesn't affect backend logic</impact>
  <default_assumption>Show a warning indicator and tooltip explaining the units are incompatible; item appears as uncovered in deficit report</default_assumption>
</question>
<question id="Q4" blocking="false" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should there be a bulk import for pantry items (e.g., from existing on_hand foods)?</question>
  <impact>Would provide migration path from boolean on_hand to quantity-tracked pantry items</impact>
  <default_assumption>Defer to Phase 4 polish; v1 requires manual entry</default_assumption>
</question>
<question id="Q5" blocking="false">
  <question>Should the route prefix be `/households/optimizer/pantry` (consistent with household-scoped routes) or `/optimizer/pantry` (as spec states)?</question>
  <impact>Affects API URL structure. All other household-scoped routes use /households/ prefix.</impact>
  <default_assumption>Use `/households/optimizer/pantry` for consistency with codebase conventions. The spec's `/optimizer/pantry` was written before verifying route patterns.</default_assumption>
</question>
<question id="Q6" blocking="false">
  <question>Should the controller file be named `controller_pantry.py` (codebase convention) or `pantry.py` (as spec states)?</question>
  <impact>File naming only — no functional difference</impact>
  <default_assumption>Use `controller_pantry.py` to match the existing convention in mealie/routes/households/</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
<resolved original_question="Independent review not performed at full depth — Gemini review performed with lite model due to capacity limits">
  <resolution>This plan includes full-depth Codex and Gemini reviews with specific architectural verification. The planning process itself serves as the independent review the spec lacked.</resolution>
</resolved>
</resolved_from_source>

## Plan Review Notes

<review_notes>
<codex_response>
Codex (GPT-5) review with focus=planning:

Dependency risks:
- "Gate deficit calculation behind `IngredientUnit.standard_unit` availability and explicitly return a 'no‑conversion' status; do not treat conversion failure as zero deficit."
- "Add a fast‑fail precheck for unit conversion support; return a per‑item warning rather than throwing or silently dropping the item."

Architectural alignment:
- "Align the pantry API with the class‑based `@controller` + `BaseCrudController` pattern to keep dependency injection and event bus behavior consistent."
- "Use `AllRepositories.cached_property` for pantry repositories to preserve lifecycle consistency and prevent per‑request repo churn."
- "Use `/households/optimizer/pantry` to preserve household scoping and authorization patterns; avoid `/optimizer/pantry` unless it is explicitly group‑wide."
- "Prefer integer PK for pantry_items unless there is a hard need for UUIDs; if UUIDs are required, ensure `PK_ID` usages and repo filters support UUIDs."

Task atomicity:
- "Split deficit calculation into separate tasks: (1) calculate deficit quantities, (2) unit conversion, (3) reporting schema formatting."
- "Treat the shopping list hook as its own task: add pantry deficit items, verify merge behavior, ensure checked/label logic remains intact."

Hidden complexity:
- "Decide up‑front whether pantry items represent a single aggregate or lots; if lots are needed, drop the unique constraint and add a lot identifier."
- "Confirm `food_id` scope compatibility; enforce household ownership on pantry rows and verify joins do not leak cross‑household food data."
- "Normalize converted units into your standard unit string and persist that, or explicitly retain the source unit for display."
</codex_response>

<gemini_response>
Gemini (lite model) review — phase readiness ratings:

Phase 1 (Database): 4/5 — "Well-defined with clear steps and acceptance criteria. Risk of Alembic migration is medium but well-mitigated with rollback instructions."
Phase 2 (Schemas): 4/5 — "Strong due to clear task definitions and actionable acceptance criteria."
Phase 3 (Repository): 4/5 — "Benefits from well-defined HouseholdRepositoryGeneric base class."
Phase 4 (Service): 4/5 — "Deficit calculation rules are detailed. Main concern is floating-point precision."
Phase 5 (Routes): 4/5 — "Comprehensive, addressing the critical deviation from spec (class-based controllers)."
Phase 6 (Shopping Integration): 3/5 — "High-risk due to modifying an upstream file. Performance concern for PantryService creation."
Phase 7 (Frontend): 4/5 — "Well-described with clear patterns. Vague on food autocomplete patterns."

Key recommendations:
- "For Task 4.1, define a tolerance for floating-point comparisons in deficit calculations (e.g., abs(recipe_qty_converted - pantry_qty_converted) <= epsilon) to prevent precision-related bugs."
- "For Task 5.1, provide an example of constructing PantryItemSave manually if the .cast() method is not guaranteed to be available or suitable."
- "For Task 6.1, ensure self.repos is correctly initialized within the ShoppingListService context such that creating PantryService(self.repos) is efficient and doesn't involve re-initializing the entire repository factory on every call to bulk_create_items."
- "For Task 7.1, reference a specific existing component that demonstrates the pattern for food item selection."

Missing tasks identified:
- Event publishing for CRUD operations (BaseCrudController provides publish_event)
- Frontend translation keys (even as placeholders)
- Explicit .cast() method verification
</gemini_response>

<agent_consensus>
  <agreement>
  Both reviewers agreed on:
  1. Class-based controller pattern is correct (matches codebase)
  2. /households/optimizer/pantry route prefix is appropriate
  3. HouseholdRepositoryGeneric + AllRepositories.cached_property is the right pattern
  4. Floating-point precision in deficit calculation needs explicit handling
  5. Unit conversion must gate on standard_unit availability
  6. Shopping list integration is the highest-risk task
  7. .cast() method usage needs clarification
  </agreement>
  <disagreements>
  1. GUID vs Integer PK: Codex suggests integer PK; however, ALL existing Mealie models with FK relationships (IngredientFoodModel, IngredientUnitModel, ShoppingListModel, etc.) use GUID primary keys. The plan correctly uses GUID to match the codebase — Codex's suggestion is rejected.
  2. Task splitting: Codex recommends splitting deficit calculation into 3 separate tasks. This is over-engineering for a single method with well-defined rules. The plan keeps it as one task with detailed subtasks — Codex's suggestion is rejected.
  3. Single lot vs multiple lots: Both flagged this, spec already decided single-lot as v1 simplification. No change needed.
  </disagreements>
  <confidence>medium-high</confidence>
</agent_consensus>

<changes_made>
Based on reviewer feedback, the following changes were made to the plan:

1. **Task 4.1 — Added floating-point tolerance**: Added `round(deficit, 4)` guidance before clamping, per both reviewers' concern about precision artifacts from pint conversion.

2. **Task 4.1 — Added standard_unit gate**: Added explicit instruction to check that both units have non-None `standard_unit` before attempting UnitConverter.can_convert(), per Codex's recommendation to "gate deficit calculation behind IngredientUnit.standard_unit availability."

3. **Task 5.1 — Clarified .cast() usage**: Added both `.cast()` and manual `PantryItemSave(**data.model_dump(), household_id=...)` construction as alternatives, per both reviewers' concern about .cast() method availability.

4. **NOT changed — GUID PK**: Kept GUID PK as-is. Codex suggested integer PK, but all existing Mealie models use GUID PKs (verified in IngredientFoodModel, ShoppingListModel, etc.). Using integer would break the codebase pattern.

5. **NOT changed — Task splitting**: Codex recommended splitting deficit calc into 3 tasks. This adds overhead without value — the deficit calculation is a single method with 6 clear rules, not 3 separate concerns.

6. **NOT changed — Phase 6 risk rating**: Gemini rated Phase 6 at 3/5. This is accurate — it's the highest-risk phase. The plan already has detailed rollback instructions. No structural change needed.

Note: Gemini thinking3 and flash models were capacity-exhausted; review performed by lite model.
</changes_made>
</review_notes>
