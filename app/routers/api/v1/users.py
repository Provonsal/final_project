from fastapi import APIRouter, status

from app.dependencies import AnyAuthDep, UserServiceDep, CurrentUserDep
from app.schemas.response_user_me import ResponseUserMe


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)
"""
API роутер для управления пользователями.

Этот роутер предоставляет эндпоинты для работы с информацией о пользователе.
"""

@router.get("/me", status_code=status.HTTP_200_OK)
async def me(current_user: AnyAuthDep, user_service: UserServiceDep):
    """
    Получает информацию о текущем авторизованном пользователе.

    Args:
        current_user (User): Текущий авторизованный пользователь
        user_service (UserService): Сервис для работы с пользователями

    Returns:
        ResponseUserMe: Информация о текущем пользователе

    Example:
        GET /api/v1/users/me
    """
    return ResponseUserMe(
        id=current_user.id,
        username=current_user.email,
        role=current_user.role.value
    )

