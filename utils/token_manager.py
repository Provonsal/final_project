from datetime import UTC, datetime, timedelta, timezone
import hashlib
from typing import NamedTuple, Optional
from fastapi import HTTPException
from jose import JWTError, jwt

from utils.config import Config, TokenConfig


class TokenConfigTuple(NamedTuple):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int


class TKNManager:
    _token_config: TokenConfigTuple

    def __init__(self, token_config: TokenConfig):
        config = TokenConfigTuple(
            token_config.key_value,
            token_config.token_cipher_alg,
            int(token_config.access_token_expire_value),
            int(token_config.refresh_token_expire_value)
        )

        self._token_config = config

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Создание JWT access токена"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=self._token_config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self._token_config.SECRET_KEY, algorithm=self._token_config.ALGORITHM)
        
        return encoded_jwt

    def hash_token(self, token: str) -> bytes:
        """
        Преобразует строковый JWT-токен в 32-байтовый хэш (SHA-256).
        """
        # Кодируем строку в байты (UTF-8)
        token_bytes = token.encode('utf-8')
        # Вычисляем SHA-256 (возвращает 32 байта)
        return hashlib.sha256(token_bytes).digest()

    def create_refresh_token(self, data: dict) -> str:
        """Создание JWT refresh токена"""
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(days=self._token_config.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self._token_config.SECRET_KEY, algorithm=self._token_config.ALGORITHM)
        
        return encoded_jwt

    def decode_token(self, token: str) -> dict:
        """Декодирование JWT токена"""
        try:
            payload = jwt.decode(token, self._token_config.SECRET_KEY, algorithms=[self._token_config.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )