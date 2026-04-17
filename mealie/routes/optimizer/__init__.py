from fastapi import APIRouter

from . import controller_config, controller_pantry, controller_recipes

router = APIRouter()
router.include_router(controller_pantry.router)
router.include_router(controller_config.router)
router.include_router(controller_recipes.router)
