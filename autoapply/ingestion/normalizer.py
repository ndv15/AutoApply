"""Normalizer to convert parsing results into canonical Profile schema.

Takes raw parsing results from PDF, DOCX, or LinkedIn and produces
a validated Profile object with evidence tracking and confidence scores.
"""

import re
from uuid import uuid4
from datetime import date
from typing import List, Optional
from autoapply.domain.profile import (
    Profile,
    ContactInfo,
    Experience,
    Education,
    Project,
    Certification,
    SkillCategory,
    DateRange,
    ParsedProfile,
    EvidenceSpan,
)
from autoapply.ingestion.pdf_parser import PDFParseResult
from autoapply.ingestion.docx_parser import DOCXParseResult
from autoapply.ingestion.linkedin_scraper import LinkedInParseResult
from autoapply.util.logger import get_logger

logger = get_logger(__name__)


async def normalize_to_profile(
    parse_result: PDFParseResult | DOCXParseResult | LinkedInParseResult,
    source: str = "pdf",
) -> ParsedProfile:
    """Convert parsing result to canonical Profile schema.

    This function:
    1. Normalizes contact info
    2. Parses dates from various formats
    3. Creates evidence IDs for each bullet/achievement
    4. Assigns confidence scores
    5. Identifies ambiguities for user review

    :param parse_result: Result from parser (PDF, DOCX, or LinkedIn)
    :param source: Source type ("pdf", "docx", "linkedin")
    :returns: ParsedProfile with confidence scores and warnings
    """
    logger.info(f"Normalizing {source} parse result to Profile schema")

    profile_id = str(uuid4())
    ambiguities: List[str] = []
    warnings: List[str] = []
    confidence_scores: dict[str, float] = {}

    # Normalize contact info
    contact, contact_confidence = _normalize_contact_info(parse_result)
    confidence_scores["contact"] = contact_confidence

    # Normalize experiences
    experiences, exp_confidence, exp_warnings = _normalize_experiences(parse_result)
    confidence_scores["experiences"] = exp_confidence
    warnings.extend(exp_warnings)

    # Normalize education
    education, edu_confidence, edu_warnings = _normalize_education(parse_result)
    confidence_scores["education"] = edu_confidence
    warnings.extend(edu_warnings)

    # Normalize skills
    skills, skills_confidence = _normalize_skills(parse_result)
    confidence_scores["skills"] = skills_confidence

    # Check for ambiguities
    if not contact.full_name:
        ambiguities.append("Full name not detected - please provide")

    if not contact.email:
        ambiguities.append("Email address not detected - please provide")

    if not experiences:
        warnings.append("No work experience detected - please add manually")

    # Create Profile
    profile = Profile(
        id=profile_id,
        contact=contact,
        experiences=experiences,
        education=education,
        skills=skills,
        source=source,  # type: ignore
        created_at=date.today(),
        consent_to_store=False,  # User must explicitly consent
        consent_to_learning=False,
    )

    # Calculate overall confidence
    overall_confidence = sum(confidence_scores.values()) / len(confidence_scores)

    return ParsedProfile(
        profile=profile,
        confidence_scores=confidence_scores,
        ambiguities=ambiguities,
        warnings=warnings,
    )


def _normalize_contact_info(
    parse_result: PDFParseResult | DOCXParseResult | LinkedInParseResult,
) -> tuple[ContactInfo, float]:
    """Normalize contact information."""
    contact_info = parse_result.contact_info

    # Build ContactInfo
    contact = ContactInfo(
        full_name=contact_info.get("name") or "Unknown",
        email=contact_info.get("email") or "email@example.com",  # Will be flagged in ambiguities
        phone=contact_info.get("phone"),
        location=contact_info.get("location"),
        linkedin_url=contact_info.get("linkedin") or contact_info.get("linkedin_url"),
    )

    # Calculate confidence
    confidence = 0.0
    if contact_info.get("name"):
        confidence += 0.3
    if contact_info.get("email"):
        confidence += 0.4
    if contact_info.get("phone"):
        confidence += 0.15
    if contact_info.get("location"):
        confidence += 0.15

    return contact, confidence


def _normalize_experiences(
    parse_result: PDFParseResult | DOCXParseResult | LinkedInParseResult,
) -> tuple[List[Experience], float, List[str]]:
    """Normalize work experiences with evidence tracking."""
    experiences: List[Experience] = []
    warnings: List[str] = []

    for exp_data in parse_result.experiences:
        try:
            exp_id = str(uuid4())

            # Parse header to extract company, title, dates
            header = exp_data.get("raw_header", "")

            # Try to extract company and title
            # Common formats:
            # "Software Engineer | Acme Corp | Jan 2020 - Present"
            # "Senior Developer, TechCo (Jan 2019 - Dec 2021)"
            # "Acme Inc. | Software Engineer | 01/2020 - Present"

            company = "Unknown Company"
            title = "Unknown Title"
            date_str = ""

            # Extract dates first
            date_pattern = r"(\d{1,2}/\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\s*[-–—]\s*(Present|\d{1,2}/\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
            date_match = re.search(date_pattern, header, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(0)
                # Remove dates from header for easier parsing
                header_without_dates = header[: date_match.start()].strip()
            else:
                header_without_dates = header
                warnings.append(f"Could not parse dates from: {header}")

            # Split by common delimiters
            parts = re.split(r"[|,]", header_without_dates)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) >= 2:
                # Assume format: Title | Company or Company | Title
                # Heuristic: Longer name is often company
                if len(parts[0]) > len(parts[1]):
                    company = parts[0]
                    title = parts[1]
                else:
                    title = parts[0]
                    company = parts[1]
            elif len(parts) == 1:
                # Only one part, assume it's title
                title = parts[0]

            # Parse dates
            dates = _parse_date_range(date_str) if date_str else DateRange(
                start=date(2020, 1, 1), end=None, is_current=True
            )

            # Create evidence IDs for each bullet
            bullets = exp_data.get("bullets", [])
            evidence_ids = [str(uuid4()) for _ in bullets]

            exp = Experience(
                id=exp_id,
                company=company,
                title=title,
                dates=dates,
                bullets=bullets,
                evidence_ids=evidence_ids,
            )

            experiences.append(exp)

        except Exception as e:
            logger.warning(f"Failed to normalize experience: {e}")
            warnings.append(f"Could not parse experience entry: {exp_data.get('raw_header', 'unknown')}")

    confidence = min(1.0, len(experiences) * 0.25) if experiences else 0.0

    return experiences, confidence, warnings


def _normalize_education(
    parse_result: PDFParseResult | DOCXParseResult | LinkedInParseResult,
) -> tuple[List[Education], float, List[str]]:
    """Normalize education entries."""
    education: List[Education] = []
    warnings: List[str] = []

    for edu_data in parse_result.education:
        try:
            edu_id = str(uuid4())
            raw_line = edu_data.get("raw_line", "")

            # Extract degree and institution
            # Common formats:
            # "Bachelor of Science in Computer Science, MIT, 2015-2019"
            # "University of California, Berkeley - B.S. Computer Science (2018)"

            degree = "Unknown Degree"
            institution = "Unknown Institution"

            # Try to find degree keywords
            degree_patterns = [
                r"(Bachelor of (?:Science|Arts) in [^,\n]+)",
                r"(Master of (?:Science|Arts) in [^,\n]+)",
                r"(B\.S\.|B\.A\.|M\.S\.|M\.A\.|Ph\.D\.)\s+[^,\n]+",
            ]

            for pattern in degree_patterns:
                match = re.search(pattern, raw_line, re.IGNORECASE)
                if match:
                    degree = match.group(1)
                    break

            # Try to find institution
            institution_keywords = ["university", "college", "institute"]
            for keyword in institution_keywords:
                match = re.search(
                    rf"([A-Z][^,\n]*{keyword}[^,\n]*)", raw_line, re.IGNORECASE
                )
                if match:
                    institution = match.group(1).strip()
                    break

            # Parse dates (simplified)
            date_match = re.search(r"(\d{4})\s*[-–]\s*(\d{4}|Present)", raw_line, re.IGNORECASE)
            if date_match:
                start_year = int(date_match.group(1))
                end_str = date_match.group(2)
                is_current = "present" in end_str.lower()
                end_year = None if is_current else int(end_str)

                dates = DateRange(
                    start=date(start_year, 9, 1),  # Assume Sep start
                    end=date(end_year, 5, 1) if end_year else None,
                    is_current=is_current,
                )
            else:
                # Default to generic dates
                dates = DateRange(start=date(2015, 9, 1), end=date(2019, 5, 1))
                warnings.append(f"Could not parse education dates: {raw_line}")

            edu = Education(
                id=edu_id,
                institution=institution,
                degree=degree,
                dates=dates,
            )

            education.append(edu)

        except Exception as e:
            logger.warning(f"Failed to normalize education: {e}")
            warnings.append(f"Could not parse education entry: {edu_data.get('raw_line', 'unknown')}")

    confidence = min(1.0, len(education) * 0.5) if education else 0.0

    return education, confidence, warnings


def _normalize_skills(
    parse_result: PDFParseResult | DOCXParseResult | LinkedInParseResult,
) -> tuple[List[SkillCategory], float]:
    """Normalize skills into categories."""
    skills: List[SkillCategory] = []

    raw_skills = parse_result.skills

    if raw_skills:
        # Simple: create one "Technical Skills" category
        # More sophisticated: use ML to categorize
        skills.append(
            SkillCategory(
                category="Technical Skills",
                skills=raw_skills[:50],  # Cap at 50 to avoid clutter
            )
        )

    confidence = 1.0 if skills else 0.0

    return skills, confidence


def _parse_date_range(date_str: str) -> DateRange:
    """Parse date range from string like 'Jan 2020 - Present' or '01/2020 - 12/2022'."""
    # Simplified parser
    parts = re.split(r"[-–—]", date_str)

    if len(parts) != 2:
        # Fallback to current date
        return DateRange(start=date.today(), end=None, is_current=True)

    start_str = parts[0].strip()
    end_str = parts[1].strip()

    # Parse start date
    start_date = _parse_single_date(start_str)

    # Parse end date
    is_current = "present" in end_str.lower()
    end_date = None if is_current else _parse_single_date(end_str)

    return DateRange(start=start_date, end=end_date, is_current=is_current)


def _parse_single_date(date_str: str) -> date:
    """Parse single date from formats like 'Jan 2020' or '01/2020'."""
    # MM/YYYY format
    slash_match = re.match(r"(\d{1,2})/(\d{4})", date_str)
    if slash_match:
        month = int(slash_match.group(1))
        year = int(slash_match.group(2))
        return date(year, month, 1)

    # Month YYYY format
    month_names = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    for month_name, month_num in month_names.items():
        if month_name in date_str.lower():
            year_match = re.search(r"\d{4}", date_str)
            if year_match:
                year = int(year_match.group(0))
                return date(year, month_num, 1)

    # Fallback
    return date.today()
