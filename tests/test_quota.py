from autoapply.store.memory_store import create_draft, get_draft
from autoapply.services.quota_service import remaining_quota


def test_quota_remaining() -> None:
    draft = create_draft(
        {
            "job": {
                "title": "Eng",
                "company": "X",
                "responsibilities": [],
                "requirements": [],
                "keywords": [],
            },
            "quota": 3,
        }
    )
    rem, done = remaining_quota(draft.id, 3)
    assert rem == 3 and not done
    draft2 = get_draft(draft.id)
    draft2.accepted_count = 3
    rem2, done2 = remaining_quota(draft.id, 3)
    assert rem2 == 0 and done2