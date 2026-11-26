from pydantic import BaseModel


class ResponseOperationResult(BaseModel):
    """
    Базовая схема для результатов операций.

    Attributes:
        message: Сообщение о результате операции
        status: Статус операции ("success" или "failure")

    Example:
        ResponseOperationResult(message="Task completed", status="success")
    """
    message: str = ""
    status: str


class ResponseOperationSuccess(ResponseOperationResult):
    """
    Схема успешной операции.

    Attributes:
        message: Сообщение об успешном завершении операции
        status: Статус операции ("success")

    Example:
        ResponseOperationSuccess()
    """
    message: str = "Operation completed successfully"
    status: str = "success"


class ResponseOperationFailure(ResponseOperationResult):
    """
    Схема неудачной операции.

    Attributes:
        message: Сообщение о неудачном выполнении операции
        status: Статус операции ("failure")

    Example:
        ResponseOperationFailure(message="Invalid input")
    """
    message: str = "Operation failed"
    status: str = "failure"