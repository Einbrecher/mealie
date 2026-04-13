from datetime import datetime
from functools import cached_property

from fastapi import APIRouter, Depends
from pydantic import UUID4

from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo
from mealie.schema.optimizer.pantry import (
    PantryDeductRequest,
    PantryDeficitReport,
    PantryDeficitRequest,
    PantryImportResult,
    PantryItemCreate,
    PantryItemOut,
    PantryItemPagination,
    PantryItemSave,
    PantryItemUpdate,
    PantryMealPlanDeficitRequest,
)
from mealie.schema.response.pagination import PaginationQuery
from mealie.services.optimizer.pantry import PantryService
from mealie.services.optimizer.recipe_utils import get_ingredients_for_recipes

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

    # All POST endpoints must be before /{item_id} to avoid route conflict

    @router.post("/deficit", response_model=PantryDeficitReport)
    def calculate_deficit(self, data: PantryDeficitRequest) -> PantryDeficitReport:
        """Calculate pantry deficit for given recipes."""
        all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, data.recipe_ids)
        return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)

    @router.post("/deficit/meal-plan", response_model=PantryDeficitReport)
    def calculate_meal_plan_deficit(self, data: PantryMealPlanDeficitRequest) -> PantryDeficitReport:
        """Calculate pantry deficit for all recipes in a meal plan date range."""
        start_dt = datetime.combine(data.start_date, datetime.min.time())
        end_dt = datetime.combine(data.end_date, datetime.max.time())
        meals = self.repos.meals.get_meals_by_date_range(start_dt, end_dt)
        recipe_ids = list({m.recipe_id for m in meals if m.recipe_id is not None})
        all_ingredients = get_ingredients_for_recipes(self.session, self.group_id, recipe_ids)
        return self.service.calculate_deficit(all_ingredients, exclude_expired=data.exclude_expired)

    @router.post("/import-on-hand", response_model=PantryImportResult)
    def import_from_on_hand(self) -> PantryImportResult:
        """Bulk import on_hand foods as pantry items."""
        imported, skipped = self.service.import_from_on_hand()
        return PantryImportResult(imported_count=imported, skipped_count=skipped)

    @router.post("/deduct", response_model=list[PantryItemOut])
    def deduct_recipe(self, data: PantryDeductRequest) -> list[PantryItemOut]:
        """Deduct recipe ingredient quantities from pantry."""
        ingredients = get_ingredients_for_recipes(self.session, self.group_id, [data.recipe_id])
        return self.service.deduct_recipe(ingredients)

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
