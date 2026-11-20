from pydantic import BaseModel


class ResponseUser(BaseModel):
    login: str
    message: str
    role: str | None = None