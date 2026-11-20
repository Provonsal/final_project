
from pydantic import BaseModel



class UpdateComment(BaseModel):
    text: str | None = None
