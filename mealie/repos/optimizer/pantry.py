from pydantic import UUID4

from mealie.db.models.optimizer.pantry import PantryItemModel
from mealie.repos.repository_generic import HouseholdRepositoryGeneric
from mealie.schema.optimizer.pantry import PantryItemOut


class RepositoryPantryItem(HouseholdRepositoryGeneric[PantryItemOut, PantryItemModel]):
    def by_food_id(self, food_id: UUID4) -> PantryItemOut | None:
        """Look up a single pantry item by food_id within the current household."""
        q = self._query().filter_by(**self._filter_builder(food_id=food_id))
        result = self.session.execute(q).unique().scalars().one_or_none()
        if not result:
            return None
        return self.schema.model_validate(result)

    def by_food_ids(self, food_ids: list[UUID4]) -> list[PantryItemOut]:
        """Look up pantry items matching any of the given food_ids."""
        if not food_ids:
            return []
        q = self._query().filter_by(**self._filter_builder()).filter(PantryItemModel.food_id.in_(food_ids))
        results = self.session.execute(q).unique().scalars().all()
        return [self.schema.model_validate(r) for r in results]
