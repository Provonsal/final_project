import enum

from fastapi import Form, HTTPException
from pydantic import BaseModel

from app.models.RoleEnum import RoleEnum

# from enums.role_enum import RoleEnum
# from enums.subcription_enum import SubscriptionEnum




class UserRegister(BaseModel):
    username: str
    name: str
    password: str
    role: RoleEnum | None = RoleEnum.GUEST

    @classmethod
    def as_form(
        cls,
        username: str = Form(...),
        name: str = Form(...),
        password: str = Form(...),
        role: RoleEnum = Form(RoleEnum.GUEST),
    ) -> "UserRegister":
        return cls(username=username, name=name, password=password, role=role)