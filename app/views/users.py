from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.views.templates import templates

from app.views.api_client import api_call, ok, redirect_if_anonymous

router = APIRouter()


@router.get("/me", response_class=HTMLResponse)
async def me(request: Request):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", "/api/v1/users/me")
    if ok(r):
        user = r.json()
        request.session["user"] = user
        request.session["role"] = user.get("role") or "guest"
    return templates.TemplateResponse(
        request,
        "users/me.html",
        {"me": r.json() if ok(r) else None,
         "error": None if ok(r) else r.text},
    )