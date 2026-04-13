from __future__ import annotations

from datetime import date, datetime

from pydantic import UUID4, ConfigDict, model_validator
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from mealie.db.models.optimizer.pantry import PantryItemModel
from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField
from mealie.schema.recipe.recipe_ingredient import IngredientFood, IngredientUnit
from mealie.schema.response.pagination import PaginationBase

__all__ = [
    "PantryItemCreate",
    "PantryItemSave",
    "PantryItemUpdate",
    "PantryItemUpdateBulk",
    "PantryItemOut",
    "PantryItemPagination",
    "PantryDeficitItem",
    "PantryDeficitReport",
]


class PantryItemCreate(MealieModel):
    food_id: UUID4 | None = None
    name: str | None = None
    is_staple: bool = False
    assume_enough: bool = False
    quantity: float | None = None
    unit_id: UUID4 | None = None
    expiration_date: date | None = None

    @model_validator(mode="after")
    def validate_food_or_name(self) -> PantryItemCreate:
        """Ensure at least one of food_id or name is provided."""
        if self.food_id is None and not self.name:
            raise ValueError("At least one of food_id or name must be provided")
        return self


class PantryItemSave(PantryItemCreate):
    group_id: UUID4
    household_id: UUID4


class PantryItemUpdate(PantryItemCreate):
    id: UUID4


class PantryItemUpdateBulk(PantryItemUpdate):
    """For bulk update operations."""

    ...


class PantryItemOut(PantryItemCreate):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    food: IngredientFood | None = None
    unit: IngredientUnit | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(None)
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            joinedload(PantryItemModel.food),
            joinedload(PantryItemModel.unit),
        ]


class PantryItemPagination(PaginationBase):
    items: list[PantryItemOut]


class PantryDeficitItem(MealieModel):
    """One ingredient's deficit analysis against pantry."""

    food_id: UUID4 | None = None
    food_name: str
    recipe_quantity: float
    recipe_unit: IngredientUnit | None = None
    pantry_quantity: float | None = None
    pantry_unit: IngredientUnit | None = None
    deficit: float
    assume_enough: bool = False
    covered: bool
    conversion_failed: bool = False


class PantryDeficitReport(MealieModel):
    """Deficit analysis for a set of recipe ingredients against the household pantry."""

    items: list[PantryDeficitItem]
    uncovered_items: list[PantryDeficitItem]
    total_items: int
    covered_count: int
    coverage_percent: float
