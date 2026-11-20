
from pydantic import BaseModel



class CreateTeam(BaseModel):
    name: str
    max_per_team: int = 10
