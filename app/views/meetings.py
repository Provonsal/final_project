from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.permissions import cap, flash
from app.views.templates import templates

router = APIRouter()


def _meeting_defaults(data: dict | None = None) -> dict:
    d = {"starts_at": "", "ends_at": "", "max_members": 10}
    if data:
        d.update({k: v for k, v in data.items() if v is not None})
    return d


@router.get("/{team_id}/meetings", response_class=HTMLResponse)
async def list_meetings(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/meetings")
    return templates.TemplateResponse(
        request, "meetings/list.html",
        {"team_id": team_id,
         "meetings": r.json() if ok(r) else [],
         "error": None if ok(r) else r.text},
    )


@router.get("/{team_id}/meetings/new", response_class=HTMLResponse)
async def new_meeting(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "meetings/form.html",
        {"mode": "create", "team_id": team_id, "meeting": _meeting_defaults()},
    )


@router.post("/{team_id}/meetings/new")
async def create_meeting(
    request: Request,
    team_id: str,
    starts_at: str = Form(""),
    ends_at: str = Form(""),
    max_members: int = Form(10),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "meeting", "create")
    payload: dict = {"max_members": max_members}
    if starts_at:
        payload["starts_at"] = starts_at
    if ends_at:
        payload["ends_at"] = ends_at
    r = await api_call(
        request, "POST", f"/api/v1/teams/{team_id}/meetings",
        json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к созданию встречи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/meetings", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "meetings/form.html",
            {"mode": "create", "team_id": team_id,
             "meeting": _meeting_defaults(payload), "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/meetings", status_code=303)


@router.get("/{team_id}/meetings/{meeting_id}", response_class=HTMLResponse)
async def meeting_detail(request: Request, team_id: str, meeting_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/meetings/{meeting_id}")
    if not ok(r):
        return HTMLResponse(f"<pre class='error'>{r.text}</pre>")
    return templates.TemplateResponse(
        request, "meetings/detail.html",
        {"team_id": team_id, "meeting_id": meeting_id, "meeting": r.json()},
    )


@router.get("/{team_id}/meetings/{meeting_id}/edit", response_class=HTMLResponse)
async def edit_meeting(request: Request, team_id: str, meeting_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/meetings/{meeting_id}")
    meeting = _meeting_defaults(r.json() if ok(r) else None)
    return templates.TemplateResponse(
        request, "meetings/form.html",
        {"mode": "edit", "team_id": team_id, "meeting_id": meeting_id,
         "meeting": meeting, "error": None if ok(r) else r.text},
    )


@router.post("/{team_id}/meetings/{meeting_id}/edit")
async def update_meeting(
    request: Request,
    team_id: str,
    meeting_id: str,
    starts_at: str = Form(""),
    ends_at: str = Form(""),
    max_members: str = Form(""),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "meeting", meeting_id, "update")
    payload: dict = {}
    if starts_at:
        payload["starts_at"] = starts_at
    if ends_at:
        payload["ends_at"] = ends_at
    if max_members != "":
        payload["max_members"] = int(max_members)
    r = await api_call(
        request, "PATCH", f"/api/v1/teams/{team_id}/meetings/{meeting_id}",
        json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к редактированию встречи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/meetings/{meeting_id}", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "meetings/form.html",
            {"mode": "edit", "team_id": team_id, "meeting_id": meeting_id,
             "meeting": _meeting_defaults(payload), "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/meetings/{meeting_id}", status_code=303)


@router.post("/{team_id}/meetings/{meeting_id}/delete")
async def delete_meeting(request: Request, team_id: str, meeting_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "meeting", meeting_id, "delete")
    r = await api_call(
        request, "DELETE", f"/api/v1/teams/{team_id}/meetings/{meeting_id}", cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к удалению встречи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/meetings/{meeting_id}", status_code=303)
    if not ok(r):
        flash(request, f"Ошибка удаления: {r.text}")
        return RedirectResponse(f"/views/teams/{team_id}/meetings/{meeting_id}", status_code=303)
    flash(request, "Встреча удалена.", "ok")
    return RedirectResponse(f"/views/teams/{team_id}/meetings", status_code=303)