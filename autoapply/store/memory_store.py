"""In‑memory store for resume drafts.

This store keeps track of drafts, bullets and skills in a module‑level
dictionary keyed by draft ID.  It is intentionally simple and not
thread‑safe; for more sophisticated use cases consider integrating a
database or persistent backend.
"""

from typing import Dict, List
from autoapply.domain.schemas import ResumeDraft, AMOTBullet, SkillsLine
from uuid import uuid4


_DRAFTS: Dict[str, ResumeDraft] = {}


def create_draft(partial: dict) -> ResumeDraft:
    """Create a new draft and store it in memory.

    :param partial: Keyword arguments to instantiate a :class:`ResumeDraft`.
    :returns: The created draft with a generated UUID.
    """
    draft = ResumeDraft(id=str(uuid4()), bullets=[], skills=[], accepted_count=0, **partial)
    _DRAFTS[draft.id] = draft
    return draft


def get_draft(draft_id: str) -> ResumeDraft:
    """Retrieve a draft by ID.

    :param draft_id: The identifier of the draft to fetch.
    :returns: The corresponding :class:`ResumeDraft`.
    :raises KeyError: If the draft ID is unknown.
    """
    draft = _DRAFTS.get(draft_id)
    if not draft:
        raise KeyError("Draft not found")
    return draft


def upsert_bullets(draft_id: str, new_bullets: List[AMOTBullet]) -> None:
    """Insert or update bullets for a draft.

    If a bullet with the same ID already exists, it will be replaced.
    Otherwise it will be appended.  Bullets retain their original order
    based on the values in ``new_bullets``.
    """
    draft = get_draft(draft_id)
    by_id: Dict[str, AMOTBullet] = {b.id: b for b in draft.bullets}
    for bullet in new_bullets:
        by_id[bullet.id] = bullet
    draft.bullets = list(by_id.values())
    _DRAFTS[draft.id] = draft


def set_accepted(draft_id: str, ids: List[str]) -> None:
    """Mark bullets as accepted and update accepted count."""
    draft = get_draft(draft_id)
    for bullet in draft.bullets:
        if bullet.id in ids:
            bullet.status = "accepted"
    draft.accepted_count = sum(1 for b in draft.bullets if b.status == "accepted")
    _DRAFTS[draft.id] = draft


def set_rejected(draft_id: str, ids: List[str]) -> None:
    """Mark bullets as rejected without affecting accepted count."""
    draft = get_draft(draft_id)
    for bullet in draft.bullets:
        if bullet.id in ids:
            bullet.status = "rejected"
    _DRAFTS[draft.id] = draft


def set_skills(draft_id: str, skills: List[SkillsLine]) -> None:
    """Update the skills associated with a draft."""
    draft = get_draft(draft_id)
    draft.skills = skills
    _DRAFTS[draft.id] = draft