from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import status

from app.dependencies import AuthServiceDep, PasswordManagerDep, TokenManagerDep, UserServiceDep, CurrentUserDep
from app.schemas.register_user import UserRegister
from app.schemas.response_register_user import ResponseUser


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)
"""
API роутер для аутентификации.

Этот роутер обрабатывает все запросы, связанные с аутентификацией и регистрацией пользователей.
"""

@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
    pwd_manager: PasswordManagerDep,
    tkn_manager: TokenManagerDep
):
    """
    Аутентифицирует пользователя и генерирует токены.

    Обрабатывает логин с использованием OAuth2PasswordRequestForm:
    - Проверяет учетные данные пользователя
    - Генерирует access token
    - Обновляет refresh token

    Returns:
        dict: Содержит tokens и информацию о пользователе

    Example:
        POST /api/v1/auth/login
        Body: {"username": "user@example.com", "password": "secret"}
    """
    return await auth_service.login(form_data, pwd_manager, tkn_manager)


@router.post("/register")
async def register(
    user: Annotated[UserRegister, Depends(UserRegister.as_form)],
    user_service: UserServiceDep,
    pwd_manager: PasswordManagerDep
):
    """
    Регистрирует нового пользователя.

    Создает нового пользователя в системе с:
    - Хэшированным паролем
    - Назначенной ролью по умолчанию

    Returns:
        ResponseUser: Информация о зарегистрированном пользователе

    Example:
        POST /api/v1/auth/register
        Body: {"username": "user@example.com", "password": "secret"}

    Raises:
        HTTPException: Если пользователь с таким email уже существует
    """
    new_user = await user_service.register(user, pwd_manager)

    return ResponseUser(
        login=user.username,
        message="Регистрация успешна",
        role=new_user.role.value
    )
    
