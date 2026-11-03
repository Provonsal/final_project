from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.permissions import cap, flash
from app.views.templates import templates

router = APIRouter()


@router.get("/{team_id}/tasks/{task_id}/comments", response_class=HTMLResponse)
async def list_comments(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/tasks/{task_id}/comments")
    return templates.TemplateResponse(
        request, "comments/list.html",
        {"team_id": team_id, "task_id": task_id,
         "comments": r.json() if ok(r) else [],
         "error": None if ok(r) else r.text},
    )


@router.get("/{team_id}/tasks/{task_id}/comments/new", response_class=HTMLResponse)
async def new_comment(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "comments/form.html",
        {"mode": "create", "team_id": team_id, "task_id": task_id,
         "comment": {"text": ""}},
    )


@router.post("/{team_id}/tasks/{task_id}/comments/new")
async def create_comment(
    request: Request,
    team_id: str,
    task_id: str,
    text: str = Form(...),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "comment", "create")
    r = await api_call(
        request, "POST", f"/api/v1/teams/{team_id}/tasks/{task_id}/comments",
        json={"text": text}, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к комментированию (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "comments/form.html",
            {"mode": "create", "team_id": team_id, "task_id": task_id,
             "comment": {"text": text}, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)


@router.get("/{team_id}/tasks/{task_id}/comments/{comment_id}/edit", response_class=HTMLResponse)
async def edit_comment(request: Request, team_id: str, task_id: str, comment_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "comments/form.html",
        {"mode": "edit", "team_id": team_id, "task_id": task_id,
         "comment_id": comment_id, "comment": {"text": ""}},
    )


@router.post("/{team_id}/tasks/{task_id}/comments/{comment_id}/edit")
async def update_comment(
    request: Request,
    team_id: str,
    task_id: str,
    comment_id: str,
    text: str = Form(""),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "comment", comment_id, "update")
    r = await api_call(
        request, "PATCH",
        f"/api/v1/teams/{team_id}/tasks/{task_id}/comments/{comment_id}",
        json={"text": text}, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к редактированию комментария (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "comments/form.html",
            {"mode": "edit", "team_id": team_id, "task_id": task_id,
             "comment_id": comment_id, "comment": {"text": text}, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)


@router.post("/{team_id}/tasks/{task_id}/comments/{comment_id}/delete")
async def delete_comment(request: Request, team_id: str, task_id: str, comment_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "comment", comment_id, "delete")
    r = await api_call(
        request, "DELETE",
        f"/api/v1/teams/{team_id}/tasks/{task_id}/comments/{comment_id}",
        cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к удалению комментария (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)
    if not ok(r):
        flash(request, f"Ошибка: {r.text}")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)
    flash(request, "Комментарий удалён.", "ok")
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/comments", status_code=303)