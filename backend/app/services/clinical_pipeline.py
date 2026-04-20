from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.orm import Session

from app.models.record import Record
from app.models.session import ClinicalSession
from app.schemas.record import DoctorAssistResponse, StructuredClinicalData
from app.services.extraction import ClinicalLLMService
from app.services.medication import MedicationValidatorService


@dataclass
class PipelineUpdatePayload:
    session_id: str
    transcript_chunk: str
    full_transcript: str
    detected_languages: list[str]
    structured_data: dict
    doctor_assist: dict


class ClinicalPipelineService:
    def __init__(self, llm_service: ClinicalLLMService) -> None:
        self.llm_service = llm_service
        self.medication_validator = MedicationValidatorService()
        self._logger = structlog.get_logger(__name__)

    def append_transcript_chunk(
        self,
        db: Session,
        session: ClinicalSession,
        transcript_chunk: str,
        detected_language: str,
    ) -> PipelineUpdatePayload:
        session.transcript_text = f"{session.transcript_text} {transcript_chunk}".strip()
        languages = set(session.detected_languages or [])
        if detected_language and detected_language != "unknown":
            languages.add(detected_language)
        session.detected_languages = sorted(languages)

        record = self._ensure_record(session)
        record.raw_transcript = session.transcript_text

        db.add(session)
        db.add(record)
        db.commit()
        db.refresh(session)

        structured_data = self._structured_data_from_record(record)
        doctor_assist = self._doctor_assist_from_record(record, structured_data)

        return PipelineUpdatePayload(
            session_id=str(session.id),
            transcript_chunk=transcript_chunk,
            full_transcript=session.transcript_text,
            detected_languages=session.detected_languages,
            structured_data=structured_data.model_dump(),
            doctor_assist=doctor_assist.model_dump(),
        )

    def refresh_structured_data(
        self,
        db: Session,
        session: ClinicalSession,
    ) -> PipelineUpdatePayload:
        record = self._ensure_record(session)
        structured_data, doctor_assist = self._safe_enrichment(session.transcript_text)

        record.raw_transcript = session.transcript_text
        record.structured_data = structured_data.model_dump()
        record.suggested_diagnosis = doctor_assist.suggested_diagnosis
        record.missing_fields = doctor_assist.missing_fields
        record.rag_summary = self._build_rag_summary(structured_data, session.transcript_text)

        db.add(session)
        db.add(record)
        db.commit()
        db.refresh(session)

        return PipelineUpdatePayload(
            session_id=str(session.id),
            transcript_chunk="",
            full_transcript=session.transcript_text,
            detected_languages=session.detected_languages,
            structured_data=structured_data.model_dump(),
            doctor_assist=doctor_assist.model_dump(),
        )

    def replace_transcript_and_extract(
        self,
        db: Session,
        session: ClinicalSession,
        transcript_text: str,
        detected_language: str | None,
    ) -> PipelineUpdatePayload:
        session.transcript_text = transcript_text.strip()
        languages = set(session.detected_languages or [])
        if detected_language and detected_language != "unknown":
            languages.add(detected_language)
        session.detected_languages = sorted(languages)

        record = self._ensure_record(session)
        record.raw_transcript = session.transcript_text

        structured_data, doctor_assist = self._safe_enrichment(session.transcript_text)
        record.structured_data = structured_data.model_dump()
        record.suggested_diagnosis = doctor_assist.suggested_diagnosis
        record.missing_fields = doctor_assist.missing_fields
        record.rag_summary = self._build_rag_summary(structured_data, session.transcript_text)

        db.add(session)
        db.add(record)
        db.commit()
        db.refresh(session)

        return PipelineUpdatePayload(
            session_id=str(session.id),
            transcript_chunk="",
            full_transcript=session.transcript_text,
            detected_languages=session.detected_languages,
            structured_data=structured_data.model_dump(),
            doctor_assist=doctor_assist.model_dump(),
        )

    def finalize_session(self, db: Session, session: ClinicalSession) -> None:
        if not session.transcript_text:
            return

        structured_data, doctor_assist = self._safe_enrichment(session.transcript_text)
        record = self._ensure_record(session)
        record.raw_transcript = session.transcript_text
        record.structured_data = structured_data.model_dump()
        record.suggested_diagnosis = doctor_assist.suggested_diagnosis
        record.missing_fields = doctor_assist.missing_fields
        record.rag_summary = self._build_rag_summary(structured_data, session.transcript_text)

        db.add(session)
        db.add(record)
        db.commit()

    @staticmethod
    def _build_rag_summary(structured_data: StructuredClinicalData, transcript: str) -> str:
        summary = [
            f"Symptoms: {', '.join(structured_data.symptoms) or 'not captured'}",
            f"Duration: {structured_data.duration or 'not captured'}",
            f"Diagnosis: {structured_data.diagnosis or 'not captured'}",
            f"Medications: {', '.join(structured_data.medications) or 'not captured'}",
            f"Transcript excerpt: {transcript[:900]}",
        ]
        return "\n".join(summary)

    @staticmethod
    def _ensure_record(session: ClinicalSession) -> Record:
        record = session.record or Record(patient_id=session.patient_id, session_id=session.id)
        session.record = record
        return record

    @staticmethod
    def _structured_data_from_record(record: Record) -> StructuredClinicalData:
        payload = record.structured_data or {}
        return StructuredClinicalData.model_validate(payload)

    def _doctor_assist_from_record(
        self,
        record: Record,
        structured_data: StructuredClinicalData,
    ) -> DoctorAssistResponse:
        fallback = self.llm_service._fallback_assist(structured_data)
        return DoctorAssistResponse(
            suggested_diagnosis=(
                record.suggested_diagnosis
                if record.suggested_diagnosis is not None
                else structured_data.diagnosis
            ),
            missing_fields=record.missing_fields if record.missing_fields is not None else fallback.missing_fields,
            red_flags=[],
        )

    def _safe_enrichment(
        self,
        transcript: str,
    ) -> tuple[StructuredClinicalData, DoctorAssistResponse]:
        try:
            structured_data = self.medication_validator.normalize(
                self.llm_service.extract_structured_data(transcript)
            )
        except Exception as exc:
            self._logger.exception("structured_data_extraction_failed", error=str(exc))
            structured_data = self.medication_validator.normalize(
                self.llm_service.fallback_structured_data(transcript)
            )

        try:
            doctor_assist = self.llm_service.doctor_assist(transcript, structured_data)
        except Exception as exc:
            self._logger.exception("doctor_assist_generation_failed", error=str(exc))
            doctor_assist = self.llm_service._fallback_assist(structured_data)
        return structured_data, doctor_assist
