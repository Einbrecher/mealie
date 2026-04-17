from __future__ import annotations

from pydantic import UUID4, ConfigDict

from mealie.schema._mealie import MealieModel


class RecipeFoodProjection(MealieModel):
    recipe_id: UUID4
    slug: str
    name: str
    food_ids: list[UUID4]
    category_ids: list[UUID4]
    tag_ids: list[UUID4]
    rating: float | None = None
    total_time: str | None = None
    last_made: str | None = None
    model_config = ConfigDict(from_attributes=True)


class RecipeFoodProjectionResponse(MealieModel):
    items: list[RecipeFoodProjection]
    unlinked_recipe_count: int
