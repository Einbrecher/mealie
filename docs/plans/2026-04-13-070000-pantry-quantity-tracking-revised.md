# Implementation Plan: Pantry Quantity Tracking

Source: docs/specs/2026-04-13-041703-pantry-quantity-tracking.md
Revised: 2026-04-13

<plan_metadata>
  <feature>Pantry Quantity Tracking with Deficit Calculation</feature>
  <source>docs/specs/2026-04-13-041703-pantry-quantity-tracking.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>8</phases>
  <tasks>22</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Extend the Phase 2 Pantry Tracker to support quantity tracking for pantry items with deficit calculation against recipe requirements. Adds a new `pantry_items` database table with quantity/unit fields and an `assume_enough` toggle that bypasses quantity checking. Integrates with the shopping list flow to auto-check covered items or reduce quantities for partial coverage. Includes full CRUD API, deficit calculation endpoint, frontend pantry management page, and automated tests.

## Changes from Original

<revision_summary>
<change type="structural">
  Split Task 4.1 into 4.1 (PantryService + deficit calculation) and 4.2 (check_shopping_items). Reason: check_shopping_items is logically separate, only consumed by Phase 6 shopping integration, and has distinct acceptance criteria.
</change>
<change type="structural">
  Split Task 5.1 into 5.1 (CRUD endpoints) and 5.2 (deficit endpoint with recipe loading). Reason: the deficit endpoint has complex group-scoped recipe loading logic that warrants isolated implementation and testing.
</change>
<change type="added">
  Added Task 7.1 (TypeScript types + API composable). Reason: all three reviewers identified that frontend tasks cannot execute without type definitions and an API client layer. This was buried as a subtask bullet in the original 7.1.
</change>
<change type="added">
  Added Phase 8 (Testing) with two tasks: unit tests for deficit calculation and API integration tests. Reason: all reviewers flagged the total absence of test tasks despite 7 edge-case deficit rules and high-risk shopping list integration.
</change>
<change type="clarity">
  Fixed Task 1.1: `SqlAlchemyBase` defines the `id` column (Integer PK), not `BaseMixins`. Attribution corrected.
</change>
<change type="clarity">
  Fixed Task 3.2: `mealie/repos/optimizer/__init__.py` exists as an empty file (verified). Changed from "create or modify" to "modify existing."
</change>
<change type="clarity">
  Fixed Task 5.1 (now 5.1): MealieModel.cast() confirmed to support kwargs at mealie_model.py:92. Removed hedging ("If .cast() doesn't support...") — use .cast() definitively.
</change>
<change type="clarity">
  Fixed Task 7.4 (was 7.3): Sidebar navigation is in `DefaultLayout.vue` line 224 (topLinks computed property), verified. Removed contradiction with CLAUDE.md's AppSidebar.vue reference.
</change>
<change type="clarity">
  Made Task 7.3 (PantryItemRow) a committed separate component. Removed original hedging ("may be merged into the page").
</change>
<change type="dependency">
  Added explicit migration-applied gate before Phase 7 frontend work. Frontend can't validate data without the database table.
</change>
<change type="clarity">
  Added auth token acquisition guidance to Phase 5 checkpoint. Original used `curl` with `Bearer <token>` but never explained how to get a token.
</change>
<change type="removed">
  Removed Dependency Verification Log section (~60 lines). Verified patterns are integrated directly into task context blocks.
</change>
<change type="removed">
  Removed Plan Review Notes section (~85 lines). Meta-content from planning process; all actionable feedback integrated inline.
</change>
</revision_summary>

**Note**: This is the ONLY meta-section. All reviewer feedback is integrated inline into task descriptions.

## Prerequisites

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
  <verification>Verified: mealie/db/models/optimizer/__init__.py, mealie/schema/optimizer/__init__.py, mealie/repos/optimizer/__init__.py, mealie/routes/optimizer/__init__.py, mealie/services/optimizer/__init__.py — all exist as empty files</verification>
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
<context>
Create the SQLAlchemy model for the `pantry_items` table at `mealie/db/models/optimizer/pantry.py`.

**Codebase patterns** (verified):

1. **Inheritance**: `class PantryItemModel(SqlAlchemyBase, BaseMixins)` — imports from `mealie.db.models._model_base`
2. **GUID primary key override**: `SqlAlchemyBase` (not BaseMixins) defines `id` as `Integer`. You MUST override it:
   ```python
   id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
   ```
3. **Auto-init decorator**: Use `@auto_init()` from `mealie.db.models._model_utils.auto_init` on `__init__(self, **_) -> None: ...`
4. **Timestamp columns**: `SqlAlchemyBase` provides `created_at` and `update_at` (note: column name is `update_at`, NOT `updated_at` — a synonym exists). Do NOT re-declare these.
5. **Foreign keys**: Reference `households.id`, `ingredient_foods.id`, `ingredient_units.id` as strings (no model imports needed for FK strings).
6. **Relationships**: Use string-based class references to avoid circular imports:
   ```python
   food: Mapped["IngredientFoodModel | None"] = relationship("IngredientFoodModel", uselist=False, foreign_keys=[food_id])
   unit: Mapped["IngredientUnitModel | None"] = relationship("IngredientUnitModel", uselist=False, foreign_keys=[unit_id])
   ```

**Columns**: id (GUID PK), household_id (GUID FK NOT NULL indexed), food_id (GUID FK nullable indexed), name (String nullable), is_staple (Boolean default False), assume_enough (Boolean default False), quantity (Float nullable), unit_id (GUID FK nullable), expiration_date (Date nullable).

**Constraints**: `UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key")`, `CheckConstraint("food_id IS NOT NULL OR name IS NOT NULL", name="pantry_item_food_or_name_check")`.

Add `__all__ = ["PantryItemModel"]` for wildcard export.
</context>

<subtasks>
- [ ] Create file `mealie/db/models/optimizer/pantry.py`
- [ ] Define `PantryItemModel` class with all columns, constraints, and relationships
- [ ] Add `__all__` export
- [ ] Verify: `python -c "from mealie.db.models.optimizer.pantry import PantryItemModel; print(PantryItemModel.__tablename__)"`
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
<context>
Modify `mealie/db/models/optimizer/__init__.py` (currently an empty file) to export PantryItemModel via wildcard import. Set file content to:
```python
from .pantry import *
```
This enables the `from .optimizer import *` in `_all_models.py` to pick up the model.
</context>

<subtasks>
- [ ] Edit `mealie/db/models/optimizer/__init__.py` to add `from .pantry import *`
</subtasks>

<acceptance>
- `python -c "from mealie.db.models.optimizer import PantryItemModel"` succeeds
</acceptance>
</task>

### 1.3 Register optimizer models in _all_models.py

<task id="1.3" status="pending" depends="1.2" risk="low">
<context>
Add optimizer model registration to `mealie/db/models/_all_models.py` so Alembic autogenerate discovers the new table.

**Current file content** (verified):
```python
from .group import *
from .labels import *
from .recipe import *
from .server import *
from .users import *
```

**Add this line** between `.labels` and `.recipe` (alphabetical order):
```python
from .optimizer import *
```

`mealie/alembic/env.py` auto-discovers models via `import mealie.db.models._all_models`, so this single line is sufficient.
</context>

<subtasks>
- [ ] Add `from .optimizer import *` to `mealie/db/models/_all_models.py`
</subtasks>

<acceptance>
- `python -c "import mealie.db.models._all_models"` succeeds without errors
- `from .optimizer import *` line present in the file between `.labels` and `.recipe`
</acceptance>
</task>

### 1.4 Create Alembic migration

<task id="1.4" status="pending" depends="1.3" risk="medium">
<context>
Generate and verify the Alembic migration for the `pantry_items` table.

**Steps**:
1. Run `alembic revision --autogenerate -m "add pantry items table"` from the project root
2. Review the generated migration — it should use `mealie.db.migration_types.GUID()` for GUID columns (Alembic's env.py configures `user_module_prefix`)
3. Verify the migration includes:
   - All 9 data columns + `created_at` and `update_at` timestamps (from base class)
   - Indexes on household_id and food_id
   - UniqueConstraint `pantry_item_household_food_key`
   - CheckConstraint `pantry_item_food_or_name_check`
   - Foreign keys to households, ingredient_foods, ingredient_units
4. Verify the downgrade drops the table
5. For `create_table` operations, use `op.create_table()` directly (no `batch_alter_table` needed)

**Rollback**: Delete the generated migration file. Run `alembic downgrade -1` if already applied.
</context>

<subtasks>
- [ ] Run Alembic autogenerate to create migration
- [ ] Review generated migration for correctness (all columns, constraints, indexes)
- [ ] Edit migration if needed (add missing constraints, fix column types)
- [ ] Test: `alembic upgrade head` on test database
- [ ] Test: `alembic downgrade -1`
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
<gate>PantryItemModel is defined, registered for Alembic, and the migration creates the table. Database layer complete.</gate>
</checkpoint>

</phase>

## Phase 2: Schema Layer

<phase id="2" name="Schema Layer" depends="1">

### 2.1 Create Pydantic schemas for pantry CRUD and deficit reporting

<task id="2.1" status="pending" depends="1.1" risk="low">
<context>
Create Pydantic schemas at `mealie/schema/optimizer/pantry.py`.

**Codebase patterns** (verified):

1. **Base class**: `MealieModel` from `mealie.schema._mealie.mealie_model` (not Pydantic's `BaseModel`)
2. **UpdatedAtField**: From `mealie.schema._mealie.mealie_model` — handles the `update_at` to `updatedAt` alias:
   ```python
   updated_at: datetime | None = UpdatedAtField(None)
   ```
3. **loader_options**: Classmethod returning `list[LoaderOption]` for eager-loading:
   ```python
   from sqlalchemy.orm import joinedload
   from mealie.db.models.optimizer.pantry import PantryItemModel

   @classmethod
   def loader_options(cls) -> list[LoaderOption]:
       return [joinedload(PantryItemModel.food), joinedload(PantryItemModel.unit)]
   ```
4. **ConfigDict**: `model_config = ConfigDict(from_attributes=True)` on the Out schema
5. **Existing types**: `IngredientFood` and `IngredientUnit` from `mealie.schema.recipe.recipe_ingredient`
6. **PaginationBase**: From `mealie.schema.response.pagination`

**Schemas to create**:

1. `PantryItemCreate(MealieModel)` — food_id (UUID4|None), name (str|None), is_staple (bool=False), assume_enough (bool=False), quantity (float|None), unit_id (UUID4|None), expiration_date (date|None). Add `@model_validator(mode="after")` to reject when both food_id and name are None.

2. `PantryItemSave(PantryItemCreate)` — adds `household_id: UUID4` (set by controller)

3. `PantryItemUpdate(PantryItemCreate)` — adds `id: UUID4`

4. `PantryItemUpdateBulk(PantryItemUpdate)` — same as Update for now, exists for pattern consistency

5. `PantryItemOut(PantryItemCreate)` — adds id, household_id, food (IngredientFood|None), unit (IngredientUnit|None), created_at, updated_at with UpdatedAtField. Has model_config and loader_options.

6. `PantryItemPagination(PaginationBase)` — `items: list[PantryItemOut]`

7. `PantryDeficitItem(MealieModel)` — food_id (UUID4|None), food_name (str), recipe_quantity (float), recipe_unit (IngredientUnit|None), pantry_quantity (float|None), pantry_unit (IngredientUnit|None), deficit (float), assume_enough (bool=False), covered (bool), conversion_failed (bool=False)

8. `PantryDeficitReport(MealieModel)` — items (list[PantryDeficitItem]), uncovered_items (list[PantryDeficitItem]), total_items (int), covered_count (int), coverage_percent (float)

Add `__all__` listing all schema class names.
</context>

<subtasks>
- [ ] Create file `mealie/schema/optimizer/pantry.py`
- [ ] Implement PantryItemCreate with model_validator
- [ ] Implement PantryItemSave, PantryItemUpdate, PantryItemUpdateBulk
- [ ] Implement PantryItemOut with loader_options, ConfigDict, UpdatedAtField
- [ ] Implement PantryItemPagination
- [ ] Implement PantryDeficitItem and PantryDeficitReport
- [ ] Add `__all__` export
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
<context>
Modify `mealie/schema/optimizer/__init__.py` (currently empty) to export pantry schemas:
```python
from .pantry import *
```
</context>

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
<gate>All Pydantic schemas defined, validated, and importable. Ready for repository and service layers.</gate>
</checkpoint>

</phase>

## Phase 3: Repository Layer

<phase id="3" name="Repository Layer" depends="1,2">

### 3.1 Create RepositoryPantryItem

<task id="3.1" status="pending" depends="1.1,2.1" risk="low">
<context>
Create the data access layer at `mealie/repos/optimizer/pantry.py`.

**Codebase pattern** (verified at mealie/repos/repository_generic.py lines 499-517):

`HouseholdRepositoryGeneric` provides:
- Constructor: `(session, pk_name, Model, Schema, *, group_id, household_id)` — auto-scopes all queries
- Inherited CRUD: `get_one`, `page_all`, `create`, `update`, `delete`, `create_many`, `update_many`, `delete_many`
- Access `self.model` (SQLAlchemy model class), `self.schema` (Pydantic schema), `self.session` (DB session)
- `self._query()` returns a pre-filtered query with group_id + household_id applied

**Custom methods to add**:

1. `by_food_id(food_id: UUID4) -> PantryItemOut | None` — filter by food_id within household scope. Use `self.session.query(self.model).filter_by(food_id=food_id).one_or_none()`, then convert to schema.

2. `by_food_ids(food_ids: list[UUID4]) -> list[PantryItemOut]` — filter where food_id IN food_ids. Used by deficit calculation to batch-load pantry items.

```python
from mealie.repos.repository_generic import HouseholdRepositoryGeneric

class RepositoryPantryItem(HouseholdRepositoryGeneric[PantryItemOut, PantryItemModel]):
    ...
```
</context>

<subtasks>
- [ ] Create file `mealie/repos/optimizer/pantry.py`
- [ ] Implement RepositoryPantryItem with by_food_id and by_food_ids methods
- [ ] Verify: `python -c "from mealie.repos.optimizer.pantry import RepositoryPantryItem"`
</subtasks>

<acceptance>
- RepositoryPantryItem extends HouseholdRepositoryGeneric
- by_food_id returns None when no match
- by_food_ids returns list filtered by food_ids within household scope
- All standard CRUD methods available via inheritance
</acceptance>
</task>

### 3.2 Export RepositoryPantryItem from optimizer package

<task id="3.2" status="pending" depends="3.1" risk="low">
<context>
Modify the existing `mealie/repos/optimizer/__init__.py` (currently an empty file — verified) to export the repository:
```python
from .pantry import RepositoryPantryItem

__all__ = ["RepositoryPantryItem"]
```
</context>

<subtasks>
- [ ] Edit `mealie/repos/optimizer/__init__.py` to add the export
</subtasks>

<acceptance>
- `python -c "from mealie.repos.optimizer import RepositoryPantryItem"` succeeds
</acceptance>
</task>

### 3.3 Register RepositoryPantryItem in AllRepositories

<task id="3.3" status="pending" depends="3.1,3.2" risk="medium">
<context>
Add the pantry repository as a `cached_property` on `AllRepositories` in `mealie/repos/repository_factory.py`.

**Exact pattern** (verified from existing code, e.g., `group_shopping_lists`):

```python
# Add these imports near the top (with other model/repo/schema imports):
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

**PK_ID** is a constant: `PK_ID = "id"` (defined in the same file). Place the property after existing household-scoped repositories.
</context>

<subtasks>
- [ ] Add imports for PantryItemModel, RepositoryPantryItem, PantryItemOut
- [ ] Add `pantry_items` cached_property to AllRepositories class
- [ ] Verify: `python -c "from mealie.repos.repository_factory import AllRepositories; print(hasattr(AllRepositories, 'pantry_items'))"`
</subtasks>

<acceptance>
- AllRepositories has a `pantry_items` property
- Property returns RepositoryPantryItem scoped to group_id and household_id
- `python -c "from mealie.repos.repository_factory import AllRepositories"` succeeds (no import errors)
</acceptance>

<rollback risk="medium">
This modifies a critical shared file (repository_factory.py). If the edit breaks imports, remove the 3 import lines and the cached_property block. No other code references pantry_items yet.
</rollback>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `python -c "from mealie.repos.optimizer import RepositoryPantryItem"` succeeds
- [ ] `python -c "from mealie.repos.repository_factory import AllRepositories"` succeeds
- [ ] AllRepositories.pantry_items property exists
</verification>
<gate>Repository layer complete. Pantry items can be CRUD-operated via AllRepositories.pantry_items. Ready for service layer.</gate>
</checkpoint>

</phase>

## Phase 4: Service Layer

<phase id="4" name="Service Layer" depends="3">

### 4.1 Create PantryService with deficit calculation

<task id="4.1" status="pending" depends="3.3" risk="medium">
<context>
Create the business logic service at `mealie/services/optimizer/pantry.py`. Also ensure `mealie/services/optimizer/__init__.py` exists (it does — verified as empty placeholder).

**Service pattern** (verified from ShoppingListService):
- Constructor takes `repos: AllRepositories`
- Access repos via `self.repos.pantry_items`, etc.
- No base class inheritance — plain class with composition

**UnitConverter usage** (verified at mealie/services/parser_services/parser_utils/unit_utils.py):
```python
from mealie.services.parser_services.parser_utils import UnitConverter

converter = UnitConverter()
can = converter.can_convert(standard_unit_1, standard_unit_2)  # bool
new_qty, new_unit = converter.convert(quantity, from_unit, to_unit)
```
`can_convert` and `convert` accept `str | Unit` — use the unit's `standard_unit` field from IngredientUnit schema.

**Methods to implement**:

1. `__init__(self, repos: AllRepositories)` — store repos, create UnitConverter instance

2. `get_pantry_map(self) -> dict[UUID4, PantryItemOut]` — load all pantry items for household, return dict keyed by food_id (skip items with no food_id)

3. `calculate_deficit(self, recipe_ingredients: list[RecipeIngredient], pantry_items: list[PantryItemOut] | None = None) -> PantryDeficitReport`

**Deficit calculation rules** (7 cases, implement in this order):

| # | Condition | Result |
|---|-----------|--------|
| 1 | Recipe ingredient has no food_id | Skip entirely — cannot match to pantry |
| 2 | Recipe has no quantity (None or 0) | deficit=0, covered=True |
| 3 | No pantry match for food_id | deficit=recipe_qty, covered=False |
| 4 | assume_enough=True | deficit=0, covered=True |
| 5 | Pantry quantity is None (untracked) | deficit=0, covered=True (boolean on_hand compat) |
| 6 | Both have quantity, units compatible | deficit=max(0, round(recipe_converted - pantry_converted, 4)), covered=(deficit==0) |
| 7 | Both have quantity, units incompatible | deficit=recipe_qty, conversion_failed=True, covered=False |

**Critical: standard_unit gate**: Before calling `UnitConverter.can_convert()`, check that BOTH units have a non-None `standard_unit` field on their IngredientUnit. If either is None, treat as incompatible (rule 7). Passing None to `can_convert()` raises an exception.

**Floating-point tolerance**: Use `round(deficit, 4)` before clamping with `max(0, ...)` to prevent pint conversion artifacts like 2.0000000001.

**RecipeIngredient schema** (at mealie/schema/recipe/recipe_ingredient.py): fields `quantity` (float|None), `unit` (IngredientUnit|None), `food` (IngredientFood|None), `note` (str|None). Access food_id via `ingredient.food.id`.

After building all PantryDeficitItem entries, compute report fields:
- `uncovered_items = [i for i in items if not i.covered]`
- `total_items = len(items)`
- `covered_count = total_items - len(uncovered_items)`
- `coverage_percent = (covered_count / total_items * 100) if total_items > 0 else 100.0`
</context>

<subtasks>
- [ ] Ensure `mealie/services/optimizer/__init__.py` exists (should already)
- [ ] Create `mealie/services/optimizer/pantry.py`
- [ ] Implement PantryService.__init__ with repos and UnitConverter
- [ ] Implement get_pantry_map
- [ ] Implement calculate_deficit handling all 7 rules in order
- [ ] Verify: `python -c "from mealie.services.optimizer.pantry import PantryService"`
</subtasks>

<acceptance>
- PantryService importable from mealie.services.optimizer.pantry
- calculate_deficit returns covered=True for assume_enough=True items
- calculate_deficit returns covered=True for pantry items with null quantity
- calculate_deficit gates on standard_unit before calling UnitConverter
- calculate_deficit sets conversion_failed=True when units incompatible
- calculate_deficit returns deficit=0 (not negative) when pantry has surplus
- calculate_deficit skips ingredients with no food_id
- calculate_deficit returns covered=True when recipe quantity is 0 or None
</acceptance>
</task>

### 4.2 Add check_shopping_items to PantryService

<task id="4.2" status="pending" depends="4.1" risk="low">
<context>
Add the `check_shopping_items` method to `PantryService` in `mealie/services/optimizer/pantry.py`. This method is consumed by the Phase 6 shopping list integration.

**Method signature**:
```python
def check_shopping_items(
    self,
    items: list[ShoppingListItemCreate],
) -> list[ShoppingListItemCreate]:
```

Import `ShoppingListItemCreate` from `mealie.schema.household.shopping_list`.

**Logic**:
1. Load pantry map once via `self.get_pantry_map()`
2. For each item with a `food_id` that matches a pantry item:
   - If `assume_enough` or pantry `quantity is None` → set `item.checked = True`
   - If pantry has quantity and both units have `standard_unit`:
     - Use UnitConverter to check compatibility and calculate deficit
     - If deficit <= 0 → set `item.checked = True`
     - If deficit > 0 → set `item.quantity = deficit` (reduce to what's still needed)
   - If units incompatible → leave unchanged (can't determine coverage)
3. Items with no pantry match → leave unchanged
4. Return modified items list

**Important**: Access `item.food_id` for matching. `ShoppingListItemCreate` has `food_id: UUID4 | None` directly (not nested under `.food`).
</context>

<subtasks>
- [ ] Add check_shopping_items method to PantryService
- [ ] Import ShoppingListItemCreate at the top of the file
- [ ] Verify no circular import issues: `python -c "from mealie.services.optimizer.pantry import PantryService"`
</subtasks>

<acceptance>
- check_shopping_items sets checked=True for fully covered items (assume_enough or quantity sufficient)
- check_shopping_items reduces quantity to deficit for partially covered items
- check_shopping_items leaves items unchanged when no pantry match
- check_shopping_items leaves items unchanged when unit conversion fails
- No circular import errors
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] PantryService importable without errors
- [ ] `python -c "from mealie.services.optimizer.pantry import PantryService"` succeeds
- [ ] All 7 deficit rules are implemented (verify by reading the calculate_deficit method)
- [ ] check_shopping_items method exists on PantryService
</verification>
<gate>Business logic for deficit calculation and shopping item checking is complete. Ready for API routes.</gate>
</checkpoint>

</phase>

## Phase 5: API Routes

<phase id="5" name="API Routes" depends="4">

### 5.1 Create pantry controller with CRUD endpoints

<task id="5.1" status="pending" depends="4.1" risk="medium">
<context>
Create the API controller at `mealie/routes/optimizer/controller_pantry.py`.

**IMPORTANT**: The spec shows function-based route handlers, but the codebase uses **class-based controllers** with the `@controller(router)` pattern. Follow the codebase, not the spec.

**Controller pattern** (verified from mealie/routes/households/controller_shopping_lists.py):

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
    def mixins(self):
        return HttpRepo[PantryItemCreate, PantryItemOut, PantryItemUpdate](
            self.repo, self.logger,
        )
```

**BaseCrudController** (verified at mealie/routes/_base/base_controllers.py) provides:
- `self.user: PrivateUser` — authenticated user
- `self.group_id`, `self.household_id` — from user
- `self.repos: AllRepositories` — scoped to user's group+household
- `self.session`, `self.logger`, `self.publish_event()`

**Route prefix**: Use `/households/optimizer/pantry` (consistent with household-scoped routes like `/households/shopping/lists`).

**CRUD endpoints** (5 total):

1. `GET /` → PantryItemPagination — paginated list via `self.repo.page_all(pagination=q, override=PantryItemOut)`
2. `POST /` → PantryItemOut (201) — use `data.cast(PantryItemSave, household_id=self.household_id)` then `self.repo.create(save_data)`. The `.cast()` method is confirmed to support kwargs (verified at mealie_model.py:92).
3. `GET /{item_id}` → PantryItemOut — use `self.mixins.get_one(item_id)` for 404 handling
4. `PUT /{item_id}` → PantryItemOut — `self.repo.update(item_id, data)`
5. `DELETE /{item_id}` → 204 — `self.repo.delete(item_id)`
</context>

<subtasks>
- [ ] Create `mealie/routes/optimizer/controller_pantry.py`
- [ ] Implement PantryItemController class with @controller(router) decorator
- [ ] Implement all 5 CRUD endpoints
- [ ] Handle household_id injection on create via .cast()
- [ ] Verify: `python -c "from mealie.routes.optimizer.controller_pantry import router"`
</subtasks>

<acceptance>
- Controller class extends BaseCrudController with @controller(router) decorator
- GET / returns PantryItemPagination with PaginationQuery support
- POST / returns 201, injects household_id from authenticated user via .cast()
- GET /{item_id} returns 404 when not found (via HttpRepo mixin)
- PUT /{item_id} updates and returns the item
- DELETE /{item_id} returns 204
</acceptance>
</task>

### 5.2 Add deficit endpoint to controller

<task id="5.2" status="pending" depends="4.1,5.1" risk="medium">
<context>
Add the deficit calculation endpoint to the pantry controller at `mealie/routes/optimizer/controller_pantry.py`.

**Endpoint**: `POST /deficit` → PantryDeficitReport

This endpoint accepts a list of recipe IDs, loads their ingredients, and runs deficit calculation against the household pantry.

**Critical detail — recipe loading scope**: Recipes are group-scoped (shared across households), but pantry items are household-scoped. Load recipes at the group level using a separate repository instance:

```python
from mealie.repos.repository_factory import AllRepositories

# Inside the deficit endpoint method:
group_repos = AllRepositories(self.session, group_id=self.group_id, household_id=None)
# Then use group_repos to load recipes
```

This pattern is used by ShoppingListService (verified in shopping_lists.py).

**Implementation**:
```python
@router.post("/deficit", response_model=PantryDeficitReport)
def calculate_deficit(self, recipe_ids: list[UUID4]):
    from mealie.services.optimizer.pantry import PantryService
    service = PantryService(self.repos)

    # Load recipe ingredients (group-scoped)
    all_ingredients = []
    for recipe_id in recipe_ids:
        recipe = group_repos.recipes.get_one(recipe_id)
        if recipe and recipe.recipe_ingredient:
            all_ingredients.extend(recipe.recipe_ingredient)

    return service.calculate_deficit(all_ingredients)
```

**Note**: Check how recipes are accessed. The recipe repository may use a different method name. Look at existing code in shopping_lists.py for the recipe-loading pattern.
</context>

<subtasks>
- [ ] Add PantryService import and cached_property to the controller
- [ ] Add POST /deficit endpoint
- [ ] Implement group-scoped recipe loading
- [ ] Collect all recipe ingredients and pass to calculate_deficit
- [ ] Verify: endpoint appears when controller is loaded
</subtasks>

<acceptance>
- POST /deficit accepts `recipe_ids: list[UUID4]` in request body
- Loads recipes at group scope (not household scope)
- Returns PantryDeficitReport with correct coverage calculations
- Returns empty report (100% coverage) when no recipe ingredients found
- Requires authentication (via BaseCrudController)
</acceptance>
</task>

### 5.3 Register pantry controller in optimizer router

<task id="5.3" status="pending" depends="5.1,5.2" risk="low">
<context>
Modify `mealie/routes/optimizer/__init__.py` (currently empty) to aggregate the pantry controller router.

**File content** (follows pattern from mealie/routes/households/__init__.py):
```python
from fastapi import APIRouter

from . import controller_pantry

router = APIRouter()
router.include_router(controller_pantry.router)
```
</context>

<subtasks>
- [ ] Edit `mealie/routes/optimizer/__init__.py`
</subtasks>

<acceptance>
- `python -c "from mealie.routes.optimizer import router"` succeeds
- Router includes the pantry controller routes
</acceptance>
</task>

### 5.4 Register optimizer router at top-level API

<task id="5.4" status="pending" depends="5.3" risk="medium">
<context>
Add the optimizer router to `mealie/routes/__init__.py`. This is a modified upstream file — keep changes minimal.

**Current file** (verified):
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
1. Add `optimizer` to the import tuple (alphabetical: between `organizers` and `parser`)
2. Add `router.include_router(optimizer.router)` after the existing include_router calls
</context>

<subtasks>
- [ ] Add `optimizer` to the import list in `mealie/routes/__init__.py`
- [ ] Add `router.include_router(optimizer.router)` call
- [ ] Verify: `python -c "from mealie.routes import router"` succeeds
</subtasks>

<acceptance>
- Optimizer routes accessible at `/api/households/optimizer/pantry/*`
- `python -c "from mealie.routes import router"` succeeds with no import errors
- Start backend (`task py:postgres`) and verify endpoints appear at localhost:9000/docs
</acceptance>

<rollback risk="medium">
Remove the `optimizer` import and include_router line. No other changes needed.
</rollback>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] Start backend: `task py:postgres`
- [ ] API docs at localhost:9000/docs show optimizer/pantry endpoints
- [ ] **Auth token**: Log in via POST /api/auth/token with test credentials (check .env or test fixtures for default user). Use the returned access_token for subsequent requests.
- [ ] `curl -X POST localhost:9000/api/households/optimizer/pantry -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name": "Test Item"}'` returns 201
- [ ] `curl localhost:9000/api/households/optimizer/pantry -H "Authorization: Bearer $TOKEN"` returns paginated list
- [ ] All 5 CRUD operations work via API
- [ ] POST /deficit endpoint responds (even if with empty results)
</verification>
<gate>Full REST API is operational. All CRUD and deficit endpoints respond with proper authentication. Ready for shopping list integration.</gate>
</checkpoint>

</phase>

## Phase 6: Shopping List Integration

<phase id="6" name="Shopping List Integration" depends="4">

### 6.1 Hook pantry checking into ShoppingListService

<task id="6.1" status="pending" depends="4.2" risk="high">
<context>
Modify `mealie/services/household_services/shopping_lists.py` to integrate pantry checking. This is a modified upstream file — keep to ~3 lines per CLAUDE.md's ~10 line budget.

**Integration point** (verified at line 177-178 of shopping_lists.py):

After items are consolidated but before the per-item merge-with-existing loop:
```python
# Line 177:
create_items = consolidated_create_items
# Line 178:
filtered_create_items: list[ShoppingListItemCreate] = []
```

**Changes** (3 lines total):

1. Add import at top of file:
```python
from mealie.services.optimizer.pantry import PantryService
```

2. Insert after line 177 (`create_items = consolidated_create_items`), before line 178:
```python
# Apply pantry coverage: auto-check covered items, reduce partial quantities
create_items = PantryService(self.repos).check_shopping_items(create_items)
```

**Why this location**: `self.repos` is `AllRepositories` — PantryService receives it for household-scoped pantry lookups. Creating PantryService here (once per bulk_create_items call) is efficient since the pantry map is loaded once inside check_shopping_items.

**Side effect**: Items with `checked=True` (pantry-covered) will have their `recipe_references` cleared at lines 207-209. This is correct — checked items don't need purchase tracking.

**Circular import check**: `mealie.services.optimizer.pantry` imports from `mealie.repos`, `mealie.schema`, and `mealie.services.parser_services` — none of which import from `shopping_lists.py`. No circular dependency.
</context>

<subtasks>
- [ ] Add `from mealie.services.optimizer.pantry import PantryService` import at top of shopping_lists.py
- [ ] Insert pantry coverage call after line 177 (after `create_items = consolidated_create_items`)
- [ ] Verify no circular imports: `python -c "from mealie.services.household_services.shopping_lists import ShoppingListService"`
- [ ] Test: add pantry item via API, then add recipe to shopping list — verify auto-check behavior
</subtasks>

<acceptance>
- Shopping list items for pantry-covered ingredients (assume_enough=True or quantity sufficient) are auto-checked
- Shopping list items for partially covered ingredients have reduced quantities (deficit only)
- Items with no pantry match are completely unaffected
- Feature is non-destructive: user can uncheck auto-checked items in the UI
- Total changes to shopping_lists.py: 1 import line + 2 lines in method = 3 lines
- No circular import issues
</acceptance>

<rollback risk="high">
Remove the import line and the 2 lines in bulk_create_items. Shopping list behavior returns to pre-integration state. Keep the original file content backed up or use `git checkout mealie/services/household_services/shopping_lists.py`.
</rollback>
</task>

### Phase 6 Checkpoint

<checkpoint phase="6">
<verification>
- [ ] Create a pantry item via API: `POST /api/households/optimizer/pantry` with food_id X, quantity 5, unit_id for "cups"
- [ ] Add recipe with ingredient food_id X, quantity 3 cups to a shopping list
- [ ] Verify shopping list item is auto-checked (covered: 5 >= 3)
- [ ] Create another recipe with food_id X, quantity 8 cups, add to shopping list
- [ ] Verify shopping list item has quantity 3 (deficit: 8 - 5 = 3)
- [ ] Create pantry item with assume_enough=True, add related recipe to shopping list
- [ ] Verify shopping list item is auto-checked regardless of quantity
- [ ] Add recipe ingredient with no pantry match → shopping list item is unmodified
</verification>
<gate>Shopping list integration works for all coverage scenarios. Upstream file changes are minimal (3 lines).</gate>
</checkpoint>

</phase>

## Phase 7: Frontend

<phase id="7" name="Frontend" depends="5">

### 7.1 Create TypeScript types and API composable for pantry

<task id="7.1" status="pending" depends="5.4" risk="medium">
<context>
Before building the pantry page, create the TypeScript type definitions and API client composable. The frontend needs these to interact with the backend API.

**Discovery steps** (the executing agent should explore these):
1. Find where existing TypeScript types/interfaces are defined. Check `frontend/app/lib/api/types/` or `frontend/app/types/` or similar.
2. Find how existing API composables are structured. Check `frontend/app/composables/api/` or how `useApi()` is set up. Look at how shopping list API calls are made for a comparable pattern.
3. Check if the project auto-generates TypeScript types from the OpenAPI schema (look for codegen scripts in package.json or Taskfile).

**Types to define** (matching backend schemas):
- `PantryItemCreate` — matches backend PantryItemCreate fields
- `PantryItemOut` — matches backend PantryItemOut fields
- `PantryItemUpdate` — matches backend PantryItemUpdate fields
- `PantryItemPagination` — paginated response
- `PantryDeficitItem` — deficit analysis per ingredient
- `PantryDeficitReport` — full deficit report

**API composable** should expose:
- `getAll(params?)` → GET /api/households/optimizer/pantry
- `createOne(data)` → POST /api/households/optimizer/pantry
- `getOne(id)` → GET /api/households/optimizer/pantry/{id}
- `updateOne(id, data)` → PUT /api/households/optimizer/pantry/{id}
- `deleteOne(id)` → DELETE /api/households/optimizer/pantry/{id}
- `calculateDeficit(recipeIds)` → POST /api/households/optimizer/pantry/deficit

Follow whatever pattern the existing codebase uses (direct fetch, axios wrapper, auto-generated client, etc.).
</context>

<subtasks>
- [ ] Explore frontend codebase to find type definition and API composable patterns
- [ ] Create TypeScript interfaces matching backend schemas
- [ ] Create API composable with all 6 endpoint methods
- [ ] Verify: types and composable import without TypeScript errors
</subtasks>

<acceptance>
- TypeScript interfaces exist for PantryItemCreate, PantryItemOut, PantryItemUpdate, PantryDeficitReport
- API composable has methods for all 6 endpoints
- Composable follows the existing codebase pattern (not a custom one-off)
- `task ui:lint` passes with the new files
</acceptance>
</task>

### 7.2 Create pantry management page

<task id="7.2" status="pending" depends="7.1" risk="medium">
<context>
Create the pantry management page at `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue`.

**Frontend patterns** (verified from existing pages):
1. `<script setup lang="ts">` with Vue 3 Composition API
2. `definePageMeta({ middleware: ["group-only"] })` for auth
3. `useSeoMeta({ title: "Pantry" })`
4. Use Vuetify components (v-data-table or v-list for items)
5. Use `useI18n()` — start with English strings, translation keys can be added later

**Page functionality**:
- List all pantry items (paginated) using the API composable from task 7.1
- "Add Item" button opens a dialog/form
- Each row shows: food name (or custom name), quantity + unit, staple badge, assume-enough indicator, expiry date
- Edit and delete actions per item
- Use the PantryItemRow component (task 7.3) for item rendering

**Prerequisite**: Migration must be applied and backend running for the page to fetch data.
</context>

<subtasks>
- [ ] Create `frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue`
- [ ] Implement page with list/table of pantry items using composable
- [ ] Implement "Add Item" dialog with food search, quantity, unit, assume-enough toggle
- [ ] Implement edit and delete functionality
- [ ] Test in browser: page loads, items display correctly
</subtasks>

<acceptance>
- Page accessible at `/g/{groupSlug}/optimizer/pantry`
- Page lists pantry items with food name, quantity, unit, and status indicators
- Add item form has food autocomplete, quantity input, unit dropdown, assume-enough toggle
- Edit and delete work correctly
- Page requires authentication (middleware)
- No console errors on load or interaction
</acceptance>
</task>

### 7.3 Create PantryItemRow component

<task id="7.3" status="pending" depends="7.1" risk="low">
<context>
Create a reusable pantry item display/edit component at `frontend/app/components/optimizer/PantryItemRow.vue`.

**Component interface**:
- Props: `item: PantryItemOut`
- Emits: `update(item)`, `delete(item)`

**Layout**: [Food name/search] [Quantity input] [Unit dropdown] [Assume Enough checkbox] [Staple toggle] [Expiry picker] [Delete button]

**Assume Enough behavior**:
- When checked: quantity and unit inputs become disabled and visually grayed out. Show indicator (infinity symbol or "Always available" text).
- When unchecked: quantity and unit inputs are enabled.

**Food autocomplete**: Use existing ingredient foods API (find the endpoint by checking how other components search foods — look for `ingredient_foods` or `/api/foods` usage in the frontend).

**Unit dropdown**: Use existing ingredient units API (find via similar pattern search).

**Quantity input**: `<v-text-field type="number" step="0.1">` or equivalent Vuetify numeric input.
</context>

<subtasks>
- [ ] Create `frontend/app/components/optimizer/PantryItemRow.vue`
- [ ] Implement layout with all fields
- [ ] Implement assume-enough toggle (disable/enable quantity and unit)
- [ ] Wire up emit events for update and delete
- [ ] Find and use existing food autocomplete and unit dropdown patterns
</subtasks>

<acceptance>
- Checking "Assume I have enough" disables and grays out quantity and unit fields
- Unchecking re-enables them
- Quantity accepts decimal values
- Component emits update and delete events correctly
- Food field supports autocomplete from existing foods API
- Unit dropdown shows available units
</acceptance>
</task>

### 7.4 Add sidebar navigation for pantry

<task id="7.4" status="pending" depends="7.2" risk="medium">
<context>
Add a navigation link to the pantry page in the sidebar.

**Sidebar location** (verified): Navigation links are defined in `frontend/app/components/Layout/DefaultLayout.vue` in the `topLinks` computed property at line 224. The `AppSidebar.vue` component receives these as props — do NOT modify AppSidebar.vue.

**Current topLinks order** (verified at DefaultLayout.vue lines 224-265):
1. Recipes
2. Recipe Finder
3. Meal Planner
4. Shopping Lists
5. Timeline
6. Cookbooks
7. Organizers

**Add a Pantry entry** after "Shopping Lists" (item 4) and before "Timeline" (item 5):
```typescript
{
  icon: $globals.icons.archive,  // or find a suitable pantry/inventory icon in $globals.icons
  title: "Pantry",
  to: `/g/${groupSlug.value}/optimizer/pantry`,
  restricted: true,
},
```

**This modifies an upstream file** — keep the change to just adding this one object to the array.

**Note**: CLAUDE.md lists `AppSidebar.vue` as the modified upstream file for nav links, but the actual data is in `DefaultLayout.vue`. The CLAUDE.md entry should be updated to reference `DefaultLayout.vue` (or both files noted).
</context>

<subtasks>
- [ ] Add pantry navigation link to topLinks in DefaultLayout.vue (after Shopping Lists)
- [ ] Choose an appropriate icon from `$globals.icons`
- [ ] Verify: pantry link appears in sidebar when logged in
- [ ] Verify: clicking link navigates to /g/{groupSlug}/optimizer/pantry
</subtasks>

<acceptance>
- Pantry link visible in sidebar between Shopping Lists and Timeline
- Link navigates to the pantry page
- Link only visible when authenticated (restricted: true)
- No other sidebar items affected
</acceptance>
</task>

### Phase 7 Checkpoint

<checkpoint phase="7">
<verification>
- [ ] Start frontend: `task ui`
- [ ] Navigate to pantry page via sidebar link
- [ ] Create a pantry item with food, quantity, unit
- [ ] Toggle "Assume I have enough" — verify quantity/unit fields disable
- [ ] Edit an existing pantry item
- [ ] Delete a pantry item
- [ ] Verify no console errors
- [ ] Verify page works on page refresh (no SSR/hydration issues)
</verification>
<gate>Frontend pantry page is fully functional with CRUD, quantity tracking, and assume-enough toggle. Sidebar navigation works.</gate>
</checkpoint>

</phase>

## Phase 8: Testing

<phase id="8" name="Testing" depends="4,5">

### 8.1 Unit tests for PantryService deficit calculation

<task id="8.1" status="pending" depends="4.1" risk="low">
<context>
Write unit tests for the deficit calculation logic. This is the core business logic with 7 edge-case rules — the highest-value test target in this feature.

**Discovery**: Find the test directory structure and patterns. Check:
- `tests/` directory for existing test organization
- How services are tested (look for tests of ShoppingListService or other services)
- How test fixtures, database sessions, and factories work
- Whether tests use real database fixtures or mocks

**Test file**: Create at an appropriate location following the codebase convention (likely `tests/unit_tests/services_tests/optimizer/` or similar).

**Test cases** (one per deficit rule):

1. `test_deficit_skips_ingredients_without_food_id` — ingredient with no food → not in report
2. `test_deficit_zero_when_recipe_has_no_quantity` — recipe qty=None or 0 → covered=True, deficit=0
3. `test_deficit_full_when_no_pantry_match` — no pantry item for food → deficit=recipe_qty, covered=False
4. `test_deficit_zero_when_assume_enough` — assume_enough=True → covered=True, deficit=0 regardless of qty
5. `test_deficit_zero_when_pantry_untracked` — pantry qty=None → covered=True, deficit=0 (boolean compat)
6. `test_deficit_calculated_with_unit_conversion` — both have qty + compatible units → deficit=max(0, recipe-pantry)
7. `test_deficit_when_units_incompatible` — incompatible units → conversion_failed=True, covered=False
8. `test_deficit_surplus_clamped_to_zero` — pantry > recipe → deficit=0, not negative
9. `test_deficit_report_aggregation` — verify total_items, covered_count, coverage_percent, uncovered_items

Also test check_shopping_items:
10. `test_shopping_items_checked_when_covered` — covered item → checked=True
11. `test_shopping_items_reduced_when_partial` — partial coverage → qty reduced to deficit
12. `test_shopping_items_unchanged_when_no_match` — no pantry match → unchanged
</context>

<subtasks>
- [ ] Explore test directory structure and patterns
- [ ] Create test file at appropriate location
- [ ] Implement all 12 test cases
- [ ] Run: `task py:test` (or pytest with the specific test file)
- [ ] Verify all tests pass
</subtasks>

<acceptance>
- All 12 test cases exist and pass
- Tests cover all 7 deficit calculation rules plus surplus clamping
- Tests cover check_shopping_items for covered, partial, and unmatched scenarios
- `task py:test` passes with no regressions
</acceptance>
</task>

### 8.2 API integration tests for pantry endpoints

<task id="8.2" status="pending" depends="5.4" risk="low">
<context>
Write integration tests for the pantry API endpoints. These test the full request/response cycle including authentication, serialization, and database operations.

**Discovery**: Find the integration test patterns. Check:
- `tests/integration_tests/` for existing API test patterns
- How test clients are created (likely TestClient from FastAPI)
- How authentication is handled in tests (test user fixtures)
- How database fixtures are managed (test database, cleanup)

**Test file**: Create at appropriate location (likely `tests/integration_tests/routes_tests/optimizer/` or similar).

**Test cases**:
1. `test_create_pantry_item` — POST / with valid data returns 201 + PantryItemOut
2. `test_create_pantry_item_validation` — POST / with both food_id and name null returns 422
3. `test_get_all_pantry_items` — GET / returns paginated list
4. `test_get_one_pantry_item` — GET /{id} returns item
5. `test_get_one_not_found` — GET /{invalid_id} returns 404
6. `test_update_pantry_item` — PUT /{id} updates and returns item
7. `test_delete_pantry_item` — DELETE /{id} returns 204, item no longer accessible
8. `test_deficit_calculation` — POST /deficit with recipe_ids returns PantryDeficitReport
9. `test_household_isolation` — items from household A not visible to household B
</context>

<subtasks>
- [ ] Explore integration test patterns in the codebase
- [ ] Create test file at appropriate location
- [ ] Implement all 9 test cases
- [ ] Run tests and verify all pass
- [ ] Verify no regressions: `task py:test`
</subtasks>

<acceptance>
- All 9 test cases exist and pass
- Tests use existing test infrastructure (client, fixtures, auth)
- Tests verify correct HTTP status codes for all operations
- Tests verify household isolation (items scoped to household)
- `task py:test` passes with no regressions
</acceptance>
</task>

### Phase 8 Checkpoint

<checkpoint phase="8">
<verification>
- [ ] `task py:test` passes — all new tests pass, no regressions
- [ ] Unit tests cover all 7 deficit rules + surplus clamping + check_shopping_items
- [ ] Integration tests cover all CRUD + deficit + household isolation
</verification>
<gate>Automated test coverage validates core business logic and API layer. Feature is regression-safe.</gate>
</checkpoint>

</phase>

## Risk Mitigation

<risks>
<risk id="R1" likelihood="low" impact="high">
  <description>Shopping list integration (Task 6.1) breaks existing shopping list functionality</description>
  <mitigation>Changes are 3 lines in upstream file. PantryService.check_shopping_items is additive — it only modifies items that match pantry entries, leaving others untouched. Rollback is simple: remove 3 lines.</mitigation>
  <detection>Existing shopping list tests fail (`task py:test`). Manual test: add recipe to shopping list without any pantry items — behavior should be identical to pre-integration.</detection>
</risk>
<risk id="R2" likelihood="medium" impact="medium">
  <description>Unit conversion fails silently or produces wrong results for many ingredient/unit combinations</description>
  <mitigation>Standard_unit gate: never call UnitConverter without checking both units have standard_unit. Set conversion_failed=True flag for transparency. Many custom units won't have standard_unit — this is expected and visible to the user.</mitigation>
  <detection>PantryDeficitItem.conversion_failed=True in deficit reports. Unit tests (8.1) validate conversion paths.</detection>
</risk>
<risk id="R3" likelihood="low" impact="medium">
  <description>Circular import between optimizer service and shopping list service</description>
  <mitigation>Shopping list imports PantryService (one direction only). PantryService imports from repos/schema/parser_utils — none of which import from shopping_lists. Verified: no circular path exists.</mitigation>
  <detection>`python -c "from mealie.services.household_services.shopping_lists import ShoppingListService"` fails with ImportError.</detection>
</risk>
<risk id="R4" likelihood="medium" impact="low">
  <description>Alembic migration conflicts with upstream migrations during next sync</description>
  <mitigation>Migration only creates a new table (no ALTER on existing tables). Conflicts would be in the `down_revision` chain only — resolvable by updating the revision pointer.</mitigation>
  <detection>Alembic reports "multiple heads" after upstream merge. Fix: `alembic merge heads`.</detection>
</risk>
<risk id="R5" likelihood="low" impact="medium">
  <description>Frontend TypeScript types drift from backend schemas</description>
  <mitigation>If the codebase has auto-generation from OpenAPI, use it. If manual, keep types in sync by referencing the backend Pydantic schemas directly when creating TS interfaces.</mitigation>
  <detection>API responses fail to match TypeScript types at runtime. `task ui:lint` catches type errors if strict mode is on.</detection>
</risk>
</risks>

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
- [ ] **Partial coverage flow**: Set pantry quantity < recipe → Shopping list item quantity reduced to deficit
- [ ] **Conversion failure**: Use incompatible units → conversion_failed=True, item uncovered
- [ ] Modified upstream files are minimal:
  - `mealie/routes/__init__.py` — 2 lines (import + include_router)
  - `mealie/db/models/_all_models.py` — 1 line (optimizer import)
  - `mealie/repos/repository_factory.py` — ~8 lines (imports + cached_property)
  - `mealie/services/household_services/shopping_lists.py` — 3 lines (import + pantry check)
  - `frontend/app/components/Layout/DefaultLayout.vue` — ~5 lines (nav link)
</verification>
<acceptance>Full pantry quantity tracking feature is operational end-to-end. All CRUD, deficit calculation, shopping list integration, and frontend management work correctly. Automated tests pass. No regressions in existing functionality. Upstream file modifications are minimal per fork isolation rules.</acceptance>
</final_validation>

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should the deficit endpoint accept a meal plan ID instead of (or in addition to) a list of recipe IDs?</question>
  <default_assumption>Start with recipe_ids only; meal plan integration can be added later as a thin wrapper that extracts recipe IDs from the plan.</default_assumption>
  <impact>If yes, adds one additional endpoint or parameter. No architectural change needed.</impact>
</question>
<question id="Q2" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should pantry items with expired expiration_date be treated as unavailable (covered=False)?</question>
  <default_assumption>No — expiration is informational only in v1. User manages expired items manually.</default_assumption>
  <impact>Would change deficit calculation rule 5 to also check expiration. Could cause unexpected shopping list additions if items expire.</impact>
</question>
<question id="Q3" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>How should the UI handle items where conversion_failed=True?</question>
  <default_assumption>Show a warning indicator (icon + tooltip) explaining units are incompatible. Item appears as uncovered in deficit report.</default_assumption>
  <impact>UI/UX only — no backend logic change.</impact>
</question>
<question id="Q4" blocking="false" owner="human" inherited_from="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
  <question>Should there be a bulk import for pantry items (e.g., from existing on_hand foods)?</question>
  <default_assumption>Defer to a later phase. V1 requires manual entry.</default_assumption>
  <impact>Would provide migration path from boolean on_hand to quantity-tracked pantry items. Useful but not blocking.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-13-041703-pantry-quantity-tracking.md">
<resolved original_question="Independent review not performed at full depth — Gemini review performed with lite model due to capacity limits">
  <resolution>This revision includes full-depth Codex (GPT-5) structural review and independent Claude agent review with codebase verification. All architectural concerns from the original spec reviews have been addressed and integrated.</resolution>
</resolved>
</resolved_from_source>

<resolved_from_source source="docs/plans/2026-04-13-050000-pantry-quantity-tracking.md">
<resolved original_question="Q5: Should the route prefix be /households/optimizer/pantry or /optimizer/pantry?">
  <resolution>Use `/households/optimizer/pantry`. Verified: all household-scoped routes in the codebase use the `/households/` prefix (e.g., `/households/shopping/lists`). The spec's `/optimizer/pantry` was written before verifying route patterns.</resolution>
</resolved>
<resolved original_question="Q6: Should the controller file be named controller_pantry.py or pantry.py?">
  <resolution>Use `controller_pantry.py`. Verified: all controller files in `mealie/routes/households/` use the `controller_` prefix convention.</resolution>
</resolved>
</resolved_from_source>
