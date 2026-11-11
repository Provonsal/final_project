
import collections
from enum import Enum, auto
import os
from typing import NamedTuple
from dotenv import load_dotenv


class Config:

    _loaded: bool = False

    @classmethod
    def load_dotenv(cls, forced: bool = False):
        if not cls._loaded or forced:
            cls._loaded = load_dotenv()
        
        return cls._loaded

    @classmethod
    def get_env_value(cls, name: str) -> str | None:
        cls.load_dotenv()

        return os.getenv(name)

class ImportanceEnum(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    SKIP = auto()

class DatabaseConfig(NamedTuple):
    DATABASE_URL: str | None = Config.get_env_value("DATABASE_URL")

    @property
    def url(self):
        if self.DATABASE_URL is None:
            raise ValueError("DATABASE_URL is not set in the environment variables.")
        return self.DATABASE_URL
        
