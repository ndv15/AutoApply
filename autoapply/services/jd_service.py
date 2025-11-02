"""Service utilities for job descriptions.

This module provides helper functions to enrich a :class:`JobSpec` from
a free‑form job description.  It uses the lightweight parser defined in
``autoapply.domain.validators.jd`` to extract responsibilities, metrics
and skills.  Enrichment is idempotent: keywords that already exist are
preserved.
"""

from typing import Optional
from autoapply.domain.schemas import JobSpec
from autoapply.domain.validators.jd import parse_job_description


def enrich_job_spec(job: JobSpec, raw_description: Optional[str] = None) -> JobSpec:
    """Return a new JobSpec with inferred keywords, responsibilities and metrics.

    If ``raw_description`` is ``None`` no enrichment is performed.  When
    enrichment occurs, any new skills or metrics found are appended to the
    ``keywords`` field if they are not already present.

    :param job: The original job specification.
    :param raw_description: The free‑form description to parse.
    :returns: A new :class:`JobSpec` with potentially extended keywords.
    """
    if not raw_description:
        return job
    parsed = parse_job_description(raw_description)
    # Combine existing keywords with new skills and metrics, preserving order.
    existing = list(job.keywords)
    for word in parsed.get("skills", []) + parsed.get("metrics", []):
        if word not in existing:
            existing.append(word)
    return JobSpec(
        title=job.title,
        company=job.company,
        responsibilities=job.responsibilities or parsed.get("responsibilities", []),
        requirements=job.requirements,
        keywords=existing,
    )