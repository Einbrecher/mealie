from __future__ import annotations

from pydantic import UUID4, ConfigDict

from mealie.schema._mealie import MealieModel

_PERISHABLE_DEFAULTS = ["vegetable", "fruit", "dairy", "egg", "meat", "poultry", "fish", "seafood", "herb"]
_SHELF_STABLE_DEFAULTS = ["spice", "grain", "pasta", "canned", "dried", "frozen", "oil", "vinegar", "condiment"]


class OptimizerConfigUpdate(MealieModel):
    overlap_weight: float = 1.0
    pantry_utilization_weight: float = 0.6
    pantry_urgency_weight: float = 0.8
    protein_diversity_weight: float = 0.5
    category_balance_weight: float = 0.3
    rating_weight: float = 0.2
    slot_overlap_penalty_weight: float = 0.7
    prep_time_budget_minutes: int | None = None
    perishable_label_keywords: list[str] = _PERISHABLE_DEFAULTS
    shelf_stable_label_keywords: list[str] = _SHELF_STABLE_DEFAULTS
    expiration_warning_days: int = 3
    onboarding_completed: bool = False


class OptimizerConfigSave(OptimizerConfigUpdate):
    group_id: UUID4
    household_id: UUID4


class OptimizerConfigOut(OptimizerConfigUpdate):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    model_config = ConfigDict(from_attributes=True)
