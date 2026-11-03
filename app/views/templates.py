from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.views.permissions import can, is_forbidden, pop_flash

templates = Jinja2Templates(directory="app/templates")


@pass_context
def _can(ctx, key: str) -> bool:
    req = ctx.get("request")
    return True if req is None else can(req, key)


@pass_context
def _is_forbidden(ctx, key: str) -> bool:
    req = ctx.get("request")
    return False if req is None else is_forbidden(req, key)


@pass_context
def _flashed(ctx) -> list[dict]:
    req = ctx.get("request")
    return [] if req is None else pop_flash(req)


templates.env.globals["can"] = _can
templates.env.globals["is_forbidden"] = _is_forbidden
templates.env.globals["flashed"] = _flashed