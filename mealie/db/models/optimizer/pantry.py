from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
from mealie.db.models._model_utils.auto_init import auto_init
from mealie.db.models._model_utils.guid import GUID

if TYPE_CHECKING:
    from mealie.db.models.recipe.ingredient import IngredientFoodModel, IngredientUnitModel

__all__ = ["PantryItemModel"]


class PantryItemModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "pantry_items"
    __table_args__ = (
        UniqueConstraint("household_id", "food_id", name="pantry_item_household_food_key"),
        CheckConstraint(
            "food_id IS NOT NULL OR name IS NOT NULL",
            name="pantry_item_food_or_name_check",
        ),
        CheckConstraint(
            "use_priority IN ('auto', 'high', 'low')",
            name="pantry_item_use_priority_check",
        ),
    )

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    household_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("households.id"), nullable=False, index=True)
    food_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("ingredient_foods.id"), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_staple: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assume_enough: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("ingredient_units.id"), nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    use_priority: Mapped[str] = mapped_column(String, nullable=False, default="auto", server_default="auto")

    # Relationships
    food: Mapped[IngredientFoodModel | None] = relationship(  # type: ignore
        "IngredientFoodModel", uselist=False, foreign_keys=[food_id]
    )
    unit: Mapped[IngredientUnitModel | None] = relationship(  # type: ignore
        "IngredientUnitModel", uselist=False, foreign_keys=[unit_id]
    )

    @auto_init()
    def __init__(self, **_) -> None: ...
