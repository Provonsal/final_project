from fastapi import APIRouter
from .auth import router as auth_router


router = APIRouter(
    prefix="/v1",
    tags=["v1"],
    responses={404: {"description": "Not found"}}
)
"""
API роутер версии 1.

Этот роутер объединяет все версии API версии 1 и устанавливает общий префикс.
"""

from .auth import router as auth_router
from .calendar import router as calendar_router
from .teams import router as teams_router
from .users import router as users_router

router.include_router(auth_router)
router.include_router(calendar_router)
router.include_router(teams_router)
router.include_router(users_router)
