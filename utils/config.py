
import collections
from enum import Enum, auto
import os
from typing import Any, NamedTuple
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

def raise_if_None[T](obj: T | None, obj_name: str) -> T:
    if obj is None:
        raise ValueError(f"{obj_name} is not set in the environment variables.")
    else:
        return obj

class PWDConfig(NamedTuple):
    ALGORITHM: str | None = Config.get_env_value("ALGORITHM")
    SALT_SIZE: str | None = Config.get_env_value("SALT_SIZE")
    HASH_SIZE: str | None = Config.get_env_value("HASH_SIZE")
    ITERATIONS: str | None = Config.get_env_value("ITERATIONS")

    @property
    def pwd_alg(self):
        return raise_if_None(self.ALGORITHM, "ALGORITHM")

    @property
    def salt_size(self):
        return raise_if_None(self.SALT_SIZE, "SALT_SIZE")

    @property
    def hash_size(self):
        return raise_if_None(self.HASH_SIZE, "HASH_SIZE")

    @property
    def iterations(self):
        return raise_if_None(self.ITERATIONS, "ITERATIONS")


class TokenConfig(NamedTuple):
    SECRET_KEY: str | None = Config.get_env_value("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: str | None = Config.get_env_value("ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: str | None = Config.get_env_value("REFRESH_TOKEN_EXPIRE_DAYS")
    TOKEN_ALGORITHM: str | None = Config.get_env_value("TOKEN_ALGORITHM")

    @property
    def key_value(self):
        return raise_if_None(self.SECRET_KEY, "SECRET_KEY")

    @property
    def access_token_expire_value(self):
        return raise_if_None(self.ACCESS_TOKEN_EXPIRE_MINUTES, "ACCESS_TOKEN_EXPIRE_MINUTES")

    @property
    def refresh_token_expire_value(self):
        return raise_if_None(self.REFRESH_TOKEN_EXPIRE_DAYS, "REFRESH_TOKEN_EXPIRE_DAYS")

    @property
    def token_cipher_alg(self):
        return raise_if_None(self.TOKEN_ALGORITHM, "TOKEN_ALGORITHM")

class DatabaseConfig(NamedTuple):
    DATABASE_URL: str | None = Config.get_env_value("DATABASE_URL")

    @property
    def url(self):
        return raise_if_None(self.DATABASE_URL, "DATABASE_URL")
        
class APIServerConfig(NamedTuple):
    API_BASE_URL: str | None = Config.get_env_value("API_BASE_URL")

    @property
    def url(self):
        return raise_if_None(self.API_BASE_URL, "API_BASE_URL")