from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import status

from app.dependencies import AuthServiceDep, UserServiceDep, CurrentUserDep
from app.schemas.user_register import UserRegister


router = APIRouter(
    prefix="/auth",  # Все пути будут начинаться с /users
    tags=["auth"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    auth_service: AuthServiceDep
):
    try:
        return await auth_service.login(form_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Неверный email или пароль"
        )

@router.post("/register")
async def register(
    user: Annotated[UserRegister, Depends(UserRegister.as_form)],
    user_service: UserServiceDep,
):
    try:
        return await user_service.register(user)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже существует.",
        )
