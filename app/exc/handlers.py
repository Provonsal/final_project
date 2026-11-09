from fastapi import Request
from fastapi.responses import JSONResponse
from .exceptions import AppException
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
import logging


async def app_exception_handler(request: Request, exc: AppException):
    """Обрабатывает все исключения, унаследованные от AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Перехватывает ошибки валидации Pydantic (422) и приводит их к общему формату."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации входных данных",
                "details": exc.errors(),  # Детализированная информация об ошибках
            }
        },
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Перехватывает стандартные HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            }
        },
    )

logger = logging.getLogger(__name__)

async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ловит все непредвиденные исключения, логирует их и возвращает безопасный 500."""
    logger.error("Необработанное исключение", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Внутренняя ошибка сервера",
            }
        },
    )