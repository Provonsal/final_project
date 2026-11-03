from fastapi import APIRouter


router = APIRouter(
    prefix="/api",  # Все пути будут начинаться с /users
    tags=["api"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

from .v1.router import router as v1_router

router.include_router(v1_router)
