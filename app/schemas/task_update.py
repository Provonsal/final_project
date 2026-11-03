from datetime import datetime
import uuid

from pydantic import BaseModel


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: datetime | None = None