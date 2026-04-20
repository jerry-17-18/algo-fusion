import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (UniqueConstraint("session_id", name="uq_records_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    raw_transcript: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggested_diagnosis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    missing_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    rag_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    patient: Mapped["Patient"] = relationship(back_populates="records")
    session: Mapped["ClinicalSession"] = relationship(back_populates="record")

