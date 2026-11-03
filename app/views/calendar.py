from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.views.api_client import api_call, ok, redirect_if_anonymous
from app.views.templates import templates

router = APIRouter()


@router.get("/{team_id}", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    team_id: str,
    date_from: str | None = None,
    date_until: str | None = None,
):
    if (redir := redirect_if_anonymous(request)):
        return redir
    params: dict = {}
    if date_from:
        params["date_from"] = date_from
    if date_until:
        params["date_until"] = date_until
    r = await api_call(request, "GET", f"/api/v1/calendar/{team_id}", params=params or None)
    return templates.TemplateResponse(
        request,
        "calendar/view.html",
        {"team_id": team_id,
         "date_from": date_from or "", "date_until": date_until or "",
         "result": r.json() if ok(r) else None,
         "error": None if ok(r) else r.text},
    )