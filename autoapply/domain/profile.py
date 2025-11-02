"""Enhanced profile schemas with evidence tracking for provenance.

These models represent a user's professional profile parsed from resumes,
LinkedIn, or manual input. Each piece of information is tracked with a
stable evidence ID for later provenance verification.
"""

from typing import List, Optional, Literal
from datetime import date
from pydantic import BaseModel, Field, EmailStr


class DateRange(BaseModel):
    """Date range for employment, education, etc."""

    start: date
    end: Optional[date] = None  # None indicates "Present"
    is_current: bool = False

    def __str__(self) -> str:
        start_str = self.start.strftime("%m/%Y")
        end_str = "Present" if self.is_current else self.end.strftime("%m/%Y") if self.end else ""
        return f"{start_str} - {end_str}"


class ContactInfo(BaseModel):
    """Contact information with PII that needs encryption."""

    full_name: str = Field(min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None  # e.g., "San Francisco, CA"
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None


class Experience(BaseModel):
    """Work experience with evidence tracking.

    Each bullet point is an evidence span that can be referenced
    when generating tailored resume bullets.
    """

    id: str  # Stable unique ID (UUID)
    company: str = Field(min_length=2)
    title: str = Field(min_length=2)
    location: Optional[str] = None
    dates: DateRange
    bullets: List[str] = Field(default_factory=list)
    # Each bullet gets its own evidence ID for provenance tracking
    evidence_ids: List[str] = Field(default_factory=list)
    # Optional: categorize by achievement type
    categories: List[Literal["leadership", "technical", "sales", "process"]] = Field(
        default_factory=list
    )


class Education(BaseModel):
    """Educational background."""

    id: str
    institution: str = Field(min_length=2)
    degree: str = Field(min_length=2)  # e.g., "Bachelor of Science in Computer Science"
    location: Optional[str] = None
    dates: DateRange
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    honors: List[str] = Field(default_factory=list)
    relevant_coursework: List[str] = Field(default_factory=list)


class Project(BaseModel):
    """Project with technical details."""

    id: str
    name: str = Field(min_length=2)
    description: str = Field(min_length=10)
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    dates: Optional[DateRange] = None
    achievements: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class Certification(BaseModel):
    """Professional certification or license."""

    id: str
    name: str = Field(min_length=2)
    issuer: str = Field(min_length=2)
    date_issued: Optional[date] = None
    expiration_date: Optional[date] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class SkillCategory(BaseModel):
    """Categorized skills for better organization."""

    category: str = Field(min_length=2)  # e.g., "Programming Languages"
    skills: List[str] = Field(min_length=1)


class Profile(BaseModel):
    """Complete user profile with all professional information.

    This is the canonical representation of a user's background,
    regardless of input source (PDF, DOCX, LinkedIn, manual).
    """

    id: str  # User/profile UUID
    contact: ContactInfo
    summary: Optional[str] = Field(None, max_length=500)
    experiences: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[SkillCategory] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)

    # Metadata
    source: Literal["pdf", "docx", "linkedin", "manual"] = "manual"
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    # Privacy & compliance
    consent_to_store: bool = False
    consent_to_learning: bool = False


class EvidenceSpan(BaseModel):
    """A trackable piece of evidence from the profile.

    Used for provenance tracking when generating resume bullets.
    Each claim in a generated bullet must link back to evidence.
    """

    id: str  # Stable UUID
    source_type: Literal["experience", "education", "project", "certification"]
    source_id: str  # FK to the parent entity
    text: str  # The actual evidence text (bullet, achievement, etc.)
    category: Optional[str] = None
    # Semantic embedding for matching (optional, added later)
    embedding: Optional[List[float]] = None


class ParsedProfile(BaseModel):
    """Result of parsing with confidence scores.

    Used to show users what was auto-extracted so they can
    correct any parsing errors before saving.
    """

    profile: Profile
    confidence_scores: dict[str, float]  # field_name -> 0-1 confidence
    ambiguities: List[str]  # Fields that need user clarification
    warnings: List[str]  # Potential issues detected
