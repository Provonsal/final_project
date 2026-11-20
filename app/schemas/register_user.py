
from fastapi import Form
from pydantic import BaseModel

from app.models.RoleEnum import RoleEnum





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