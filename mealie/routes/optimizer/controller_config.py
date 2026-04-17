from fastapi import APIRouter

from mealie.routes._base.base_controllers import BaseCrudController
from mealie.routes._base.controller import controller
from mealie.schema.optimizer.config import OptimizerConfigOut, OptimizerConfigUpdate

router = APIRouter(prefix="/households/optimizer/config", tags=["Optimizer: Config"])


@controller(router)
class OptimizerConfigController(BaseCrudController):
    @router.get("", response_model=OptimizerConfigOut, summary="Get optimizer config (creates default on first call)")
    def get_config(self):
        """Return the household's optimizer config. Creates a row with default weights on first access."""
        return self.repos.optimizer_config.get_or_create_default()

    @router.put("", response_model=OptimizerConfigOut)
    def update_config(self, data: OptimizerConfigUpdate):
        config = self.repos.optimizer_config.get_or_create_default()
        return self.repos.optimizer_config.update(config.id, data)
