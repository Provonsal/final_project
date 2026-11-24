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


@pass_context
def format_datetime(ctx, dt) -> str:
    """Format datetime object to readable string"""
    if dt is None:
        return "Never"
    return dt.strftime("%d.%m.%Y %H:%M") if hasattr(dt, "strftime") else str(dt)


@pass_context
def format_date(ctx, dt) -> str:
    """Format date object to readable string"""
    if dt is None:
        return "Never"
    return dt.strftime("%d.%m.%Y") if hasattr(dt, "strftime") else str(dt)


# Register as filters (not globals) to work with pipe syntax
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_date"] = format_date

# Register globals
templates.env.globals["can"] = _can
templates.env.globals["is_forbidden"] = _is_forbidden
templates.env.globals["flashed"] = _flashed