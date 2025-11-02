"""Finite state machine transitions for the orchestration layer."""

from typing import Literal


# Define the allowed states and events as literal types for type checking.
State = Literal[
    "Idle",
    "Researching",
    "Generating",
    "Validating",
    "QuotaGate",
    "Presenting",
    "Committing",
    "Regenerating",
    "Done",
]
Event = Literal[
    "START",
    "RESEARCHED",
    "GENERATED",
    "VALIDATED",
    "PRESENT",
    "COMMIT",
    "RETRY",
    "FINISH",
]


def transition(state: State, event: Event) -> State:
    """Return the next state given a current state and event.

    :param state: The current state of the orchestrator.
    :param event: The event that occurred.
    :returns: The next state.
    :raises RuntimeError: If the transition is illegal.
    """
    if state == "Idle" and event == "START":
        return "Researching"
    if state == "Researching" and event == "RESEARCHED":
        return "Generating"
    if state == "Generating" and event == "GENERATED":
        return "Validating"
    if state == "Validating" and event == "VALIDATED":
        return "QuotaGate"
    if state == "QuotaGate" and event == "PRESENT":
        return "Presenting"
    if state == "QuotaGate" and event == "FINISH":
        return "Done"
    if state == "Presenting" and event == "COMMIT":
        return "Committing"
    if state == "Committing" and event == "RETRY":
        return "Regenerating"
    if state == "Committing" and event == "FINISH":
        return "Done"
    if state == "Regenerating" and event == "GENERATED":
        return "Validating"
    raise RuntimeError(f"Illegal transition: {state} -> {event}")