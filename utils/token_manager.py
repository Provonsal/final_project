from datetime import UTC, datetime, timedelta, timezone
import hashlib
from typing import Optional
from fastapi import HTTPException
from jose import JWTError, jwt


class TKNManager:
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @classmethod
    def create_access_token(cls, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Создание JWT access токена"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        
        return encoded_jwt

    @classmethod
    def hash_token(cls, token: str) -> bytes:
        """
        Преобразует строковый JWT-токен в 32-байтовый хэш (SHA-256).
        """
        # Кодируем строку в байты (UTF-8)
        token_bytes = token.encode('utf-8')
        # Вычисляем SHA-256 (возвращает 32 байта)
        return hashlib.sha256(token_bytes).digest()

    @classmethod
    def create_refresh_token(cls, data: dict) -> str:
        """Создание JWT refresh токена"""
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        
        return encoded_jwt

    @classmethod
    def decode_token(cls, token: str) -> dict:
        """Декодирование JWT токена"""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )