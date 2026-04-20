from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models.patient import Patient
from app.schemas.auth import AuthActorRead, PatientLoginRequest, TokenResponse, UserRead
from app.services.auth import authenticate_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/patient-login", response_model=TokenResponse)
def patient_login(
    payload: PatientLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_external_id = payload.patient_id.strip()
    normalized_name = " ".join(payload.full_name.strip().split()).lower()
    if not normalized_external_id or not normalized_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Patient credentials are required")

    patient = db.scalar(
        select(Patient).where(func.lower(Patient.external_id) == normalized_external_id.lower())
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect patient credentials")

    patient_name = " ".join(patient.full_name.split()).lower()
    if patient_name != normalized_name or patient.age != payload.age:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect patient credentials")

    token = create_access_token(
        subject=str(patient.id),
        role="patient",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, user=AuthActorRead.model_validate({**patient.__dict__, "role": "patient"}))
