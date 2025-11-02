"""PDF resume parser using PyPDF2 and pdfplumber.

Extracts text from PDF resumes and performs initial structure detection
for sections like experience, education, skills, etc.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path
import PyPDF2
import pdfplumber
from autoapply.util.logger import get_logger

logger = get_logger(__name__)


class PDFParseResult:
    """Structured result from PDF parsing."""

    def __init__(self) -> None:
        self.raw_text: str = ""
        self.sections: Dict[str, str] = {}
        self.contact_info: Dict[str, Optional[str]] = {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "linkedin": None,
        }
        self.experiences: List[Dict[str, str]] = []
        self.education: List[Dict[str, str]] = []
        self.skills: List[str] = []
        self.confidence: float = 0.0


async def parse_pdf_resume(file_path: str | Path) -> PDFParseResult:
    """Parse a PDF resume and extract structured information.

    Uses pdfplumber for better text extraction with layout awareness,
    falling back to PyPDF2 if needed.

    :param file_path: Path to the PDF file
    :returns: Structured parsing result
    """
    file_path = Path(file_path)
    result = PDFParseResult()

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info(f"Parsing PDF resume: {file_path}")

    try:
        # Primary: Use pdfplumber for better text extraction
        with pdfplumber.open(file_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

            result.raw_text = "\n\n".join(pages_text)

    except Exception as e:
        logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
        # Fallback: Use PyPDF2
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)

                result.raw_text = "\n\n".join(pages_text)

        except Exception as e2:
            logger.error(f"Both PDF parsers failed: {e2}")
            raise ValueError(f"Unable to parse PDF: {e2}")

    if not result.raw_text.strip():
        raise ValueError("PDF appears to be empty or contains only images")

    # Extract structured information
    _extract_contact_info(result)
    _extract_sections(result)
    _extract_experiences(result)
    _extract_education(result)
    _extract_skills(result)

    # Calculate confidence score based on what we found
    result.confidence = _calculate_confidence(result)

    logger.info(
        f"PDF parsed: {len(result.experiences)} experiences, "
        f"{len(result.education)} education, confidence={result.confidence:.2f}"
    )

    return result


def _extract_contact_info(result: PDFParseResult) -> None:
    """Extract contact information from the resume text."""
    text = result.raw_text

    # Email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text, re.IGNORECASE)
    if email_match:
        result.contact_info["email"] = email_match.group(0)

    # Phone (US format primarily, but flexible)
    phone_patterns = [
        r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # (123) 456-7890 or variations
        r"\+\d{1,3}[-.\s]?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}",  # International
    ]
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            result.contact_info["phone"] = phone_match.group(0)
            break

    # LinkedIn
    linkedin_match = re.search(
        r"linkedin\.com/in/[\w-]+|linkedin\.com/[\w-]+", text, re.IGNORECASE
    )
    if linkedin_match:
        result.contact_info["linkedin"] = linkedin_match.group(0)

    # Name (heuristic: first non-empty line, usually capitalized)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if lines:
        first_line = lines[0]
        # If it looks like a name (2-4 words, capitalized, no @ or numbers)
        if (
            2 <= len(first_line.split()) <= 4
            and first_line[0].isupper()
            and "@" not in first_line
            and not any(char.isdigit() for char in first_line)
        ):
            result.contact_info["name"] = first_line


def _extract_sections(result: PDFParseResult) -> None:
    """Split resume into major sections (Experience, Education, Skills, etc.)."""
    text = result.raw_text

    # Common section headers
    section_patterns = {
        "experience": r"(?i)(professional\s+)?experience|work\s+history|employment",
        "education": r"(?i)education|academic\s+background",
        "skills": r"(?i)(technical\s+)?skills|technologies|competencies",
        "projects": r"(?i)projects?|portfolio",
        "certifications": r"(?i)certifications?|licenses",
        "summary": r"(?i)summary|profile|objective",
    }

    # Find section boundaries
    section_matches = []
    for section_name, pattern in section_patterns.items():
        for match in re.finditer(pattern, text):
            section_matches.append((match.start(), section_name, match.group(0)))

    section_matches.sort(key=lambda x: x[0])

    # Extract text for each section
    for i, (start_pos, section_name, header) in enumerate(section_matches):
        end_pos = section_matches[i + 1][0] if i + 1 < len(section_matches) else len(text)
        section_text = text[start_pos:end_pos].strip()
        result.sections[section_name] = section_text


def _extract_experiences(result: PDFParseResult) -> None:
    """Extract work experience entries."""
    experience_text = result.sections.get("experience", "")
    if not experience_text:
        return

    # Pattern: Company/Title line followed by dates and bullets
    # This is a simplified heuristic; real-world parsing needs ML
    lines = experience_text.split("\n")

    current_exp: Optional[Dict[str, str]] = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line contains dates (MM/YYYY or Month YYYY pattern)
        date_pattern = r"\d{1,2}/\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
        has_date = bool(re.search(date_pattern, line, re.IGNORECASE))

        # If line has dates, likely a title/company line
        if has_date and "|" not in line:
            if current_exp:
                result.experiences.append(current_exp)

            current_exp = {
                "raw_header": line,
                "bullets": [],
            }

        # If line starts with bullet character or dash, it's a bullet
        elif current_exp and (line.startswith("•") or line.startswith("-") or line.startswith("*")):
            bullet = line.lstrip("•-* ").strip()
            if bullet:
                current_exp["bullets"].append(bullet)

    # Add last experience
    if current_exp:
        result.experiences.append(current_exp)


def _extract_education(result: PDFParseResult) -> None:
    """Extract education entries."""
    education_text = result.sections.get("education", "")
    if not education_text:
        return

    lines = [line.strip() for line in education_text.split("\n") if line.strip()]

    current_edu: Optional[Dict[str, str]] = None

    for line in lines:
        # Look for degree keywords
        degree_keywords = ["bachelor", "master", "phd", "associate", "b.s.", "m.s.", "b.a.", "m.a."]
        has_degree = any(keyword in line.lower() for keyword in degree_keywords)

        # Look for university keywords
        university_keywords = ["university", "college", "institute", "school"]
        has_university = any(keyword in line.lower() for keyword in university_keywords)

        if has_degree or has_university:
            if current_edu:
                result.education.append(current_edu)

            current_edu = {
                "raw_line": line,
                "details": [],
            }

        elif current_edu and (line.startswith("•") or line.startswith("-") or "GPA" in line):
            detail = line.lstrip("•-* ").strip()
            if detail:
                current_edu["details"].append(detail)

    if current_edu:
        result.education.append(current_edu)


def _extract_skills(result: PDFParseResult) -> None:
    """Extract skills section."""
    skills_text = result.sections.get("skills", "")
    if not skills_text:
        return

    # Skills are often comma-separated or pipe-separated
    # Remove section header
    lines = skills_text.split("\n")[1:]  # Skip header line

    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith("skills"):
            continue

        # Split by common delimiters
        if "|" in line:
            skills = [s.strip() for s in line.split("|")]
        elif "," in line:
            skills = [s.strip() for s in line.split(",")]
        elif "•" in line or "–" in line:
            skills = [s.strip() for s in re.split(r"[•–]", line)]
        else:
            skills = [line]

        result.skills.extend([s for s in skills if s and not s.endswith(":")])


def _calculate_confidence(result: PDFParseResult) -> float:
    """Calculate confidence score based on extracted data."""
    score = 0.0

    # Contact info (30 points)
    if result.contact_info.get("name"):
        score += 10
    if result.contact_info.get("email"):
        score += 10
    if result.contact_info.get("phone"):
        score += 5
    if result.contact_info.get("linkedin"):
        score += 5

    # Experiences (40 points)
    if result.experiences:
        score += min(40, len(result.experiences) * 10)

    # Education (20 points)
    if result.education:
        score += min(20, len(result.education) * 10)

    # Skills (10 points)
    if result.skills:
        score += 10

    return min(100.0, score) / 100.0
