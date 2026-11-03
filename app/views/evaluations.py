from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.permissions import cap, flash
from app.views.templates import templates

router = APIRouter()

RATES = [0, 1, 2, 3, 4, 5]


@router.get("/{team_id}/tasks/{task_id}/evaluation", response_class=HTMLResponse)
async def read_evaluation(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    r = await api_call(request, "GET", f"/api/v1/teams/{team_id}/tasks/{task_id}/evaluation")
    return templates.TemplateResponse(
        request, "evaluations/detail.html",
        {"team_id": team_id, "task_id": task_id,
         "evaluation": r.json() if ok(r) else None,
         "error": None if ok(r) else r.text},
    )


@router.get("/{team_id}/tasks/{task_id}/evaluation/new", response_class=HTMLResponse)
async def new_evaluation(request: Request, team_id: str, task_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "evaluations/form.html",
        {"mode": "create", "team_id": team_id, "task_id": task_id,
         "evaluation": {"rate": 0}, "rates": RATES},
    )


@router.post("/{team_id}/tasks/{task_id}/evaluation/new")
async def create_evaluation(
    request: Request,
    team_id: str,
    task_id: str,
    rate: int = Form(...),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "evaluation", "create")
    payload = {"task_id": task_id, "rate": rate}
    r = await api_call(
        request, "POST", f"/api/v1/teams/{team_id}/tasks/{task_id}/evaluation",
        json=payload, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к оценке задачи (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/evaluation", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "evaluations/form.html",
            {"mode": "create", "team_id": team_id, "task_id": task_id,
             "evaluation": {"rate": rate}, "rates": RATES, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/evaluation", status_code=303)


@router.get("/{team_id}/tasks/{task_id}/evaluation/{evaluation_id}/edit", response_class=HTMLResponse)
async def edit_evaluation(request: Request, team_id: str, task_id: str, evaluation_id: str):
    if (redir := redirect_if_anonymous(request)):
        return redir
    return templates.TemplateResponse(
        request, "evaluations/form.html",
        {"mode": "edit", "team_id": team_id, "task_id": task_id,
         "evaluation_id": evaluation_id, "evaluation": {"rate": 0}, "rates": RATES},
    )


@router.post("/{team_id}/tasks/{task_id}/evaluation/{evaluation_id}/edit")
async def update_evaluation(
    request: Request,
    team_id: str,
    task_id: str,
    evaluation_id: str,
    rate: int = Form(...),
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    cap_key = cap("team", team_id, "task", task_id, "evaluation", evaluation_id, "update")
    r = await api_call(
        request, "PATCH",
        f"/api/v1/teams/{team_id}/tasks/{task_id}/evaluation/{evaluation_id}",
        json={"rate": rate}, cap=cap_key,
    )
    if r.status_code == 403:
        flash(request, "Нет доступа к редактированию оценки (403).")
        return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/evaluation", status_code=303)
    if not ok(r):
        return templates.TemplateResponse(
            request, "evaluations/form.html",
            {"mode": "edit", "team_id": team_id, "task_id": task_id,
             "evaluation_id": evaluation_id, "evaluation": {"rate": rate},
             "rates": RATES, "error": r.text},
        )
    return RedirectResponse(f"/views/teams/{team_id}/tasks/{task_id}/evaluation", status_code=303)