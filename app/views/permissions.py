from fastapi import Request

from app.views.policy import decide

_FORBIDDEN = "forbidden_caps"
_FLASH = "_flash"


def cap(*parts: object) -> str:
    return ":".join(str(p) for p in parts)


def mark_forbidden(request: Request, key: str) -> None:
    caps = request.session.get(_FORBIDDEN, [])
    if key not in caps:
        caps.append(key)
        request.session[_FORBIDDEN] = caps


def mark_allowed(request: Request, key: str) -> None:
    caps = request.session.get(_FORBIDDEN, [])
    if key in caps:
        request.session[_FORBIDDEN] = [c for c in caps if c != key]


def is_forbidden(request: Request, key: str) -> bool:
    return key in request.session.get(_FORBIDDEN, [])


def current_role(request: Request) -> str:
    return request.session.get("role") or "guest"


def can(request: Request, key: str) -> bool:
    if is_forbidden(request, key):
        return False
    return decide(current_role(request), key) is not False


def flash(request: Request, message: str, kind: str = "error") -> None:
    msgs = request.session.get(_FLASH, [])
    msgs.append({"kind": kind, "message": message})
    request.session[_FLASH] = msgs


def pop_flash(request: Request) -> list[dict]:
    msgs = request.session.get(_FLASH, [])
    request.session[_FLASH] = []
    return msgs