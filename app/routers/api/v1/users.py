from fastapi import APIRouter, status

from app.dependencies import AnyAuthDep, UserServiceDep, CurrentUserDep
from app.schemas.response_user_me import ResponseUserMe


router = APIRouter(
    prefix="/users",  # Все пути будут начинаться с /users
    tags=["users"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

@router.get("/me", status_code=status.HTTP_200_OK)
async def me(current_user: AnyAuthDep, user_service: UserServiceDep):
    return ResponseUserMe(id=current_user.id,username=current_user.email, role=current_user.role.value)

