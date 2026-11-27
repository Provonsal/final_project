
from fastapi import Form
from pydantic import BaseModel

from app.models.RoleEnum import RoleEnum





class UserRegister(BaseModel):
    """
    Схема для регистрации нового пользователя.

    Attributes:
        username: Имя пользователя (обычно email)
        name: Отображаемое имя пользователя
        password: Пароль пользователя
        role: Роль пользователя (по умолчанию GUEST)

    Example:
        UserRegister(username="user@example.com", name="John Doe", password="password")
    """
    username: str
    name: str
    password: str

    @classmethod
    def as_form(
        cls,
        username: str = Form(...),
        name: str = Form(...),
        password: str = Form(...),
    ) -> "UserRegister":
        """
        Создаёт экземпляр UserRegister из FastAPI Form данных.

        Args:
            username: Имя пользователя
            name: Отображаемое имя пользователя
            password: Пароль пользователя
            role: Роль пользователя

        Returns:
            UserRegister: Экземпляр схемы пользователя
        """
        return cls(username=username, name=name, password=password)