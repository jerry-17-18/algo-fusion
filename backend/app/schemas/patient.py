from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    external_id: str | None = None
    full_name: str
    age: int | None = None
    gender: str | None = None
    preferred_language: str | None = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    full_name: str
    age: int | None
    gender: str | None
    preferred_language: str | None
    created_at: datetime
