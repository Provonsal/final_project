import enum


class TaskStatusEnum(enum.Enum):
    OPEN = enum.auto()
    IN_PROGRESS = enum.auto()
    DONE = enum.auto()