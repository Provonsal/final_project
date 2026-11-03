from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.permissions import cap, flash
from app.views.templates import templates

router = APIRouter()

STATUS_LABELS = {1: "To Do", 2: "In Progress", 3: "Done"}


def _task_defaults(data: dict | None = None) -> dict:
    d = {"title": "", "description": "", "assignee": "", "due_date": "", "status": 1}
    if data:
        d.update({k: v for k, v in data.items() if v is not None})
    return d


@router.get("/{team_id}/tasks", response_class=HTMLResponse)
async def list_tasks(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/tasks")
    return templates.TemplateResponse(
        request, "tasks/list.html",
        {"team_id": team_id,
         "tasks": r.json() if ok(r) else [],
         "error": None if ok(r) else r.text,
         "status_labels": STATUS_LABELS},
    )


@router.get("/{team_id}/tasks/new", response_class=HTMLResponse)
async def new_task(request: Request, team_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "tasks/form.html",
        {"mode": "create", "team_id": team_id,
         "task": _task_defaults(), "status_labels": STATUS_LABELS},
    )


@router.post("/{team_id}/tasks/new")
async def create_task(
    request: Request,
    team_id: str,
    title: str = Form(...),
    description: str = Form(...),
    assignee: str = Form(...),
    due_date: str = Form(...),
    status: int = Form(1),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", "create")
    payload = {
        "title": title, "description": description,
        "assignee": assignee, "due_date": due_date, "status": status,
    }
    r = await api_call(
        request, "POST", f"/api/v1/teams/{team_id}/tasks",
        json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к созданию задачи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "tasks/form.html",
            {"mode": "create", "team_id": team_id,
             "task": _task_defaults(payload), "status_labels": STATUS_LABELS, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks", status_code=303)


@router.get("/{team_id}/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/tasks/{task_id}")
    if not ok(r):
        return HTMLResponse(f"<pre class='error'>{r.text}</pre><a href='/views/teams/{team_id}/tasks'>Back</a>")
    return templates.TemplateResponse(
        request, "tasks/detail.html",
        {"team_id": team_id, "task_id": task_id, "task": r.json(),
         "status_labels": STATUS_LABELS},
    )


@router.get("/{team_id}/tasks/{task_id}/edit", response_class=HTMLResponse)
async def edit_task(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/tasks/{task_id}")
    task = _task_defaults(r.json() if ok(r) else None)
    return templates.TemplateResponse(
        request, "tasks/form.html",
        {"mode": "edit", "team_id": team_id, "task_id": task_id,
         "task": task, "status_labels": STATUS_LABELS,
         "error": None if ok(r) else r.text},
    )


@router.post("/{team_id}/tasks/{task_id}/edit")
async def update_task(
    request: Request,
    team_id: str,
    task_id: str,
    title: str = Form(""),
    description: str = Form(""),
    due_date: str = Form(""),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "update")
    payload: dict = {}
    if title:
        payload["title"] = title
    if description:
        payload["description"] = description
    if due_date:
        payload["due_date"] = due_date
    r = await api_call(
        request, "PATCH", f"/api/v1/teams/{team_id}/tasks/{task_id}",
        json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к редактированию задачи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "tasks/form.html",
            {"mode": "edit", "team_id": team_id, "task_id": task_id,
             "task": _task_defaults(payload), "status_labels": STATUS_LABELS, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}", status_code=303)


@router.post("/{team_id}/tasks/{task_id}/delete")
async def delete_task(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "delete")
    r = await api_call(
        request, "DELETE", f"/api/v1/teams/{team_id}/tasks/{task_id}", cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к удалению задачи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}", status_code=303)
    if not ok(r):
        flash(request, f"Ошибка удаления: {r.text}")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}", status_code=303)
    flash(request, "Задача удалена.", "ok")
    return RedirectResponse(f"/views/teams/{team_id}/tasks", status_code=303)