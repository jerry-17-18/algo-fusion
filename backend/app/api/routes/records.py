from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_doctor, get_current_patient, get_db
from app.models.patient import Patient
from app.models.record import Record
from app.models.user import User
from app.schemas.record import (
    PatientHistoryRecord,
    PatientHistoryResponse,
    PatientPortalDashboardResponse,
    PatientPortalProfile,
    RecordRead,
    VisitReportSummary,
)
from app.services.reporting import ReportService

router = APIRouter()
report_service = ReportService()


@router.get("/patient/{patient_id}", response_model=list[RecordRead])
def list_records(
    patient_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> list[Record]:
    query = select(Record).where(Record.patient_id == patient_id).order_by(Record.created_at.desc())
    return list(db.scalars(query).all())


@router.get("/patient/{patient_id}/history", response_model=PatientHistoryResponse)
def get_patient_history(
    patient_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> PatientHistoryResponse:
    return _build_patient_history_response(db=db, patient_id=patient_id)


@router.get("/patient/{patient_id}/history/download")
def download_patient_history(
    patient_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> Response:
    history = _build_patient_history_response(db=db, patient_id=patient_id)
    payload = history.model_dump(mode="json")
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="patient-{patient_id}-history.json"'},
    )


@router.get("/{record_id}/report/pdf")
def download_visit_report_pdf(
    record_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> Response:
    record = db.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    patient = db.get(Patient, record.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _pdf_response(patient=patient, record=record)


@router.get("/portal/me/reports", response_model=PatientPortalDashboardResponse)
def get_patient_portal_reports(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> PatientPortalDashboardResponse:
    query = select(Record).where(Record.patient_id == patient.id).order_by(Record.created_at.desc())
    records = list(db.scalars(query).all())
    return PatientPortalDashboardResponse(
        patient=PatientPortalProfile(
            id=patient.id,
            external_id=patient.external_id,
            full_name=patient.full_name,
            age=patient.age,
            gender=patient.gender,
        ),
        reports=[
            VisitReportSummary(
                id=record.id,
                session_id=record.session_id,
                created_at=record.created_at,
                structured_data=record.structured_data or {},
                suggested_diagnosis=record.suggested_diagnosis,
            )
            for record in records
        ],
    )


@router.get("/portal/reports/{record_id}/pdf")
def download_patient_portal_report_pdf(
    record_id: UUID,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    record = db.get(Record, record_id)
    if not record or record.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return _pdf_response(patient=patient, record=record)


def _build_patient_history_response(db: Session, patient_id: UUID) -> PatientHistoryResponse:
    query = select(Record).where(Record.patient_id == patient_id).order_by(Record.created_at.desc())
    records = list(db.scalars(query).all())
    return PatientHistoryResponse(
        patient_id=patient_id,
        records=[
            PatientHistoryRecord(
                id=record.id,
                session_id=record.session_id,
                created_at=record.created_at,
                raw_transcript=record.raw_transcript,
                structured_data=record.structured_data or {},
                suggested_diagnosis=record.suggested_diagnosis,
                missing_fields=record.missing_fields or [],
            )
            for record in records
        ],
    )


def _pdf_response(patient: Patient, record: Record) -> Response:
    pdf_bytes = report_service.build_visit_report_pdf(patient=patient, record=record)
    filename = f"{patient.external_id}-visit-{record.created_at.strftime('%Y%m%d-%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
