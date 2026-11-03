import hashlib
import secrets
from typing import Tuple


class PWDManager: 
    
    ALGORITHM = "sha256"  # будем хранить в колонке algorithm
    SALT_SIZE = 16        # байт, как у тебя BYTEA(16)
    HASH_SIZE = 32        # байт, как у тебя BYTEA(32)
    ITERATIONS = 600_000  # количество итераций PBKDF2
    
    @classmethod
    def generate_salt(cls) -> bytes:
        """Генерирует криптографически безопасную соль (16 байт)."""
        return secrets.token_bytes(cls.SALT_SIZE)

    @classmethod
    def hash_password(cls, password: str, salt: bytes) -> bytes:
        """
        Хэширует пароль с солью.
        Возвращает ровно 32 байта.
        """
        # Кодируем пароль в bytes
        password_bytes = password.encode('utf-8')

        # PBKDF2-HMAC-SHA256 с 600 000 итераций
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password_bytes,
            salt,
            cls.ITERATIONS,
            dklen=cls.HASH_SIZE   # ровно 32 байта
        )

        return hash_bytes

    @classmethod
    def create_credentials(cls, password: str) -> Tuple[bytes, bytes]:
        """
        Создаёт пару (salt, password_hash) для нового пользователя.
        """
        salt = cls.generate_salt()
        hash_bytes = cls.hash_password(password, salt)
        return salt, hash_bytes
    
    @classmethod
    def verify_password(cls, password: str, salt: bytes, stored_hash: bytes) -> bool:
        """
        Проверяет пароль.
        Сравнивает через secrets.compare_digest для защиты от timing-атак.
        """
        new_hash = cls.hash_password(password, salt)
        return secrets.compare_digest(new_hash, stored_hash)