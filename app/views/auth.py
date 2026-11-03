from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok
from app.views.permissions import flash
from app.views.templates import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(request, "auth/login.html")


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    payload = {"username": username, "password": password, "grant_type": "password"}
    r = await api_call(request, "POST", "/api/v1/auth/login", data=payload)
    if not ok(r):
        return templates.TemplateResponse(
            request, "auth/login.html", {"error": r.text, "username": username}
        )
    body = r.json()
    token = body.get("access_token")
    if not token:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": f"Нет access_token в ответе:\n{r.text}", "username": username},
        )

    request.session.clear()
    request.session["token"] = token

    # Подтягиваем профиль — от role зависит, какие элементы управления показывать
    me_r = await api_call(request, "GET", "/api/v1/users/me")
    if ok(me_r):
        user = me_r.json()
        request.session["user"] = user
        request.session["role"] = user.get("role") or "guest"
    else:
        request.session["role"] = "guest"

    flash(request, "Успешный вход.", "ok")
    return RedirectResponse("/views/teams/", status_code=303)


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse(request, "auth/register.html", {"form": {}})


@router.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    role: str = Form("guest"),
):
    payload = {"username": username, "name": name, "password": password, "role": role}
    r = await api_call(request, "POST", "/api/v1/auth/register", data=payload)
    if not ok(r):
        return templates.TemplateResponse(
            request, "auth/register.html", {"error": r.text, "form": payload}
        )
    flash(request, "Аккаунт создан, войдите.", "ok")
    return RedirectResponse("/views/auth/login", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/views/auth/login", status_code=303)