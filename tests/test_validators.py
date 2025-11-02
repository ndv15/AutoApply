import pytest
from autoapply.domain.validators.amot import parse_amot
from autoapply.domain.validators.skills import validate_skills_line


def test_amot_valid() -> None:
    parts = parse_amot("Improved data pipeline by 35% which reduced latency using Python")
    assert parts["action"].lower().startswith("improv")
    assert "35" in parts["metric"]
    assert "reduced" in parts["outcome"].lower()
    assert "using python" in parts["tool"].lower()


def test_amot_missing_tool() -> None:
    with pytest.raises(ValueError):
        parse_amot("Improved data pipeline by 35% which reduced latency")


def test_skills_line_valid() -> None:
    result = validate_skills_line("Languages: Python | Go | Rust | TypeScript")
    assert len(result["items"]) == 4


def test_skills_line_bad() -> None:
    with pytest.raises(ValueError):
        validate_skills_line("Languages: Python, Go, Rust, TS")