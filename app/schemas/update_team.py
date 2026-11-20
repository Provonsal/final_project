
from pydantic import BaseModel



class UpdateTeam(BaseModel):
    name: str | None = None
    max_per_team: int | None = None
