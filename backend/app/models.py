from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.program_identity import default_program_key


class Scholar(Base):
    __tablename__ = "scholars"

    id: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer)
    previous_degree: Mapped[str | None] = mapped_column(String(300))
    missing_requirements: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_hard_copy: Mapped[bool | None] = mapped_column(Boolean)
    has_soft_copy: Mapped[bool | None] = mapped_column(Boolean)
    department: Mapped[str | None] = mapped_column(String(120), index=True)
    personnel_type: Mapped[str | None] = mapped_column(String(20))
    rank: Mapped[str | None] = mapped_column(String(120))
    tenure: Mapped[str | None] = mapped_column(String(120))
    tenure_years: Mapped[float | None] = mapped_column(Float)
    tenure_note: Mapped[str | None] = mapped_column(Text)
    profile_remarks: Mapped[str | None] = mapped_column(Text)
    data_source: Mapped[str] = mapped_column(String(30), default="Cathedra", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    participations: Mapped[list["FsdpParticipation"]] = relationship(
        back_populates="scholar", cascade="all, delete-orphan"
    )
    requirements: Mapped[list["ScholarRequirement"]] = relationship(
        back_populates="scholar", cascade="all, delete-orphan"
    )

    education_suppressions: Mapped[list["EducationSuppression"]] = relationship(
        cascade="all, delete-orphan"
    )

    education: Mapped[list["ScholarEducation"]] = relationship(
        back_populates="scholar", cascade="all, delete-orphan", order_by="ScholarEducation.id"
    )


class ScholarEducation(Base):
    __tablename__ = "scholar_education"

    id: Mapped[int] = mapped_column(primary_key=True)
    scholar_id: Mapped[int] = mapped_column(ForeignKey("scholars.id"), nullable=False, index=True)
    source_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL")
    )
    level: Mapped[str] = mapped_column(Text, default="", nullable=False)
    degree: Mapped[str] = mapped_column(Text, default="", nullable=False)
    institution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    graduation_year: Mapped[str | None] = mapped_column(Text)
    graduation_year_manual: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    scholar: Mapped[Scholar] = relationship(back_populates="education")


class EducationSuppression(Base):
    __tablename__ = "education_suppressions"
    scholar_id: Mapped[int] = mapped_column(
        ForeignKey("scholars.id", ondelete="CASCADE"), primary_key=True
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), primary_key=True
    )


class CreationRequest(Base):
    __tablename__ = "creation_requests"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("local_users.id", ondelete="CASCADE"), primary_key=True
    )
    request_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    # Keep the non-reusable identity even when the original scholar is deleted.
    scholar_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class ScholarRequirement(Base):
    __tablename__ = "scholar_requirements"
    __table_args__ = (Index("ix_scholar_requirements_due_complete", "due_date", "is_complete"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scholar_id: Mapped[int] = mapped_column(ForeignKey("scholars.id"), nullable=False, index=True)
    requirement_name: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    remarks: Mapped[str | None] = mapped_column(String(500))

    scholar: Mapped[Scholar] = relationship(back_populates="requirements")


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (Index("uq_programs_canonical_key", "canonical_key", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False, unique=True, index=True)
    canonical_key: Mapped[str | None] = mapped_column(Text, default=default_program_key)
    delivering_hei: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    participations: Mapped[list["FsdpParticipation"]] = relationship(back_populates="program")

    @property
    def identity_conflict(self) -> bool:
        return self.canonical_key is None


class FsdpParticipation(Base):
    __tablename__ = "fsdp_participations"
    __table_args__ = (Index("ix_fsdp_participations_status_scholar", "status", "scholar_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scholar_id: Mapped[int] = mapped_column(ForeignKey("scholars.id"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False, index=True)
    delivering_hei: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    contract_completed_on: Mapped[date | None] = mapped_column(Date)
    graduation_date: Mapped[date | None] = mapped_column(Date)
    case_status: Mapped[str] = mapped_column(
        String(20), default="Open", server_default="Open", nullable=False
    )
    start_term: Mapped[str | None] = mapped_column(String(50))
    start_academic_year: Mapped[str | None] = mapped_column(String(20))
    end_term: Mapped[str | None] = mapped_column(String(50))
    end_academic_year: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50), default="On Going", nullable=False, index=True)
    grant_type: Mapped[str | None] = mapped_column(String(100))
    program_category: Mapped[str | None] = mapped_column(String(100))
    application_key: Mapped[str | None] = mapped_column(String(64))
    grant_other: Mapped[str | None] = mapped_column(String(200))
    extension: Mapped[str | None] = mapped_column(String(200))
    remarks: Mapped[str | None] = mapped_column(Text)

    scholar: Mapped[Scholar] = relationship(back_populates="participations")
    program: Mapped[Program] = relationship(back_populates="participations")


class LocalUser(Base):
    __tablename__ = "local_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    __table_args__ = (Index("uq_local_users_username_lower", func.lower(username), unique=True),)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="staff")
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class OfficeLog(Base):
    """An append-only office record, independent from administrator audit history."""

    __tablename__ = "office_logs"
    __table_args__ = (
        Index("ix_office_logs_occurred_id", "occurred_on", "id"),
        Index("uq_office_logs_user_request", "user_id", "request_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scholar_id: Mapped[int | None] = mapped_column(
        ForeignKey("scholars.id", ondelete="SET NULL"), index=True
    )
    scholar_name: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(64))
    payload_digest: Mapped[str | None] = mapped_column(String(64))
    occurred_on: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    document_name: Mapped[str | None] = mapped_column(Text)
    from_department: Mapped[str | None] = mapped_column(Text)
    to_department: Mapped[str | None] = mapped_column(Text)


class LocalSession(Base):
    __tablename__ = "local_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("local_users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_events_created_id", "created_at", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str] = mapped_column(String(80), nullable=False)
    record_type: Mapped[str | None] = mapped_column(String(80))
    record_id: Mapped[int | None] = mapped_column(Integer)
    operation: Mapped[str | None] = mapped_column(String(40))
    changed_fields: Mapped[str | None] = mapped_column(Text)
    subject_scholar_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )


class BackupReview(Base):
    __tablename__ = "backup_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    backup_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    copied_off_device: Mapped[bool] = mapped_column(Boolean, nullable=False)
    restore_tested: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
