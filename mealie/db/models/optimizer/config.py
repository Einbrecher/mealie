from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
from mealie.db.models._model_utils.auto_init import auto_init
from mealie.db.models._model_utils.guid import GUID

__all__ = ["OptimizerConfigModel"]

_PERISHABLE_DEFAULTS = ["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"]
_SHELF_STABLE_DEFAULTS = ["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]


class OptimizerConfigModel(SqlAlchemyBase, BaseMixins):
    __tablename__ = "optimizer_config"
    __table_args__ = (UniqueConstraint("household_id", name="optimizer_config_household_key"),)

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    group_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    household_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("households.id"), nullable=False, index=True)

    # Scoring weights
    overlap_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    pantry_utilization_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.6, server_default="0.6")
    pantry_urgency_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.8, server_default="0.8")
    protein_diversity_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    category_balance_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.3, server_default="0.3")
    rating_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2, server_default="0.2")
    slot_overlap_penalty_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, server_default="0.7")

    # Optional prep time budget
    prep_time_budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Configurable label classification keywords (JSON arrays)
    perishable_label_keywords: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: list(_PERISHABLE_DEFAULTS),
        server_default='["vegetable","fruit","dairy","egg","meat","poultry","fish","seafood","herb"]',
    )
    shelf_stable_label_keywords: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: list(_SHELF_STABLE_DEFAULTS),
        server_default='["spice","grain","pasta","canned","dried","frozen","oil","vinegar","condiment"]',
    )

    expiration_warning_days: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    @auto_init()
    def __init__(self, **_) -> None: ...
