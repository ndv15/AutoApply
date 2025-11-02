"""Quota enforcement helpers."""

from autoapply.store.memory_store import get_draft


def remaining_quota(draft_id: str, target: int) -> tuple[int, bool]:
    """Compute how many bullets remain to be accepted.

    :param draft_id: ID of the draft to check.
    :param target: Target number of accepted bullets.
    :returns: A tuple of (remaining_count, done_flag) where ``done_flag`` is
      ``True`` if the remaining count is zero and ``False`` otherwise.
    """
    draft = get_draft(draft_id)
    remaining = max(0, target - draft.accepted_count)
    return remaining, remaining == 0