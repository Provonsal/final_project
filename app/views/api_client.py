import os
import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.views.permissions import mark_forbidden, mark_allowed

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_token(request: Request) -> str | None:
    return request.session.get("token")


def redirect_if_anonymous(request: Request) -> RedirectResponse | None:
    if not get_token(request):
        return RedirectResponse("/views/auth/login", status_code=303)
    return None


async def api_call(
    request: Request,
    method: str,
    path: str,
    *,
    json: dict | None = None,
    data: dict | None = None,
    params: dict | None = None,
    cap: str | None = None,
) -> httpx.Response:
    headers = {}
    token = get_token(request)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=15.0) as client:
        r = await client.request(
            method, path, headers=headers, json=json, data=data, params=params
        )

    if cap:
        if r.status_code == 403:
            mark_forbidden(request, cap)
        elif 200 <= r.status_code < 300:
            mark_allowed(request, cap)
    return r


def ok(r: httpx.Response) -> bool:
    return 200 <= r.status_code < 300