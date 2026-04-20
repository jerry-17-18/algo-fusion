import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_doctor, get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientRead

router = APIRouter()
PATIENT_ID_PREFIX = "PAT-"


@router.get("", response_model=list[PatientRead])
def list_patients(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> list[Patient]:
    return list(db.scalars(select(Patient).order_by(Patient.created_at.desc())).all())


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> Patient:
    external_id = (payload.external_id or "").strip() or _generate_patient_external_id(db)
    existing = db.scalar(select(Patient).where(Patient.external_id == external_id))
    if existing:
        raise HTTPException(status_code=409, detail="Patient ID already exists")

    patient = Patient(**payload.model_dump(exclude={"external_id"}), external_id=external_id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _generate_patient_external_id(db: Session) -> str:
    highest_suffix = 1000
    existing_ids = db.scalars(select(Patient.external_id)).all()

    for external_id in existing_ids:
        match = re.fullmatch(rf"{PATIENT_ID_PREFIX}(\d+)", external_id or "")
        if not match:
            continue
        highest_suffix = max(highest_suffix, int(match.group(1)))

    while True:
        highest_suffix += 1
        candidate = f"{PATIENT_ID_PREFIX}{highest_suffix:04d}"
        if not db.scalar(select(Patient).where(Patient.external_id == candidate)):
            return candidate
