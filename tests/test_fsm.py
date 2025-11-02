import pytest
from autoapply.orchestration.state_machine import transition


def test_happy_path() -> None:
    s: str = "Idle"
    s = transition(s, "START")
    s = transition(s, "RESEARCHED")
    s = transition(s, "GENERATED")
    s = transition(s, "VALIDATED")
    s = transition(s, "PRESENT")
    s = transition(s, "COMMIT")
    s = transition(s, "FINISH")
    assert s == "Done"


def test_illegal_jump() -> None:
    with pytest.raises(RuntimeError):
        transition("Idle", "VALIDATED")