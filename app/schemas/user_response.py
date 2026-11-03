from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    login: str
    message: str
    role: str | None = None