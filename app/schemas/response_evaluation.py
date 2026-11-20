import uuid

from pydantic import BaseModel

from app.models import RateEnum



class ResponseEvaluationSchema(BaseModel):
    id: uuid.UUID
    rate: RateEnum
    author: uuid.UUID