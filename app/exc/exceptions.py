# app/error_handlers/exceptions.py
from typing import Any, Dict, Optional

class AppException(Exception):
    """Базовое исключение для всех ошибок приложения."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class NotFoundError(AppException):
    """Ресурс не найден."""
    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} с ID {resource_id} не найден",
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "resource_id": str(resource_id)},
        )

class BusinessRuleError(AppException):
    """Нарушено бизнес-правило."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422, error_code="BUSINESS_RULE_VIOLATION")

class AuthorizationError(AppException):
    """Ошибка авторизации."""
    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(message=message, status_code=403, error_code="FORBIDDEN")

class WrongInputError(AppException):
    """Ошибка ввода данных."""
    def __init__(self, message: str = "Неверные входные данные"):
        super().__init__(message=message, status_code=400, error_code="BAD_REQUEST")