
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
    DB_NAME: str | None = Config.get_env_value("DB_NAME")
    DB_PWD: str | None = Config.get_env_value("DB_PWD")
    DB_USER: str | None = Config.get_env_value("DB_USER")
    DB_HOST: str | None = Config.get_env_value("DB_HOST")
    DB_NAME_N_DRIVER: str | None = Config.get_env_value("DB_NAME_N_DRIVER")

    # driver://user:pass@localhost/dbname

    @property
    def url(self):
        return f"{self.DB_NAME_N_DRIVER}://{self.DB_USER}:{self.DB_PWD}@{self.DB_HOST}/{self.DB_NAME}"
