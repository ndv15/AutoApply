"""Service functions for generating and validating AMOT bullets."""

from uuid import uuid4
from typing import List, Optional
from autoapply.providers.registry import get_providers
from autoapply.domain.validators.amot import parse_amot
from autoapply.domain.schemas import AMOTBullet, ResumeDraft
from autoapply.store.memory_store import upsert_bullets


async def propose_bullets(
    draft: ResumeDraft,
    count: int,
    negative_phrases: Optional[List[str]] | None = None,
) -> List[AMOTBullet]:
    """Generate and validate a batch of AMOT bullets for a draft.

    Generation and reranking are delegated to the configured providers.
    After generation, each bullet is validated using the AMOT parser; if
    any bullet fails validation, a :class:`ValueError` is raised.  Valid
    bullets are stored in the in‑memory store and returned to the caller.

    :param draft: The draft for which to generate bullets.
    :param count: The number of bullets to generate.
    :param negative_phrases: Optional phrases to avoid in generation.
    :returns: A list of validated :class:`AMOTBullet` objects.
    """
    providers = get_providers()
    gen_resp = await providers["generator"].generate(
        {
            "job": draft.job,
            "count": count,
            "constraints": {"negativePhrases": negative_phrases or []},
        }
    )
    ranked = await providers["rerank"].rerank(gen_resp["bullets"], draft.job.title)
    validated: List[AMOTBullet] = []
    for text in ranked:
        parts = parse_amot(text)
        validated.append(
            AMOTBullet(
                id=str(uuid4()),
                text=text,
                action=parts["action"],
                metric=parts["metric"],
                outcome=parts["outcome"],
                tool=parts["tool"],
                status="proposed",
            )
        )
    upsert_bullets(draft.id, validated)
    return validated