
from pydantic import BaseModel

from app.models.RateEnum import RateEnum


class UpdateEvaluation(BaseModel):
    rate: RateEnum | None = None