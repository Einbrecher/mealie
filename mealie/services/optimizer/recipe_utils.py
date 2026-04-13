from __future__ import annotations

from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient


def get_ingredients_for_recipes(
    session: Session,
    group_id: UUID4,
    recipe_ids: list[UUID4],
) -> list[RecipeIngredient]:
    """
    Batch-fetch all ingredients for the given recipe IDs in a single query.
    Returns flattened list of RecipeIngredient from all matched recipes.
    Recipes not found are silently skipped.
    """
    if not recipe_ids:
        return []

    stmt = (
        select(RecipeModel)
        .where(RecipeModel.id.in_(recipe_ids), RecipeModel.group_id == group_id)
        .options(
            selectinload(RecipeModel.recipe_ingredient)
            .selectinload(RecipeIngredientModel.food),
            selectinload(RecipeModel.recipe_ingredient)
            .selectinload(RecipeIngredientModel.unit),
        )
    )

    recipes = session.execute(stmt).unique().scalars().all()

    all_ingredients: list[RecipeIngredient] = []
    for recipe in recipes:
        for ing_model in recipe.recipe_ingredient:
            all_ingredients.append(RecipeIngredient.model_validate(ing_model))

    return all_ingredients
