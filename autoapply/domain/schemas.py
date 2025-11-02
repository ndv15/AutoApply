"""Typed Pydantic models representing domain concepts.

These models define the structure of job specifications, AMOT bullets,
skills lines and resume drafts.  Validation happens automatically on
instantiation, preventing malformed data from propagating through the
system.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    """Specification of a job against which AMOT bullets are generated."""

    title: str = Field(min_length=2)
    company: str = Field(min_length=2)
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class AMOTBullet(BaseModel):
    """Action‑Metric‑Outcome‑Tool bullet proposal.

    Each bullet has a unique ID, the full text, extracted AMOT parts
    (action, metric, outcome and tool) and a status indicating whether it
    is proposed, accepted or rejected.
    """

    id: str
    text: str = Field(min_length=8)
    action: str = Field(min_length=2)
    metric: str = Field(min_length=1)
    outcome: str = Field(min_length=3)
    tool: str = Field(min_length=2)
    status: Literal["proposed", "accepted", "rejected"] = "proposed"


class SkillsLine(BaseModel):
    """Structured representation of a skills line from a resume."""

    category: str = Field(min_length=2)
    items: List[str] = Field(min_length=4, max_length=4)
    raw: str


class ResumeDraft(BaseModel):
    """Stateful draft of a resume being built for a specific job."""

    id: str
    job: JobSpec
    quota: int = Field(gt=0)
    accepted_count: int = 0
    bullets: List[AMOTBullet] = Field(default_factory=list)
    skills: List[SkillsLine] = Field(default_factory=list)