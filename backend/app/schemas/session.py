from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    patient_id: UUID


class TranscriptSyncRequest(BaseModel):
    transcript_text: str
    detected_language: str | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    status: str
    started_at: datetime
    ended_at: datetime | None
    transcript_text: str
    detected_languages: list[str]


class PipelineUpdate(BaseModel):
    session_id: UUID
    transcript_chunk: str
    full_transcript: str
    detected_languages: list[str]
    structured_data: dict
    doctor_assist: dict
