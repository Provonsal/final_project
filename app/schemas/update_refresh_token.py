
from pydantic import BaseModel



class UpdateRefreshToken(BaseModel):
    revoked: bool | None = None
