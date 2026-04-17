from datetime import datetime

from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only, selectinload

from mealie.db.models.household.household_to_recipe import HouseholdToRecipe
from mealie.db.models.recipe.category import Category
from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.db.models.recipe.tag import Tag
from mealie.schema.optimizer.recipe_projection import RecipeFoodProjection, RecipeFoodProjectionResponse


class RecipeProjectionService:
    def __init__(self, session: Session, group_id: UUID4, household_id: UUID4) -> None:
        self.session = session
        self.group_id = group_id
        self.household_id = household_id

    def get_all_recipe_food_projections(self) -> RecipeFoodProjectionResponse:
        # Pre-fetch household-scoped last_made timestamps in a single query
        htr_stmt = select(HouseholdToRecipe.recipe_id, HouseholdToRecipe.last_made).where(
            HouseholdToRecipe.household_id == self.household_id
        )
        htr_rows = self.session.execute(htr_stmt).all()
        last_made_map: dict[UUID4, datetime | None] = {row.recipe_id: row.last_made for row in htr_rows}

        stmt = (
            select(RecipeModel)
            .where(RecipeModel.group_id == self.group_id)
            .options(
                load_only(
                    RecipeModel.id,
                    RecipeModel.slug,
                    RecipeModel.name,
                    RecipeModel.rating,
                    RecipeModel.total_time,
                ),
                selectinload(RecipeModel.recipe_ingredient).load_only(RecipeIngredientModel.food_id),
                selectinload(RecipeModel.recipe_category).load_only(Category.id),
                selectinload(RecipeModel.tags).load_only(Tag.id),
            )
        )
        recipes = self.session.execute(stmt).scalars().all()

        items = []
        unlinked_count = 0
        for recipe in recipes:
            food_ids = list({ing.food_id for ing in recipe.recipe_ingredient if ing.food_id is not None})
            if not food_ids:
                unlinked_count += 1
                continue

            household_last_made = last_made_map.get(recipe.id)

            items.append(
                RecipeFoodProjection(
                    recipe_id=recipe.id,
                    slug=recipe.slug,
                    name=recipe.name,
                    food_ids=food_ids,
                    category_ids=[cat.id for cat in recipe.recipe_category],
                    tag_ids=[tag.id for tag in recipe.tags],
                    rating=recipe.rating,
                    total_time=recipe.total_time,
                    last_made=household_last_made.isoformat() if household_last_made else None,
                )
            )

        return RecipeFoodProjectionResponse(items=items, unlinked_recipe_count=unlinked_count)
