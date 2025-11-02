"""Orchestration layer tying together providers, services and state."""

from typing import List, Optional
from autoapply.providers.registry import get_providers
from autoapply.store.memory_store import (
    create_draft,
    get_draft,
    set_accepted,
    set_rejected,
)
from autoapply.services.quota_service import remaining_quota
from autoapply.services.bullet_service import propose_bullets
from autoapply.services.preview_service import render_preview
from autoapply.orchestration.state_machine import transition, State
from autoapply.domain.validators.skills import validate_skills_line
from autoapply.domain.schemas import SkillsLine


class Orchestrator:
    """High‑level orchestrator managing the resume tailoring flow."""

    def __init__(
        self,
        job: dict,
        quota: int,
        skills: Optional[List[str]] | None = None,
        raw_jd: Optional[str] | None = None,
    ) -> None:
        # Create a draft with the provided job and quota.
        draft = create_draft({"job": job, "quota": quota})
        self.draft_id = draft.id
        self.state: State = "Idle"
        # Parse and set skills if provided.
        if skills:
            parsed = [SkillsLine(**validate_skills_line(s)) for s in skills]
            d = get_draft(self.draft_id)
            d.skills = parsed
        # Raw job descriptions could be enriched here via jd_service if needed.

    async def start(self) -> None:
        """Kick off the research phase."""
        providers = get_providers()
        self.state = transition(self.state, "START")
        await providers["research"].research(get_draft(self.draft_id).job)
        self.state = transition("Researching", "RESEARCHED")

    async def generate_or_stop(self) -> None:
        """Generate a new batch of bullets or finish if the quota is met."""
        draft = get_draft(self.draft_id)
        rem, done = remaining_quota(self.draft_id, draft.quota)
        if done:
            # If quota is met, move directly to Done.
            self.state = transition("Validating", "VALIDATED")
            self.state = transition("QuotaGate", "FINISH")
            return
        # Generate bullets equal to the remaining count.
        await propose_bullets(draft, rem)
        # Transition through generating and validating states to quota gate.
        self.state = transition("Generating", "GENERATED")
        self.state = transition("Validating", "VALIDATED")
        self.state = transition("QuotaGate", "PRESENT")

    async def commit(self, accept: List[str], reject: List[str]) -> None:
        """Commit accepted and rejected bullets and update the preview."""
        set_accepted(self.draft_id, accept)
        set_rejected(self.draft_id, reject)
        # Render preview after commit.
        render_preview(self.draft_id)
        draft = get_draft(self.draft_id)
        rem, done = remaining_quota(self.draft_id, draft.quota)
        # Transition to committing state.
        self.state = transition("Presenting", "COMMIT")
        if done:
            # All bullets accepted; finish.
            self.state = transition("Committing", "FINISH")
        else:
            # More bullets needed; prepare to regenerate.
            self.state = transition("Committing", "RETRY")

    async def regenerate_if_needed(self) -> None:
        """Regenerate bullets based on rejected content if quota not met."""
        draft = get_draft(self.draft_id)
        # Build negative phrases from the first three words of rejected bullets.
        negatives = [
            " ".join(b.text.split(" ")[:3]) for b in draft.bullets if b.status == "rejected"
        ]
        # Generate at least one bullet, but no more than required to hit the quota.
        count = max(1, draft.quota - draft.accepted_count)
        await propose_bullets(draft, count, negatives)
        # Transition through regeneration states back to present.
        self.state = transition("Regenerating", "GENERATED")
        self.state = transition("Validating", "VALIDATED")
        self.state = transition("QuotaGate", "PRESENT")