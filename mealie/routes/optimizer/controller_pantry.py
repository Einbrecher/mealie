from functools import cached_property

from fastapi import APIRouter, Depends
from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo
from mealie.schema.optimizer.pantry import (
    PantryDeficitReport,
    PantryItemCreate,
    PantryItemOut,
    PantryItemPagination,
    PantryItemSave,
    PantryItemUpdate,
)
from mealie.schema.response.pagination import PaginationQuery
from mealie.services.optimizer.pantry import PantryService

router = APIRouter(prefix="/households/optimizer/pantry", tags=["Optimizer: Pantry"])


@controller(router)
class PantryItemController(BaseCrudController):
    @cached_property
    def repo(self):
        return self.repos.pantry_items

    @cached_property
    def mixins(self):
        return HttpRepo[PantryItemCreate, PantryItemOut, PantryItemUpdate](
            self.repo,
            self.logger,
        )

    @cached_property
    def service(self):
        return PantryService(self.repos)

    # CRUD

    # Deficit must be before /{item_id} to avoid route conflict
    @router.post("/deficit", response_model=PantryDeficitReport)
    def calculate_deficit(self, recipe_ids: list[UUID4]):
        """Calculate pantry deficit for given recipes."""
        group_repos = AllRepositories(self.session, group_id=self.group_id, household_id=None)

        all_ingredients = []
        for recipe_id in recipe_ids:
            recipe = group_repos.recipes.get_one(recipe_id)
            if recipe and recipe.recipe_ingredient:
                all_ingredients.extend(recipe.recipe_ingredient)

        return self.service.calculate_deficit(all_ingredients)

    @router.get("", response_model=PantryItemPagination)
    def get_all(self, q: PaginationQuery = Depends()):
        response = self.repo.page_all(pagination=q, override=PantryItemOut)
        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=PantryItemOut, status_code=201)
    def create_one(self, data: PantryItemCreate):
        save_data = data.cast(PantryItemSave, group_id=self.group_id, household_id=self.household_id)
        return self.repo.create(save_data)

    @router.get("/{item_id}", response_model=PantryItemOut)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=PantryItemOut)
    def update_one(self, item_id: UUID4, data: PantryItemUpdate):
        return self.mixins.update_one(data, item_id)

    @router.delete("/{item_id}", status_code=204)
    def delete_one(self, item_id: UUID4):
        self.repo.delete(item_id)

