import hashlib
import secrets
from typing import NamedTuple, Tuple

from utils.config import PWDConfig


class PWDConfigTuple(NamedTuple):
    ALGORITHM: str
    SALT_SIZE: int 
    HASH_SIZE: int 
    ITERATIONS: int 

class PWDManager: 
    
    _pwd_config: PWDConfigTuple

    def __init__(self, token_config: PWDConfig):
        config = PWDConfigTuple(
            token_config.pwd_alg,
            int(token_config.salt_size),
            int(token_config.hash_size),
            int(token_config.iterations)
        )

        self._pwd_config = config
    
    def generate_salt(self) -> bytes:
        """Генерирует криптографически безопасную соль (16 байт)."""
        return secrets.token_bytes(self._pwd_config.SALT_SIZE)

    def hash_password(self, password: str, salt: bytes) -> bytes:
        """
        Хэширует пароль с солью.
        Возвращает ровно 32 байта.
        """
        # Кодируем пароль в bytes
        password_bytes = password.encode('utf-8')

        hash_bytes = hashlib.pbkdf2_hmac(
            self._pwd_config.ALGORITHM,
            password_bytes,
            salt,
            self._pwd_config.ITERATIONS,
            dklen=self._pwd_config.HASH_SIZE
        )

        return hash_bytes

    def create_credentials(self, password: str) -> Tuple[bytes, bytes]:
        """
        Создаёт пару (salt, password_hash) для нового пользователя.
        """
        salt = self.generate_salt()
        hash_bytes = self.hash_password(password, salt)
        return salt, hash_bytes
    
    def verify_password(self, password: str, salt: bytes, stored_hash: bytes) -> bool:
        """
        Проверяет пароль.
        Сравнивает через secrets.compare_digest для защиты от timing-атак.
        """
        new_hash = self.hash_password(password, salt)
        return secrets.compare_digest(new_hash, stored_hash)