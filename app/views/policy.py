from __future__ import annotations


# Глобальные cap-ключи, которые не зависят от team.
_GLOBAL_ALLOW: dict[str, set[str]] = {
    "team:create": {"auth", "manager"},
    "team:join": {"auth", "member", "manager"},
}


def decide(role: str | None, key: str) -> bool | None:
    """Показывать ли элемент управления для данной роли.

    True  — показывать (роль позволяет)
    False — не показывать (роль точно не позволяет)
    None  — неизвестно; пусть решит фактический 403 от бэкенда
    """
    role = role or "guest"

    if key in _GLOBAL_ALLOW:
        return role in _GLOBAL_ALLOW[key]

    if role == "manager":
        return True
    if role in ("guest", "auth"):
        return False

    if role == "member":
        parts = key.split(":")
        # комментарии и оценки: создание — да
        if parts[-2:] == ["comment", "create"]:
            return True
        if parts[-2:] == ["evaluation", "create"]:
            return True
        # правка/удаление конкретной записи — возможно, своей; решит 403
        if (
            len(parts) >= 3
            and parts[-3] in ("comment", "evaluation")
            and parts[-1] in ("update", "delete")
        ):
            return None
        return False

    return False