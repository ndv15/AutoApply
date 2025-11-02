"""Simple parser for job descriptions.

This module contains heuristics to extract responsibilities, infer skills
based on keywords and capture metrics from a free‑form job description.
It is intentionally lightweight and does not attempt to fully understand
natural language; it provides just enough signal for providers to improve
their generation and reranking.
"""

from typing import List, Dict, Any
import re


# List of keywords to infer potential skills from the job description.
HINTS: List[str] = [
    "Python",
    "SQL",
    "Kubernetes",
    "AWS",
    "Airflow",
    "Tableau",
    "TypeScript",
]


def parse_job_description(text: str) -> Dict[str, Any]:
    """Parse a job description into structured hints.

    Extracts lines that look like bullet points, infers skills based on
    presence of hints, and collects up to ten numeric metrics found in
    the text.

    :param text: The job description to parse.
    :returns: A dictionary with keys ``skills``, ``responsibilities`` and
      ``metrics``.  If no values are found for a key, an empty list is
      returned.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    responsibilities: List[str] = [
        line.lstrip("-*• ").strip() for line in lines if line[:1] in "-*•"
    ]
    skills = list({hint for hint in HINTS if hint.lower() in text.lower()})
    metrics = (
        re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%?", text) or []
    )[:10]
    return {
        "skills": skills,
        "responsibilities": responsibilities,
        "metrics": metrics,
    }