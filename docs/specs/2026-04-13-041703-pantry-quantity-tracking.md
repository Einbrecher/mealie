```yaml
spec_metadata:
  goal: "Extend Phase 2 Pantry Tracker to support quantity tracking for pantry items with deficit calculation against recipe requirements, and an 'Assume I have enough' toggle that bypasses quantity checking"
  constraints:
    - "All new code in optimizer/ subdirectories per fork isolation rules"
    - "No modifications to existing Mealie database tables"
    - "Must integrate with existing IngredientFoodModel, IngredientUnitModel, and UnitConverter"
    - "Shopping list integration limited to ~10 lines in shopping_lists.py (per concept doc)"
    - "Must register models/routes/repos in standard Mealie entry points (_all_models.py, routes/__init__.py, repository_factory.py)"
  non_goals:
    - "Automatic pantry deduction when cooking or completing shopping"
    - "Price tracking or cost estimation"
    - "Multi-store or multi-location pantry tracking"
    - "Barcode scanning or receipt parsing"
    - "Pantry sharing between households"
  timestamp: "2026-04-13T04:17:03"
  confidence: medium
  survey_consumed: false

current_state:
  summary: "Mealie has a boolean-only 'on_hand' mechanism via a many-to-many households_to_ingredient_foods table — no quantities. The concept doc defines a pantry_items table with quantity/unit fields but lacks an 'assume enough' flag and deficit calculation logic. All optimizer/ directories exist as empty placeholders with __init__.py files."
  relevant_files:
    - path: "mealie/db/models/recipe/ingredient.py"
      purpose: "IngredientFoodModel and IngredientUnitModel — FK targets for pantry items; households_to_ingredient_foods join table"
      reuse_potential: high
    - path: "mealie/db/models/household/household.py"
      purpose: "Household model with ingredient_foods_on_hand relationship — existing boolean on_hand mechanism"
      reuse_potential: medium
    - path: "mealie/schema/recipe/recipe_ingredient.py"
      purpose: "Pydantic schemas for foods, units, recipe ingredients — patterns for loader_options, from_attributes, quantity display"
      reuse_potential: high
    - path: "mealie/services/household_services/shopping_lists.py"
      purpose: "ShoppingListService with merge logic, UnitConverter usage — integration point for pantry auto-check"
      reuse_potential: high
    - path: "mealie/services/parser_services/parser_utils/unit_utils.py"
      purpose: "UnitConverter (pint-based) and merge_quantity_and_unit — reuse for deficit calculation unit conversion"
      reuse_potential: high
    - path: "mealie/repos/repository_factory.py"
      purpose: "AllRepositories with cached_property pattern — must add pantry repository here"
      reuse_potential: high
    - path: "mealie/repos/repository_generic.py"
      purpose: "RepositoryGeneric, GroupRepositoryGeneric, HouseholdRepositoryGeneric base classes"
      reuse_potential: high
    - path: "mealie/routes/__init__.py"
      purpose: "Top-level API router registration — must add optimizer router"
      reuse_potential: high
    - path: "mealie/db/models/_all_models.py"
      purpose: "Model registration for Alembic — must add optimizer models import"
      reuse_potential: high
    - path: "mealie/db/models/optimizer/__init__.py"
      purpose: "Empty placeholder for optimizer models"
      reuse_potential: high
  patterns_identified:
    - "HouseholdRepositoryGeneric: scoped by group_id + household_id, used for household-owned entities like shopping lists"
    - "Service-as-composition: services take AllRepositories in __init__, not BaseService inheritance (see ShoppingListService)"
    - "Schema loader_options: classmethod returning list[LoaderOption] for eager loading relationships (see IngredientFood)"
    - "auto_init decorator: SQLAlchemy models use @auto_init() on __init__ for automatic column assignment"
    - "GUID primary keys: all models use GUID type with GUID.generate default"
    - "PaginationBase: standard paginated response pattern (items: list[SchemaType])"
    - "Router registration: import module in __init__.py, call router.include_router(module.router)"

gaps:
  exists:
    - component: "IngredientFoodModel / IngredientUnitModel"
      location: "mealie/db/models/recipe/ingredient.py"
      notes: "FK targets for pantry_items.food_id and pantry_items.unit_id — use as-is"
    - component: "UnitConverter"
      location: "mealie/services/parser_services/parser_utils/unit_utils.py"
      notes: "Pint-based unit conversion with can_convert() and merge_quantity_and_unit() — reuse for deficit calculation"
    - component: "Repository and schema base classes"
      location: "mealie/repos/repository_generic.py, mealie/schema/_mealie/mealie_model.py"
      notes: "HouseholdRepositoryGeneric, MealieModel, PaginationBase — follow same patterns"
    - component: "Optimizer directory structure"
      location: "mealie/db/models/optimizer/, mealie/schema/optimizer/, etc."
      notes: "Empty __init__.py placeholders ready for implementation"
  partial:
    - component: "pantry_items table definition"
      location: "docs/concepts/mealie-fork-spec.md (lines 112-123)"
      missing: "assume_enough boolean column; food_id-or-name validation constraint; deficit calculation logic"
    - component: "Shopping list integration"
      location: "mealie/services/household_services/shopping_lists.py"
      missing: "Quantity-aware pantry checking — currently only boolean on_hand exists upstream"
  missing:
    - component: "PantryItemModel"
      rationale: "New SQLAlchemy model for pantry_items table with quantity, unit, assume_enough fields"
    - component: "Pantry Pydantic schemas"
      rationale: "CRUD schemas + deficit report schemas for API request/response"
    - component: "PantryItemRepository"
      rationale: "Data access layer with food_id lookup methods"
    - component: "PantryService"
      rationale: "Business logic for deficit calculation with unit conversion"
    - component: "Pantry API routes"
      rationale: "CRUD + deficit endpoint"
    - component: "AllRepositories.pantry_items property"
      rationale: "Repository registration following cached_property pattern"
    - component: "Alembic migration"
      rationale: "DDL for pantry_items table, indexes, and constraints"
    - component: "Frontend pantry page and item component"
      rationale: "UI for managing pantry items with quantity input and assume-enough toggle"
  integration_points:
    - location: "mealie/db/models/_all_models.py"
      connects_to: "PantryItemModel — add 'from .optimizer import *' for Alembic discovery"
    - location: "mealie/routes/__init__.py"
      connects_to: "Optimizer router — add import + include_router"
    - location: "mealie/repos/repository_factory.py:AllRepositories"
      connects_to: "RepositoryPantryItem — add cached_property"
    - location: "mealie/services/household_services/shopping_lists.py:bulk_create_items"
      connects_to: "PantryService — call to check pantry coverage during item creation"

specification:
  files:
    # ================================================================
    # Database Model
    # ================================================================
    - path: "mealie/db/models/optimizer/pantry.py"
      action: create
      purpose: "SQLAlchemy model for pantry_items table with quantity tracking and assume_enough flag"
      signature: |
        from datetime import date, datetime
        from sqlalchemy import Boolean, Date, Float, ForeignKey, String, UniqueConstraint, CheckConstraint
        from sqlalchemy.orm import Mapped, mapped_column, relationship
        from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
        from mealie.db.models._model_utils.auto_init import auto_init
        from mealie.db.models._model_utils.guid import GUID

        class PantryItemModel(SqlAlchemyBase, BaseMixins):
            __tablename__ = "pantry_items"
            __table_args__ = (
                UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key"),
                CheckConstraint(
                    "food_id IS NOT NULL OR name IS NOT NULL",
                    name="pantry_item_food_or_name_check",
                ),
            )

            id: Mapped[GUID]             # PK, GUID.generate default
            household_id: Mapped[GUID]    # FK → households.id, NOT NULL, indexed
            food_id: Mapped[GUID | None]  # FK → ingredient_foods.id, nullable, indexed
            name: Mapped[str | None]      # for items not in foods DB
            is_staple: Mapped[bool]       # default False
            assume_enough: Mapped[bool]   # default False — when True, quantity ignored, always covered
            quantity: Mapped[float | None] # nullable — null means "untracked" (boolean on_hand behavior)
            unit_id: Mapped[GUID | None]  # FK → ingredient_units.id, nullable
            expiration_date: Mapped[date | None]

            # Relationships
            food: Mapped["IngredientFoodModel | None"]   # uselist=False
            unit: Mapped["IngredientUnitModel | None"]    # uselist=False

            @auto_init()
            def __init__(self, **_) -> None: ...
      depends_on:
        - "mealie/db/models/_model_base.py"
        - "mealie/db/models/_model_utils/auto_init.py"
        - "mealie/db/models/_model_utils/guid.py"
        - "mealie/db/models/recipe/ingredient.py (IngredientFoodModel, IngredientUnitModel)"
      acceptance_criteria:
        - "Model creates pantry_items table via Alembic migration"
        - "Unique constraint prevents duplicate (household_id, food_id) pairs when food_id is not null"
        - "Check constraint requires at least one of food_id or name to be non-null"
        - "Relationships to food and unit load correctly"

    - path: "mealie/db/models/optimizer/__init__.py"
      action: modify
      purpose: "Export PantryItemModel for _all_models.py wildcard import"
      signature: |
        from .pantry import *
      depends_on:
        - "mealie/db/models/optimizer/pantry.py"
      acceptance_criteria:
        - "PantryItemModel is importable via 'from mealie.db.models.optimizer import *'"

    - path: "mealie/db/models/_all_models.py"
      action: modify
      purpose: "Register optimizer models for Alembic autogeneration"
      signature: |
        # Add line:
        from .optimizer import *
      depends_on:
        - "mealie/db/models/optimizer/__init__.py"
      acceptance_criteria:
        - "Alembic autogenerate detects PantryItemModel and generates migration"

    # ================================================================
    # Pydantic Schemas
    # ================================================================
    - path: "mealie/schema/optimizer/pantry.py"
      action: create
      purpose: "Pydantic schemas for pantry CRUD operations and deficit reporting"
      signature: |
        from datetime import date, datetime
        from pydantic import UUID4, ConfigDict, model_validator
        from sqlalchemy.orm import joinedload
        from sqlalchemy.orm.interfaces import LoaderOption
        from mealie.schema._mealie import MealieModel
        from mealie.schema._mealie.mealie_model import UpdatedAtField
        from mealie.schema.recipe.recipe_ingredient import IngredientFood, IngredientUnit
        from mealie.schema.response.pagination import PaginationBase

        class PantryItemCreate(MealieModel):
            food_id: UUID4 | None = None
            name: str | None = None
            is_staple: bool = False
            assume_enough: bool = False
            quantity: float | None = None
            unit_id: UUID4 | None = None
            expiration_date: date | None = None

            @model_validator(mode="after")
            def validate_food_or_name(self) -> "PantryItemCreate":
                """Ensure at least one of food_id or name is provided."""
                ...

            @model_validator(mode="after")
            def clear_quantity_when_assume_enough(self) -> "PantryItemCreate":
                """When assume_enough is True, quantity and unit are irrelevant — allow but ignore."""
                ...

        class PantryItemSave(PantryItemCreate):
            household_id: UUID4

        class PantryItemUpdate(PantryItemCreate):
            id: UUID4

        class PantryItemUpdateBulk(PantryItemUpdate):
            """For bulk update operations."""
            ...

        class PantryItemOut(PantryItemCreate):
            id: UUID4
            household_id: UUID4
            food: IngredientFood | None = None
            unit: IngredientUnit | None = None
            created_at: datetime | None = None
            updated_at: datetime | None = UpdatedAtField(None)
            model_config = ConfigDict(from_attributes=True)

            @classmethod
            def loader_options(cls) -> list[LoaderOption]:
                """Eager-load food and unit relationships to avoid N+1."""
                ...

        class PantryItemPagination(PaginationBase):
            items: list[PantryItemOut]

        class PantryDeficitItem(MealieModel):
            """One ingredient's deficit analysis against pantry."""
            food_id: UUID4 | None = None
            food_name: str             # display name (from food or recipe note)
            recipe_quantity: float
            recipe_unit: IngredientUnit | None = None
            pantry_quantity: float | None = None
            pantry_unit: IngredientUnit | None = None
            deficit: float             # positive = need to buy, 0 = covered
            assume_enough: bool = False
            covered: bool              # True if assume_enough, deficit <= 0, or pantry qty is null (boolean on_hand)
            conversion_failed: bool = False  # True if units incompatible, deficit calculated without conversion

        class PantryDeficitReport(MealieModel):
            """Deficit analysis for a set of recipe ingredients against the household pantry."""
            items: list[PantryDeficitItem]
            uncovered_items: list[PantryDeficitItem]  # filtered to covered=False
            total_items: int
            covered_count: int
            coverage_percent: float
      depends_on:
        - "mealie/schema/_mealie/mealie_model.py"
        - "mealie/schema/recipe/recipe_ingredient.py"
        - "mealie/schema/response/pagination.py"
      acceptance_criteria:
        - "PantryItemCreate rejects input with both food_id and name null"
        - "PantryItemOut serializes food and unit relationships from ORM"
        - "PantryDeficitReport.uncovered_items contains only items where covered=False"
        - "PantryDeficitItem.conversion_failed=True when units are incompatible"

    - path: "mealie/schema/optimizer/__init__.py"
      action: modify
      purpose: "Export pantry schemas"
      signature: |
        from .pantry import *
      depends_on:
        - "mealie/schema/optimizer/pantry.py"
      acceptance_criteria:
        - "Pantry schemas importable via 'from mealie.schema.optimizer import *'"

    # ================================================================
    # Repository
    # ================================================================
    - path: "mealie/repos/optimizer/pantry.py"
      action: create
      purpose: "Data access layer for pantry items with food-based lookups"
      signature: |
        from pydantic import UUID4
        from mealie.db.models.optimizer.pantry import PantryItemModel
        from mealie.repos.repository_generic import HouseholdRepositoryGeneric
        from mealie.schema.optimizer.pantry import PantryItemOut

        class RepositoryPantryItem(HouseholdRepositoryGeneric[PantryItemOut, PantryItemModel]):
            def by_food_id(self, food_id: UUID4) -> PantryItemOut | None:
                """Look up a single pantry item by food_id within the current household."""
                ...

            def by_food_ids(self, food_ids: list[UUID4]) -> list[PantryItemOut]:
                """Look up pantry items matching any of the given food_ids."""
                ...
      depends_on:
        - "mealie/repos/repository_generic.py"
        - "mealie/db/models/optimizer/pantry.py"
        - "mealie/schema/optimizer/pantry.py"
      acceptance_criteria:
        - "by_food_id returns None when no pantry item exists for that food"
        - "by_food_ids returns only items matching the given food IDs within the household scope"
        - "Standard CRUD operations (get_one, page_all, create, update, delete) work via inherited methods"

    - path: "mealie/repos/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer repositories"
      signature: |
        from .pantry import RepositoryPantryItem
      depends_on:
        - "mealie/repos/optimizer/pantry.py"
      acceptance_criteria:
        - "RepositoryPantryItem importable from mealie.repos.optimizer"

    - path: "mealie/repos/repository_factory.py"
      action: modify
      purpose: "Register RepositoryPantryItem as a cached_property on AllRepositories"
      signature: |
        # Add import:
        from mealie.db.models.optimizer.pantry import PantryItemModel
        from mealie.repos.optimizer.pantry import RepositoryPantryItem
        from mealie.schema.optimizer.pantry import PantryItemOut

        # Add to AllRepositories class (under Household section):
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
      depends_on:
        - "mealie/repos/optimizer/pantry.py"
        - "mealie/db/models/optimizer/pantry.py"
        - "mealie/schema/optimizer/pantry.py"
      acceptance_criteria:
        - "repos.pantry_items returns a RepositoryPantryItem scoped to the current household"
        - "Property is lazily initialized via cached_property"

    # ================================================================
    # Service
    # ================================================================
    - path: "mealie/services/optimizer/pantry.py"
      action: create
      purpose: "Business logic for pantry operations including deficit calculation with unit conversion"
      signature: |
        from pydantic import UUID4
        from mealie.repos.repository_factory import AllRepositories
        from mealie.schema.optimizer.pantry import (
            PantryDeficitItem,
            PantryDeficitReport,
            PantryItemOut,
        )
        from mealie.schema.recipe.recipe_ingredient import RecipeIngredient
        from mealie.services.parser_services.parser_utils import UnitConverter

        class PantryService:
            def __init__(self, repos: AllRepositories) -> None:
                self.repos = repos
                self.pantry_items = repos.pantry_items
                ...

            def get_pantry_map(self) -> dict[UUID4, PantryItemOut]:
                """Load all pantry items for the household, keyed by food_id."""
                ...

            def calculate_deficit(
                self,
                recipe_ingredients: list[RecipeIngredient],
                pantry_items: list[PantryItemOut] | None = None,
            ) -> PantryDeficitReport:
                """
                Compare recipe ingredient requirements against pantry inventory.

                Deficit rules:
                - assume_enough=True → covered=True, deficit=0
                - pantry quantity is None (untracked) → covered=True, deficit=0 (boolean on_hand compat)
                - pantry quantity present, units compatible → deficit = max(0, recipe_qty_converted - pantry_qty_converted)
                - pantry quantity present, units incompatible → deficit = recipe_qty, conversion_failed=True, covered=False
                - pantry quantity present, units compatible, deficit <= 0 → covered=True
                - no pantry match → deficit = recipe_qty, covered=False
                - recipe ingredient with no food_id → skip (cannot match to pantry)
                """
                ...

            def check_shopping_items(
                self,
                items: list["ShoppingListItemCreate"],
            ) -> list["ShoppingListItemCreate"]:
                """
                Adjust shopping list items based on pantry state.

                - assume_enough or fully covered → set checked=True
                - partially covered → reduce quantity to deficit
                - no pantry match → leave unchanged
                """
                ...
      depends_on:
        - "mealie/repos/repository_factory.py (AllRepositories)"
        - "mealie/repos/optimizer/pantry.py (RepositoryPantryItem)"
        - "mealie/schema/optimizer/pantry.py"
        - "mealie/schema/recipe/recipe_ingredient.py (RecipeIngredient)"
        - "mealie/services/parser_services/parser_utils/unit_utils.py (UnitConverter)"
      acceptance_criteria:
        - "calculate_deficit returns covered=True for items with assume_enough=True regardless of quantity"
        - "calculate_deficit returns covered=True for pantry items with null quantity (boolean on_hand compat)"
        - "calculate_deficit performs unit conversion via UnitConverter when both units have standard_unit"
        - "calculate_deficit sets conversion_failed=True and covered=False when units are incompatible"
        - "calculate_deficit returns deficit=0 (not negative) when pantry has surplus"
        - "check_shopping_items sets checked=True for fully covered items"
        - "check_shopping_items reduces quantity to deficit for partially covered items"

    # ================================================================
    # Routes
    # ================================================================
    - path: "mealie/routes/optimizer/pantry.py"
      action: create
      purpose: "REST API endpoints for pantry CRUD and deficit calculation"
      signature: |
        from fastapi import APIRouter, Depends
        from pydantic import UUID4
        from mealie.schema.optimizer.pantry import (
            PantryItemCreate,
            PantryItemOut,
            PantryItemPagination,
            PantryItemUpdate,
            PantryDeficitReport,
        )
        from mealie.schema.response.pagination import PaginationQuery

        router = APIRouter(prefix="/optimizer/pantry", tags=["Optimizer: Pantry"])

        # CRUD
        @router.get("", response_model=PantryItemPagination)
        def get_all_pantry_items(q: PaginationQuery = Depends()) -> PantryItemPagination: ...

        @router.post("", response_model=PantryItemOut, status_code=201)
        def create_pantry_item(data: PantryItemCreate) -> PantryItemOut: ...

        @router.get("/{item_id}", response_model=PantryItemOut)
        def get_pantry_item(item_id: UUID4) -> PantryItemOut: ...

        @router.put("/{item_id}", response_model=PantryItemOut)
        def update_pantry_item(item_id: UUID4, data: PantryItemUpdate) -> PantryItemOut: ...

        @router.delete("/{item_id}", status_code=204)
        def delete_pantry_item(item_id: UUID4) -> None: ...

        # Deficit
        @router.post("/deficit", response_model=PantryDeficitReport)
        def calculate_deficit(recipe_ids: list[UUID4]) -> PantryDeficitReport:
            """Calculate pantry deficit for given recipes. Loads recipe ingredients, runs deficit calc."""
            ...
      depends_on:
        - "mealie/schema/optimizer/pantry.py"
        - "mealie/services/optimizer/pantry.py"
        - "mealie/repos/repository_factory.py"
      acceptance_criteria:
        - "All CRUD endpoints return correct status codes (201 create, 204 delete)"
        - "GET / supports pagination and filtering (via PaginationQuery)"
        - "POST /deficit accepts recipe_ids and returns PantryDeficitReport"
        - "All endpoints require household authentication"

    - path: "mealie/routes/optimizer/__init__.py"
      action: modify
      purpose: "Register pantry router under optimizer namespace"
      signature: |
        from fastapi import APIRouter
        from . import pantry

        router = APIRouter()
        router.include_router(pantry.router)
      depends_on:
        - "mealie/routes/optimizer/pantry.py"
      acceptance_criteria:
        - "Optimizer router aggregates pantry sub-router"

    - path: "mealie/routes/__init__.py"
      action: modify
      purpose: "Register optimizer router at top-level API"
      signature: |
        # Add to imports:
        from . import optimizer
        # (existing imports: admin, app, auth, comments, explore, groups, households, ...)

        # Add after existing include_router calls:
        router.include_router(optimizer.router)
      depends_on:
        - "mealie/routes/optimizer/__init__.py"
      acceptance_criteria:
        - "Optimizer endpoints accessible at /api/optimizer/pantry/*"

    # ================================================================
    # Shopping List Integration
    # ================================================================
    - path: "mealie/services/household_services/shopping_lists.py"
      action: modify
      purpose: "Hook pantry checking into shopping list item creation flow"
      signature: |
        # In bulk_create_items or the recipe-to-shopping-list flow:
        # After items are consolidated but before DB write:

        from mealie.services.optimizer.pantry import PantryService

        # ~10 lines: instantiate PantryService, call check_shopping_items(),
        # which sets checked=True or reduces quantity for covered items
      depends_on:
        - "mealie/services/optimizer/pantry.py"
      acceptance_criteria:
        - "Shopping list items for pantry-covered ingredients are auto-checked"
        - "Shopping list items for partially covered ingredients have reduced quantities"
        - "Items with no pantry match are unaffected"
        - "Feature is non-destructive: user can uncheck auto-checked items"

    # ================================================================
    # Alembic Migration
    # ================================================================
    - path: "mealie/alembic/versions/{timestamp}_add_pantry_items_table.py"
      action: create
      purpose: "Database migration creating pantry_items table with all columns, indexes, and constraints"
      signature: |
        # Standard Alembic migration:
        # op.create_table("pantry_items",
        #   sa.Column("id", GUID(), primary_key=True),
        #   sa.Column("household_id", GUID(), sa.ForeignKey("households.id"), nullable=False, index=True),
        #   sa.Column("food_id", GUID(), sa.ForeignKey("ingredient_foods.id"), nullable=True, index=True),
        #   sa.Column("name", sa.String(), nullable=True),
        #   sa.Column("is_staple", sa.Boolean(), nullable=False, server_default="false"),
        #   sa.Column("assume_enough", sa.Boolean(), nullable=False, server_default="false"),
        #   sa.Column("quantity", sa.Float(), nullable=True),
        #   sa.Column("unit_id", GUID(), sa.ForeignKey("ingredient_units.id"), nullable=True),
        #   sa.Column("expiration_date", sa.Date(), nullable=True),
        #   sa.Column("created_at", sa.DateTime(), nullable=False),
        #   sa.Column("updated_at", sa.DateTime(), nullable=False),
        #   sa.UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key"),
        #   sa.CheckConstraint("food_id IS NOT NULL OR name IS NOT NULL", name="pantry_item_food_or_name_check"),
        # )
      depends_on:
        - "mealie/db/models/optimizer/pantry.py"
      acceptance_criteria:
        - "Migration applies cleanly on a fresh database"
        - "Migration applies cleanly on an existing database with data"
        - "Downgrade drops the table"

    # ================================================================
    # Frontend
    # ================================================================
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/pantry.vue"
      action: create
      purpose: "Pantry management page — list, add, edit, delete pantry items"
      signature: |
        <!-- Nuxt 4 page component -->
        <!-- Uses Vuetify v-data-table or v-list for pantry items -->
        <!-- "Add Item" button opens dialog with PantryItemForm -->
        <!-- Each row: food name, quantity + unit, staple badge, assume-enough indicator, expiry -->
        <!-- Inline editing or edit dialog for existing items -->
        <!-- Bulk actions: mark as staple, delete selected -->
      depends_on:
        - "frontend/app/components/optimizer/PantryItemRow.vue"
        - "API: GET/POST/PUT/DELETE /api/optimizer/pantry"
      acceptance_criteria:
        - "Page lists all pantry items for the current household"
        - "User can add a new pantry item with food search, quantity, unit, and assume-enough toggle"
        - "User can edit quantity, unit, staple status, and assume-enough for existing items"
        - "User can delete pantry items"
        - "Page is accessible from sidebar navigation"

    - path: "frontend/app/components/optimizer/PantryItemRow.vue"
      action: create
      purpose: "Individual pantry item row/card with quantity input and assume-enough toggle"
      signature: |
        <!-- Props -->
        <!-- item: PantryItemOut -->
        <!-- Emits: update, delete -->

        <!-- Layout -->
        <!-- [Food name/search] [Quantity input] [Unit dropdown] [Assume Enough checkbox] [Staple toggle] [Expiry picker] [Delete] -->

        <!-- Behavior -->
        <!-- When "Assume I have enough" is checked: -->
        <!--   - Quantity input becomes disabled and visually grayed out -->
        <!--   - Unit dropdown becomes disabled and visually grayed out -->
        <!--   - Visual indicator (e.g., infinity symbol or "Always available" text) -->
        <!-- When unchecked: quantity and unit inputs are enabled -->
      depends_on:
        - "API: ingredient_units endpoint for unit dropdown options"
        - "API: ingredient_foods endpoint for food search/autocomplete"
      acceptance_criteria:
        - "Checking 'Assume I have enough' disables and grays out quantity and unit fields"
        - "Unchecking re-enables quantity and unit fields"
        - "Quantity input accepts numeric values including decimals"
        - "Unit dropdown shows available units from the ingredient_units API"
        - "Food field supports autocomplete search against ingredient_foods API"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/db/models/recipe/ingredient.py — fully analyzed, know IngredientFoodModel/IngredientUnitModel signatures"
    - "mealie/db/models/household/household.py — fully analyzed, know Household model and on_hand relationship"
    - "mealie/schema/recipe/recipe_ingredient.py — fully analyzed, know all schema patterns including loader_options"
    - "mealie/services/household_services/shopping_lists.py — fully analyzed, know ShoppingListService patterns"
    - "mealie/services/parser_services/parser_utils/unit_utils.py — fully analyzed, know UnitConverter and merge_quantity_and_unit"
    - "mealie/repos/repository_factory.py — fully analyzed, know AllRepositories pattern"
    - "mealie/repos/repository_generic.py — fully analyzed, know RepositoryGeneric/GroupRepositoryGeneric/HouseholdRepositoryGeneric"
    - "mealie/routes/__init__.py — fully analyzed, know router registration pattern"
    - "mealie/db/models/_all_models.py — fully analyzed, know model registration pattern"
  known_patterns:
    - "HouseholdRepositoryGeneric: constructor takes (session, pk_name, Model, Schema, group_id=, household_id=)"
    - "Service composition: PantryService.__init__(repos: AllRepositories) — access repos.pantry_items, repos.ingredient_foods, etc."
    - "Schema loader_options: return [joinedload(PantryItemModel.food), joinedload(PantryItemModel.unit)]"
    - "auto_init decorator: @auto_init() on __init__ handles column assignment from kwargs"
    - "Router prefix: use prefix='/optimizer/pantry' on APIRouter, registered under /api via top-level include_router"
    - "Pagination: inherit PaginationBase, define items: list[SchemaType]"
    - "UnitConverter.can_convert(standard_unit_1, standard_unit_2): returns bool for unit compatibility check"
  decisions_made:
    - "Single pantry item per food per household: UniqueConstraint(household_id, food_id) — simpler model, user updates quantity rather than managing multiple lots"
    - "assume_enough as a boolean on pantry_items: simplest implementation, clear UI semantics, avoids overloading is_staple"
    - "Deficit clamped to 0: deficit = max(0, recipe_qty - pantry_qty) — negative values (surplus) reported as 0 deficit, not negative"
    - "Null quantity = covered: backward compatibility with boolean on_hand — if user adds item without quantity, it behaves like old on_hand"
    - "conversion_failed flag: when units are incompatible (e.g., '3 cloves' vs '50 grams'), mark as not covered rather than silently skipping"
    - "Shopping list integration via check_shopping_items: non-destructive approach that sets checked=True, user can uncheck"
  warnings:
    - "UnitConverter requires both units to have standard_unit set — many custom/unstandard units will cause conversion_failed=True"
    - "Unique constraint on (household_id, food_id) prevents multiple lots with different expiration dates — acceptable for v1 simplicity"
    - "Shopping list integration modifies upstream file (shopping_lists.py) — keep changes minimal per fork isolation rules"
    - "Frontend food search depends on existing ingredient_foods API — ensure autocomplete matches the existing foods controller pattern"

open_questions:
  - question: "Should the deficit endpoint accept a meal plan ID instead of (or in addition to) a list of recipe IDs?"
    blocking: false
    default_assumption: "Start with recipe_ids only; meal plan integration can be added later as a thin wrapper"
  - question: "Should pantry items with expired expiration_date be treated as unavailable (covered=False)?"
    blocking: false
    default_assumption: "No — expiration is informational only in v1; user manages expired items manually"
  - question: "How should the UI handle items where conversion_failed=True? Show a warning icon?"
    blocking: false
    default_assumption: "Show a warning indicator and tooltip explaining the units are incompatible; item appears as uncovered in deficit report"
  - question: "Should there be a bulk import for pantry items (e.g., from existing on_hand foods)?"
    blocking: false
    default_assumption: "Defer to Phase 4 polish; v1 requires manual entry"
  - question: "Independent review not performed at full depth — Gemini review performed with lite model due to capacity limits"
    blocking: false
    default_assumption: "Proceed with Codex feedback incorporated; recommend manual review before deep-plan"

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Verdict: CONCERNS

    Issues:
    - PantryItemModel won't be picked up by Alembic autogen unless imported in _all_models.py
    - AllRepositories has no pantry repository property — must add to repository_factory.py
    - PantryItemOut needs from_attributes config and loader_options for food/unit to avoid N+1
    - No validation constraint for food_id vs name — both could be null or both set
    - Unit conversion underspecified for missing/invalid standard_unit
    - Unique constraint on (household_id, food_id) prevents multiple lots with different expiration_date

    Recommended changes:
    - Register optimizer models/routes/services in standard entry points
    - Add pantry repo to AllRepositories as cached_property
    - Add schema config and loader_options matching recipe_ingredient.py patterns
    - Enforce "exactly one of food_id or name" via DB check constraint and Pydantic validation
    - Define explicit conversion fallback rules for incompatible units
    - Decide on single vs multiple lots per food
  gemini_rating: 4
  gemini_notes: |
    Completeness Rating: 4/5

    The specification covers the essential aspects of the feature. Scope is well-defined
    and non-goals prevent scope creep. No apparent over-engineering — assume_enough boolean
    is a lean solution.

    Missing Elements:
    - Unit conversion logic details (addressed: existing UnitConverter handles this)
    - Deficit calculation edge cases for zero/negative/fractional quantities
    - Shopping list integration granularity for partial coverage
    - Input validation rules for quantity fields

    Testability: Generally testable — deficit calculation and assume_enough logic are
    strong unit test candidates. CRUD operations testable via integration tests.

    Recommendations:
    1. Elaborate on unit conversion strategy (addressed: reuse UnitConverter)
    2. Detail deficit edge cases (addressed: deficit clamped to 0, conversion_failed flag)
    3. Clarify shopping list partial coverage behavior (addressed: reduce quantity to deficit)
    4. Define validation rules (addressed: Pydantic model_validator)

    Note: Review performed with lite model due to capacity constraints on thinking models.
  consensus: |
    Both reviewers validated the overall approach. Codex raised 6 specific architectural
    concerns, all of which have been addressed in this final spec:
    1. Model registration → added _all_models.py and optimizer/__init__.py modifications
    2. Repository registration → added AllRepositories.pantry_items cached_property
    3. Schema loader_options → specified in PantryItemOut
    4. food_id/name validation → added CheckConstraint + Pydantic model_validator
    5. Unit conversion fallback → added conversion_failed flag on PantryDeficitItem
    6. Single lot decision → documented as intentional v1 simplification

    Gemini rated 4/5 completeness with minor gaps around edge cases, which have been
    addressed with explicit deficit clamping and conversion failure handling.

    Confidence: medium — architectural approach is sound and follows codebase patterns,
    but independent deep review was limited by model capacity constraints.
```
