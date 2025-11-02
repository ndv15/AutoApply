"""Validation of skills lines.

A skills line is expected to be in the format
``Category: item | item | item | item``.  Exactly four items are
required, separated by pipes, and the category must start with a capital
letter.  Matching is case sensitive for the category but relaxed for
items.
"""

import re
from typing import TypedDict


CATEGORY = r"[A-Z][A-Za-z0-9\/+&\-\s]{1,30}"
ITEM = r"[A-Za-z0-9.+#\/\- ]{1,30}"
SKILLS_RE = re.compile(
    rf"^(?P<category>{CATEGORY}):\s*(?P<i1>{ITEM})\s*\|\s*(?P<i2>{ITEM})\s*\|\s*(?P<i3>{ITEM})\s*\|\s*(?P<i4>{ITEM})\s*$"
)


class SkillsParts(TypedDict):
    category: str
    items: list[str]
    raw: str


def validate_skills_line(raw: str) -> SkillsParts:
    """Validate and parse a skills line.

    :param raw: The raw skills line as entered by the user.
    :returns: A mapping containing the category, the individual items and
      the original raw string.
    :raises ValueError: If the line does not conform to the required format.
    """
    match = SKILLS_RE.match(raw.strip())
    if not match:
        raise ValueError('Skills must be: "Category: item | item | item | item"')
    groups = match.groupdict()
    return {
        "category": groups["category"],
        "items": [groups["i1"], groups["i2"], groups["i3"], groups["i4"]],
        "raw": raw.strip(),
    }