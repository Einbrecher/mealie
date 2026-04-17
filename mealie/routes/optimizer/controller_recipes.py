from fastapi import APIRouter

from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.schema.optimizer.recipe_projection import RecipeFoodProjectionResponse
from mealie.services.optimizer.recipe_projection import RecipeProjectionService

router = APIRouter(prefix="/households/optimizer", tags=["Optimizer: Recipes"])


@controller(router)
class OptimizerRecipeController(BaseCrudController):
    @router.get("/recipe-foods", response_model=RecipeFoodProjectionResponse)
    def get_recipe_foods(self):
        service = RecipeProjectionService(self.session, self.group_id, self.household_id)
        return service.get_all_recipe_food_projections()
