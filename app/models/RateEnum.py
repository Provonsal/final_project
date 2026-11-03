import enum


class RateEnum(enum.Enum):
    UNRATED = 0
    FAIL = enum.auto()
    BAD = enum.auto()
    DECENT = enum.auto()
    GOOD = enum.auto()
    PERFECT = enum.auto()