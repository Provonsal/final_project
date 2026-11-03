from fastapi import APIRouter
from .auth import router as auth_router


router = APIRouter(
    prefix="/v1",  # Все пути будут начинаться с /users
    tags=["v1"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

from .auth import router as auth_router
from .calendar import router as calendar_router
# from .tasks import router as tasks_router
from .teams import router as teams_router
from .users import router as users_router

router.include_router(auth_router)
router.include_router(calendar_router)
# router.include_router(tasks_router)
router.include_router(teams_router)
router.include_router(users_router)

