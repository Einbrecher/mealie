from fastapi import APIRouter

from . import controller_pantry

router = APIRouter()
router.include_router(controller_pantry.router)
