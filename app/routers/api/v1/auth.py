from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import status

from app.dependencies import AuthServiceDep, PasswordManagerDep, TokenManagerDep, UserServiceDep, CurrentUserDep
from app.schemas.user_register import UserRegister


router = APIRouter(
    prefix="/auth",  
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)

@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    auth_service: AuthServiceDep,
    pwd_manager: PasswordManagerDep,
    tkn_manager: TokenManagerDep
):
    
    return await auth_service.login(form_data, pwd_manager, tkn_manager)
    

@router.post("/register")
async def register(
    user: Annotated[UserRegister, Depends(UserRegister.as_form)],
    user_service: UserServiceDep,
    pwd_manager: PasswordManagerDep
):
    
    return await user_service.register(user, pwd_manager)
    
