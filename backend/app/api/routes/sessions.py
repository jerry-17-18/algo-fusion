from datetime import datetime, timezone
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_doctor, get_db
from app.models.enums import SessionStatus
from app.models.patient import Patient
from app.models.session import ClinicalSession
from app.models.user import User
from app.schemas.session import PipelineUpdate, SessionCreate, SessionRead, TranscriptSyncRequest
from app.services.runtime import asr_service, clinical_pipeline, rag_service

router = APIRouter()


@router.post("", response_model=SessionRead)
def start_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(get_current_doctor),
) -> ClinicalSession:
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    session = ClinicalSession(patient_id=patient.id, doctor_id=doctor.id, status=SessionStatus.active)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> ClinicalSession:
    session = db.get(ClinicalSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/stop", response_model=SessionRead)
def stop_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> ClinicalSession:
    session = db.get(ClinicalSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = SessionStatus.completed
    session.ended_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)

    clinical_pipeline.finalize_session(db=db, session=session)
    rag_service.refresh_record_from_session(db=db, session_id=session.id)
    return session


@router.post("/{session_id}/transcript", response_model=PipelineUpdate)
def sync_transcript(
    session_id: UUID,
    payload: TranscriptSyncRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> PipelineUpdate:
    session = db.get(ClinicalSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=409, detail="Session is not active")
    if not payload.transcript_text.strip():
        raise HTTPException(status_code=422, detail="Transcript is empty")

    update = clinical_pipeline.replace_transcript_and_extract(
        db=db,
        session=session,
        transcript_text=payload.transcript_text,
        detected_language=payload.detected_language,
    )
    rag_service.refresh_record_from_session(db=db, session_id=session.id)
    return PipelineUpdate.model_validate(asdict(update))


@router.post("/{session_id}/audio", response_model=PipelineUpdate)
async def transcribe_consultation_audio(
    session_id: UUID,
    audio_file: UploadFile = File(...),
    language_hint: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> PipelineUpdate:
    session = db.get(ClinicalSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not audio_file.filename:
        raise HTTPException(status_code=422, detail="Audio filename is missing")

    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Uploaded audio file is empty")

    asr_result = await run_in_threadpool(
        asr_service.transcribe_consultation,
        audio_bytes,
        audio_file.filename,
        audio_file.content_type or "audio/webm",
        language_hint,
    )
    if not asr_result.text.strip():
        raise HTTPException(status_code=422, detail="No transcript returned from Sarvam")

    update = clinical_pipeline.replace_transcript_and_extract(
        db=db,
        session=session,
        transcript_text=asr_result.text,
        detected_language=asr_result.language,
    )
    rag_service.refresh_record_from_session(db=db, session_id=session.id)
    return PipelineUpdate.model_validate(asdict(update))


@router.get("/patient/{patient_id}", response_model=list[SessionRead])
def list_sessions_for_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> list[ClinicalSession]:
    query = (
        select(ClinicalSession)
        .where(ClinicalSession.patient_id == patient_id)
        .order_by(ClinicalSession.started_at.desc())
    )
    return list(db.scalars(query).all())
