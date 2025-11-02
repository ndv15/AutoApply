"""SQLAlchemy database models for persistent storage.

All models use UUID primary keys and include created_at/updated_at timestamps.
Sensitive fields (PII) are stored encrypted.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    JSON,
    LargeBinary,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from autoapply.store.database import Base


class ProfileModel(Base):
    """User profile with personal and professional information."""

    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Contact info (encrypted)
    full_name_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source and metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, linkedin, manual

    # Privacy & consent
    consent_to_store: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_to_learning: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    experiences: Mapped[List["ExperienceModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    education: Mapped[List["EducationModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[List["SkillCategoryModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[List["ProjectModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[List["CertificationModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    drafts: Mapped[List["ResumeDraftModel"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ExperienceModel(Base):
    """Work experience entry with bullets and evidence tracking."""

    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Date range
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # Bullets stored as JSON array
    bullets: Mapped[List[str]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Categories for achievement types
    categories: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="experiences")


class EducationModel(Base):
    """Education entry."""

    __tablename__ = "education"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Date range
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # Optional details
    gpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    honors: Mapped[List[str]] = mapped_column(JSON, default=list)
    relevant_coursework: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="education")


class SkillCategoryModel(Base):
    """Categorized skills."""

    __tablename__ = "skill_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    skills: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="skills")


class ProjectModel(Base):
    """Project with achievements and evidence."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Technologies as JSON array
    technologies: Mapped[List[str]] = mapped_column(JSON, default=list)
    achievements: Mapped[List[str]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Optional date range
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="projects")


class CertificationModel(Base):
    """Professional certification or license."""

    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(String(200), nullable=False)

    date_issued: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiration_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="certifications")


class ResumeDraftModel(Base):
    """Resume draft being generated for a specific job."""

    __tablename__ = "resume_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)  # References JobModel

    # Quota and progress
    quota: Mapped[int] = mapped_column(nullable=False)
    accepted_count: Mapped[int] = mapped_column(default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="draft"
    )  # draft, generating, complete, exported

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped["ProfileModel"] = relationship(back_populates="drafts")
    bullets: Mapped[List["BulletModel"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )


class JobModel(Base):
    """Job specification that bullets are generated for."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Basic info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Parsed job details as JSON
    responsibilities: Mapped[List[str]] = mapped_column(JSON, default=list)
    requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Raw JD text
    raw_jd: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BulletModel(Base):
    """Generated AMOT bullet (proposed, accepted, or rejected)."""

    __tablename__ = "bullets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    draft_id: Mapped[str] = mapped_column(ForeignKey("resume_drafts.id"), nullable=False)

    # AMOT components
    text: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    metric: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(200), nullable=False)
    tool: Mapped[str] = mapped_column(String(200), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="proposed"
    )  # proposed, accepted, rejected

    # Provenance: evidence IDs that support this bullet
    evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    draft: Mapped["ResumeDraftModel"] = relationship(back_populates="bullets")


class AuditLogModel(Base):
    """Audit log for sensitive operations and compliance."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "profile_created"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "profile"
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Who did it (user ID, system, etc.)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)

    # Additional context as JSON
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
