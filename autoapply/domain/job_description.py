"""Enhanced job description schemas with structured extraction.

This module defines the schema for parsing job descriptions into structured
components that can be matched against candidate profiles. The extraction
identifies must-have vs nice-to-have requirements, which is critical for
prioritizing which evidence to highlight in the tailored resume.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """A single requirement from a job description.
    
    Requirements are the backbone of coverage mapping. Each requirement
    will be matched against the candidate's profile evidence to determine
    coverage and identify gaps.
    
    Attributes:
        text: The requirement as stated in the JD (e.g., "5+ years Python experience")
        category: Type of requirement (technical, soft_skill, experience, certification)
        priority: Must-have requirements are non-negotiable; nice-to-have are bonuses
        keywords: Extracted keywords for semantic matching (e.g., ["Python", "5 years"])
    """

    text: str = Field(min_length=3, description="The requirement text from JD")
    category: Literal["technical", "soft_skill", "experience", "certification", "other"] = Field(
        description="Category of requirement for filtering and prioritization"
    )
    priority: Literal["must_have", "nice_to_have"] = Field(
        description="Whether this is required or preferred"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Key terms for semantic matching (e.g., tech stack, skills)"
    )


class Responsibility(BaseModel):
    """A responsibility or duty described in the job posting.
    
    Responsibilities tell us what the candidate will actually be doing day-to-day.
    We use these to tailor bullets that show relevant past experience doing
    similar work.
    
    Attributes:
        text: The responsibility as stated (e.g., "Lead sprint planning meetings")
        keywords: Action verbs and key terms (e.g., ["lead", "sprint planning", "agile"])
    """

    text: str = Field(min_length=3, description="The responsibility description")
    keywords: List[str] = Field(
        default_factory=list,
        description="Action verbs and key concepts"
    )


class CompanyInfo(BaseModel):
    """Information about the hiring company.
    
    Company context helps us understand industry, size, and culture fit,
    which can inform tone and emphasis in the tailored resume.
    
    Attributes:
        name: Company name
        industry: Industry/sector (e.g., "SaaS", "Healthcare", "Finance")
        size: Employee count range (e.g., "50-200", "1000+")
        stage: Startup stage or maturity (e.g., "Series B", "Public", "Enterprise")
        culture_keywords: Cultural indicators (e.g., ["remote-first", "fast-paced"])
    """

    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    stage: Optional[str] = Field(
        None,
        description="Startup stage (Seed/Series A/B/C) or maturity (Public/Enterprise)"
    )
    culture_keywords: List[str] = Field(
        default_factory=list,
        description="Cultural fit indicators from JD language"
    )


class ExtractedJD(BaseModel):
    """Fully parsed and structured job description.
    
    This is the output of the JD extraction service. It transforms an
    unstructured job posting into structured data that can be used for:
    1. Coverage mapping (matching requirements to profile)
    2. Bullet generation (highlighting relevant experience)
    3. Gap analysis (identifying missing qualifications)
    4. ATS optimization (incorporating required keywords)
    
    The extraction prioritizes conservative inference—if something is ambiguous,
    we leave it empty rather than guessing. This prevents false matches and
    maintains data integrity.
    
    Attributes:
        title: Job title (e.g., "Senior Software Engineer")
        seniority: Experience level required (entry/mid/senior/staff/principal)
        company: Company information if available
        location: Job location (e.g., "San Francisco, CA" or "Remote")
        employment_type: Full-time, part-time, contract, etc.
        salary_range: Salary info if disclosed (e.g., "$120K-$180K")
        
        must_have_requirements: Non-negotiable requirements (critical for coverage)
        nice_to_have_requirements: Preferred but not required
        responsibilities: Day-to-day duties and expectations
        
        required_keywords: Terms that MUST appear in resume for ATS (e.g., tech stack)
        bonus_keywords: Nice-to-have terms for ranking boost
        
        red_flags: Warning signs (e.g., "unpaid internship", "commission only")
        
        raw_text: Original job description for reference
        confidence_scores: How confident we are in each extracted field (0-1)
    """

    # Basic info (always required)
    title: str = Field(min_length=2, description="Job title")
    seniority: Literal["entry", "mid", "senior", "staff", "principal", "unknown"] = Field(
        default="unknown",
        description="Experience level - conservative if unclear"
    )

    # Company info (optional)
    company: Optional[CompanyInfo] = Field(
        None,
        description="Company details if available in JD"
    )

    # Location and employment details
    location: Optional[str] = Field(
        None,
        description="Job location or 'Remote' if remote-eligible"
    )
    employment_type: Literal[
        "full_time", "part_time", "contract", "internship", "unknown"
    ] = Field(default="full_time")

    salary_range: Optional[str] = Field(
        None,
        description="Salary if disclosed (e.g., '$120K-$180K', '€50K-€70K')"
    )

    # Requirements (split by priority for coverage mapping)
    must_have_requirements: List[Requirement] = Field(
        default_factory=list,
        description="Non-negotiable requirements - critical for coverage analysis"
    )
    nice_to_have_requirements: List[Requirement] = Field(
        default_factory=list,
        description="Preferred but not required - bonus points if covered"
    )

    # Responsibilities (used for bullet generation)
    responsibilities: List[Responsibility] = Field(
        default_factory=list,
        description="Day-to-day duties - matched to profile achievements"
    )

    # Keywords for ATS optimization
    required_keywords: List[str] = Field(
        default_factory=list,
        description="Terms that MUST appear in resume (e.g., 'Python', 'AWS', 'Agile')"
    )
    bonus_keywords: List[str] = Field(
        default_factory=list,
        description="Nice-to-have keywords for ranking boost"
    )

    # Warning signs
    red_flags: List[str] = Field(
        default_factory=list,
        description="Warning indicators (e.g., 'unpaid', 'commission only', 'must relocate')"
    )

    # Original text for reference
    raw_text: str = Field(
        description="Original job description text for audit trail"
    )

    # Confidence scoring (for QA and user feedback)
    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence in each extracted field (0-1), e.g., {'seniority': 0.9}"
    )

    def get_all_requirements(self) -> List[Requirement]:
        """Get combined list of all requirements (must-have + nice-to-have).
        
        Useful for bulk operations like coverage mapping across all requirements.
        
        Returns:
            Combined list with must-haves first (for priority ordering)
        """
        return self.must_have_requirements + self.nice_to_have_requirements

    def get_must_have_keywords(self) -> List[str]:
        """Extract keywords from must-have requirements only.
        
        These are the most critical keywords to include in the tailored resume
        for ATS ranking and human review.
        
        Returns:
            List of unique keywords from must-have requirements
        """
        keywords = []
        for req in self.must_have_requirements:
            keywords.extend(req.keywords)
        return list(set(keywords))  # Deduplicate

    def has_red_flags(self) -> bool:
        """Check if job has any warning signs.
        
        Used to alert users before they invest time tailoring for a problematic role.
        
        Returns:
            True if any red flags detected
        """
        return len(self.red_flags) > 0

    def calculate_overall_confidence(self) -> float:
        """Calculate average confidence across all extracted fields.
        
        Lower confidence suggests the JD was ambiguous or poorly formatted,
        which may require manual review or additional clarification from the user.
        
        Returns:
            Average confidence score (0-1)
        """
        if not self.confidence_scores:
            return 0.5  # Default if no scores recorded

        return sum(self.confidence_scores.values()) / len(self.confidence_scores)


class JDExtractionResult(BaseModel):
    """Result from JD extraction service, including metadata.
    
    Wraps the extracted JD with additional context for the extraction process.
    
    Attributes:
        extracted_jd: The parsed job description
        provider_used: Which AI provider did the extraction (e.g., "claude-3-sonnet")
        extraction_time_ms: Time taken for extraction (for performance monitoring)
        ambiguities: List of fields that were unclear and may need user review
        warnings: Non-critical issues noticed during extraction
    """

    extracted_jd: ExtractedJD
    provider_used: str = Field(description="AI provider used (e.g., 'claude-3-sonnet')")
    extraction_time_ms: int = Field(description="Extraction latency in milliseconds")
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Fields that were unclear (e.g., 'Could not determine seniority')"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical issues (e.g., 'Salary range not specified')"
    )
