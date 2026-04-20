from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StructuredClinicalData(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    duration: str = ""
    diagnosis: str = ""
    medications: list[str] = Field(default_factory=list)


class DoctorAssistResponse(BaseModel):
    suggested_diagnosis: str = ""
    missing_fields: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    session_id: UUID
    raw_transcript: str
    structured_data: StructuredClinicalData
    suggested_diagnosis: str | None
    missing_fields: list[str]
    rag_summary: str | None
    created_at: datetime
    updated_at: datetime | None = None


class RAGQueryRequest(BaseModel):
    patient_id: UUID | None = None
    question: str
    top_k: int = 4


class RAGCitation(BaseModel):
    record_id: UUID
    session_id: UUID
    excerpt: str
    score: float


class RAGAnswer(BaseModel):
    answer: str
    citations: list[RAGCitation] = Field(default_factory=list)


class PatientHistoryRecord(BaseModel):
    id: UUID
    session_id: UUID
    created_at: datetime
    raw_transcript: str
    structured_data: StructuredClinicalData
    suggested_diagnosis: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class PatientHistoryResponse(BaseModel):
    patient_id: UUID
    records: list[PatientHistoryRecord] = Field(default_factory=list)


class VisitReportSummary(BaseModel):
    id: UUID
    session_id: UUID
    created_at: datetime
    structured_data: StructuredClinicalData
    suggested_diagnosis: str | None = None


class PatientPortalProfile(BaseModel):
    id: UUID
    external_id: str
    full_name: str
    age: int | None = None
    gender: str | None = None


class PatientPortalDashboardResponse(BaseModel):
    patient: PatientPortalProfile
    reports: list[VisitReportSummary] = Field(default_factory=list)
