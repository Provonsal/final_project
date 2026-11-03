import enum


class RoleEnum(str, enum.Enum):
    GUEST = "guest"
    AUTH = "auth"
    MANAGER = "manager"
    MEMBER = "member"