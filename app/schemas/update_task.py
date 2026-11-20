from datetime import datetime

from pydantic import BaseModel


class UpdateTask(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: datetime | None = None