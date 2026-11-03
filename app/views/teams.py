from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.permissions import cap, flash
from app.views.templates import templates

router = APIRouter()


def _team_defaults(data: dict | None = None) -> dict:
    d = {"name": "", "max_per_team": 10}
    if data:
        d.update({k: v for k, v in data.items() if v is not None})
    return d


@router.get("/", response_class=HTMLResponse)
async def list_teams(request: Request):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", "/api/v1/teams/")
    return templates.TemplateResponse(
        request,
        "teams/list.html",
        {"teams": r.json() if ok(r) else [],
         "error": None if ok(r) else r.text},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_team(request: Request):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "teams/form.html",
        {"mode": "create", "team": _team_defaults()},
    )


@router.post("/new")
async def create_team(
    request: Request,
    name: str = Form(...),
    max_per_team: int = Form(10),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", "create")
    payload = {"name": name, "max_per_team": max_per_team}
    r = await api_call(request, "POST", "/api/v1/teams/", json=payload, cap=cap_key)
    if r.status_code == 403:
        flash(request, "Нет доступа к созданию команды (403).")
        return RedirectResponse("/views/teams/", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "teams/form.html",
            {"mode": "create", "team": _team_defaults(payload), "error": r.text},
        )
    return RedirectResponse("/views/teams/", status_code=303)


@router.post("/join")
async def join_team(request: Request, invite_code: str = Form(...)):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", "join")
    r = await api_call(
        request, "POST", "/api/v1/teams/join",
        params={"invite_code": invite_code}, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к присоединению (403).")
        return RedirectResponse("/views/teams/", status_code=303)
    if not ok(r):
        flash(request, f"Ошибка join: {r.text}")
        return RedirectResponse("/views/teams/", status_code=303)
    flash(request, "Вы присоединились к команде.", "ok")
    return RedirectResponse("/views/teams/", status_code=303)


@router.post("/{team_id}/code")
async def get_invite_code(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "invite")
    r = await api_call(
        request, "POST", "/api/v1/teams/code",
        params={"team_id": team_id}, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к инвайт-коду (403).")
        return RedirectResponse(f"/views/teams/{team_id}", status_code=303)
    return templates.TemplateResponse(
        request, "teams/invite_code.html",
        {"team_id": team_id,
         "result": r.json() if ok(r) else None,
         "error": None if ok(r) else r.text},
    )


@router.get("/{team_id}", response_class=HTMLResponse)
async def team_detail(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}")
    if not ok(r):
        return HTMLResponse(f"<pre class='error'>{r.text}</pre><a href='/views/teams/'>Back</a>")
    return templates.TemplateResponse(
        request, "teams/detail.html",
        {"team": r.json(), "team_id": team_id},
    )


@router.get("/{team_id}/edit", response_class=HTMLResponse)
async def edit_team(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}")
    team = _team_defaults(r.json() if ok(r) else None)
    return templates.TemplateResponse(
        request, "teams/form.html",
        {"mode": "edit", "team": team, "team_id": team_id,
         "error": None if ok(r) else r.text},
    )


@router.post("/{team_id}/edit")
async def update_team(
    request: Request,
    team_id: str,
    name: str = Form(""),
    max_per_team: str = Form(""),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "update")
    payload: dict = {}
    if name:
        payload["name"] = name
    if max_per_team != "":
        payload["max_per_team"] = int(max_per_team)
    r = await api_call(
        request, "PATCH", f"/api/v1/teams/{team_id}", json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к редактированию команды (403).")
        return RedirectResponse(f"/views/teams/{team_id}", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "teams/form.html",
            {"mode": "edit", "team_id": team_id,
             "team": _team_defaults(payload), "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}", status_code=303)


@router.post("/{team_id}/delete")
async def delete_team(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "delete")
    r = await api_call(request, "DELETE", f"/api/v1/teams/{team_id}", cap=cap_key)
    if r.status_code == 403:
        flash(request, "Нет доступа к удалению команды (403).")
        return RedirectResponse(f"/views/teams/{team_id}", status_code=303)
    if not ok(r):
        flash(request, f"Ошибка удаления: {r.text}")
        return RedirectResponse(f"/views/teams/{team_id}", status_code=303)
    flash(request, "Команда удалена.", "ok")
    return RedirectResponse("/views/teams/", status_code=303)


@router.get("/{team_id}/members", response_class=HTMLResponse)
async def team_members(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/members")
    return templates.TemplateResponse(
        request, "teams/members.html",
        {"team_id": team_id,
         "members": r.json() if ok(r) else [],
         "error": None if ok(r) else r.text},
    )