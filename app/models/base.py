import uuid

from sqlalchemy import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для сущностей с id."""
    pass

class BaseModel(Base):
    """Базовый класс для моделей с UUID PK."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )