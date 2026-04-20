import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import User


def seed_database(db: Session) -> None:
    doctor = db.scalar(select(User).where(User.username == settings.demo_doctor_username))
    if not doctor and settings.seed_demo_data:
        doctor = User(
            username=settings.demo_doctor_username,
            full_name="Demo Doctor",
            hashed_password=get_password_hash(settings.demo_doctor_password),
            role=UserRole.doctor,
        )
        db.add(doctor)
        db.commit()

    patient_count = db.scalar(select(Patient).limit(1))
    if patient_count or not settings.seed_demo_data:
        return

    sample_path = Path(__file__).resolve().parents[2] / "sample_data" / "patients.json"
    if not sample_path.exists():
        return

    patients = json.loads(sample_path.read_text())
    for item in patients:
        db.add(Patient(**item))
    db.commit()
