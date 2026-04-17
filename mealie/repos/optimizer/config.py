from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from mealie.db.models.optimizer.config import OptimizerConfigModel
from mealie.repos.repository_generic import HouseholdRepositoryGeneric
from mealie.schema.optimizer.config import OptimizerConfigOut, OptimizerConfigSave


class RepositoryOptimizerConfig(HouseholdRepositoryGeneric[OptimizerConfigOut, OptimizerConfigModel]):
    def get_or_create_default(self) -> OptimizerConfigOut:
        """Return the household's config, creating with defaults if none exists."""
        result = (
            self.session.execute(select(self.model).filter_by(household_id=self.household_id)).scalars().one_or_none()
        )

        if result:
            return self.schema.model_validate(result)

        # Create with defaults using the inherited create() method.
        save_data = OptimizerConfigSave(
            group_id=self.group_id,
            household_id=self.household_id,
        )
        try:
            return self.create(save_data)
        except IntegrityError:
            # Concurrent request already created the row — re-query
            self.session.rollback()
            result = self.session.execute(select(self.model).filter_by(household_id=self.household_id)).scalars().one()
            return self.schema.model_validate(result)
