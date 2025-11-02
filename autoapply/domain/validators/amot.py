"""Action‑Metric‑Outcome‑Tool (AMOT) bullet validation and parsing."""

import re
from typing import TypedDict


class AMOTParts(TypedDict):
    action: str
    metric: str
    outcome: str
    tool: str


# Regular expression to match AMOT bullets.  The pattern captures the first
# capitalised verb (ending with 'ed' or 'ing') as the action, the next
# number as the metric, a predefined outcome keyword and the trailing tool
# introduced by using/with/via.
AMOT_RE = re.compile(
    r"^(?P<action>[A-Z][a-zA-Z]+(?:ed|ing))\b.*?"
    r"(?P<metric>(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?%?)\b.*?"
    r"(?P<outcome>(?:reduced|increased|improved|decreased|accelerated|cut|boosted|saved|grew|drove)[^.;]*)\b.*?"
    r"(?P<tool>(?:using|with|via)\s+[A-Za-z0-9+_.\-/ ]+)\.?$",
    re.IGNORECASE,
)


def parse_amot(text: str) -> AMOTParts:
    """Parse an AMOT bullet into structured parts.

    Raises a :class:`ValueError` if the text does not match the required
    pattern of an action, numeric metric, outcome and tool.  Returned
    values are stripped of leading/trailing whitespace but otherwise left
    unchanged.

    :param text: The bullet text to parse.
    :returns: A mapping of named parts.
    """
    match = AMOT_RE.match(text.strip())
    if not match:
        raise ValueError(
            "AMOT validation failed: need Action, numeric Metric, Outcome, and Tool via using|with|via"
        )
    groups = match.groupdict()
    return {
        "action": groups["action"],
        "metric": groups["metric"],
        "outcome": groups["outcome"].strip(),
        "tool": groups["tool"].strip(),
    }