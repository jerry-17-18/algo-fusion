"""Initial schema for clinical voice AI."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("doctor", name="user_role")
    session_status = sa.Enum("active", "completed", name="session_status")
    user_role.create(op.get_bind(), checkfirst=True)
    session_status.create(op.get_bind(), checkfirst=True)
    user_role_existing = postgresql.ENUM("doctor", name="user_role", create_type=False)
    session_status_existing = postgresql.ENUM(
        "active",
        "completed",
        name="session_status",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_existing, nullable=False, server_default="doctor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(length=24), nullable=True),
        sa.Column("preferred_language", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patients_external_id", "patients", ["external_id"], unique=True)
    op.create_index("ix_patients_full_name", "patients", ["full_name"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", session_status_existing, nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("detected_languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
    )
    op.create_index("ix_sessions_patient_id", "sessions", ["patient_id"], unique=False)
    op.create_index("ix_sessions_doctor_id", "sessions", ["doctor_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)

    op.create_table(
        "records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_transcript", sa.Text(), nullable=False, server_default=""),
        sa.Column("structured_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("suggested_diagnosis", sa.String(length=255), nullable=True),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("rag_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.UniqueConstraint("session_id", name="uq_records_session_id"),
    )
    op.create_index("ix_records_patient_id", "records", ["patient_id"], unique=False)
    op.create_index("ix_records_session_id", "records", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_records_session_id", table_name="records")
    op.drop_index("ix_records_patient_id", table_name="records")
    op.drop_table("records")

    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_doctor_id", table_name="sessions")
    op.drop_index("ix_sessions_patient_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_patients_full_name", table_name="patients")
    op.drop_index("ix_patients_external_id", table_name="patients")
    op.drop_table("patients")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    sa.Enum(name="session_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
