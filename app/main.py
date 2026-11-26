from contextlib import asynccontextmanager
import os

from sqlalchemy.exc import NoResultFound

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.exc.exceptions import AppException
from app.exc.handlers import app_exception_handler, db_not_found_exception_handler, http_exception_handler, unhandled_exception_handler, validation_exception_handler

from .routers.api.api_router import router as api_router
from starlette.middleware.sessions import SessionMiddleware
from .views import auth, teams, tasks, meetings, comments, evaluations, calendar, users

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    yield
    ...


app = FastAPI(
    lifespan=lifespan,
    title="Team Management API",
    description="API для управления командами, задачами и совещаниями",
    version="1.0.0"
)
"""
Главное приложение FastAPI.

Объединяет API роутеры и views роутеры, а также настраивает исключения.
"""

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("VIEWS_SECRET", "dev-secret-change-me"),
    session_cookie="views_session",
    same_site="lax",
    https_only=False,
)
"""
Middleware для управления сессиями.
"""

app.mount("/static", StaticFiles(directory="app/static"), name="static")
"""
Служба для обслуживания статических файлов.
"""

# Роутеры Views
app.include_router(auth.router, prefix="/views/auth", tags=["views-auth"])
app.include_router(teams.router, prefix="/views/teams", tags=["views-teams"])
app.include_router(tasks.router, prefix="/views/teams", tags=["views-tasks"])
app.include_router(meetings.router, prefix="/views/teams", tags=["views-meetings"])
app.include_router(comments.router, prefix="/views/teams", tags=["views-comments"])
app.include_router(evaluations.router, prefix="/views/teams", tags=["views-evaluations"])
app.include_router(calendar.router, prefix="/views/calendar", tags=["views-calendar"])
app.include_router(users.router, prefix="/views/users", tags=["views-users"])

# Роутеры API
app.include_router(api_router)

# Обработчики исключений
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(NoResultFound, db_not_found_exception_handler)


@app.get("/views")
@app.get("/views/")
async def views_root():
    """Перенаправляет на главную страницу views."""
    return RedirectResponse("/views/teams/", status_code=303)


@app.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}