"""Profile ingestion from multiple sources.

This module handles parsing resumes from PDF, DOCX, LinkedIn profiles,
and manual input, normalizing everything to the Profile schema.
"""

from autoapply.ingestion.pdf_parser import parse_pdf_resume
from autoapply.ingestion.docx_parser import parse_docx_resume
from autoapply.ingestion.linkedin_scraper import scrape_linkedin_profile
from autoapply.ingestion.normalizer import normalize_to_profile

__all__ = [
    "parse_pdf_resume",
    "parse_docx_resume",
    "scrape_linkedin_profile",
    "normalize_to_profile",
]
