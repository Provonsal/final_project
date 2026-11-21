from fastapi import APIRouter


router = APIRouter(
    prefix="/api",  # Все пути будут начинаться с /api
    tags=["api"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)
"""
Главный API-роутер приложения.

Этот роутер включает в себя все версии API и устанавливает общий префикс.
"""


from .v1.router import router as v1_router

router.include_router(v1_router)
