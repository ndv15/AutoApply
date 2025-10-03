"""
Filesystem utilities for safe, idempotent file I/O.
Ensures all expected directories and files exist on startup.
"""
from pathlib import Path
import json
from typing import Any, Dict

# Project root paths
ROOT = Path(__file__).resolve().parents[2]  # autoapply_scaffold/
DATA = ROOT / "out"
LOGS = ROOT / "logs"
PROFILE = ROOT / "profile"
TEMPLATES = ROOT / "templates"
WEB = ROOT / "web"

# Directories that must exist
DIRS = [
    DATA,
    DATA / "reviews",
    DATA / "approvals",
    LOGS,
    PROFILE,
    TEMPLATES,
    WEB,
]

# Default files that must exist with their default content
DEFAULT_FILES = {
    DATA / "state.json": {},
    DATA / "dedupe.json": {"seen": []},
}


def bootstrap_fs():
    """
    Create all required directories and default files.
    Call this once during app startup to ensure filesystem is ready.
    """
    # Create directories
    for directory in DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    # Create default files if missing
    for file_path, default_content in DEFAULT_FILES.items():
        if not file_path.exists():
            write_json(file_path, default_content)

    # Ensure logs file exists
    events_log = LOGS / "events.jsonl"
    if not events_log.exists():
        events_log.touch()


def read_json(path: Path | str, default: Any = None) -> Any:
    """
    Safely read JSON file with fallback to default.

    Args:
        path: Path to JSON file
        default: Value to return if file doesn't exist or is invalid

    Returns:
        Parsed JSON content or default value
    """
    try:
        p = Path(path)
        if not p.exists():
            if default is not None:
                # Create file with default content
                write_json(p, default)
            return default

        content = p.read_text(encoding='utf-8')
        if not content.strip():
            return default

        return json.loads(content)
    except Exception as e:
        print(f"Warning: Failed to read {path}: {e}")
        return default


def write_json(path: Path | str, payload: Any):
    """
    Safely write JSON file with proper encoding and formatting.

    Args:
        path: Path to JSON file
        payload: Data to write (will be JSON serialized)
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"Error: Failed to write {path}: {e}")
        raise


def read_text(path: Path | str, default: str = "") -> str:
    """
    Safely read text file with UTF-8 encoding.

    Args:
        path: Path to text file
        default: Value to return if file doesn't exist

    Returns:
        File content or default value
    """
    try:
        p = Path(path)
        if not p.exists():
            return default
        return p.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Failed to read {path}: {e}")
        return default


def write_text(path: Path | str, content: str):
    """
    Safely write text file with UTF-8 encoding.

    Args:
        path: Path to text file
        content: Text content to write
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
    except Exception as e:
        print(f"Error: Failed to write {path}: {e}")
        raise


def append_jsonl(path: Path | str, payload: Dict):
    """
    Append a JSON line to a JSONL file (for telemetry logs).

    Args:
        path: Path to JSONL file
        payload: Dict to append as JSON line
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(p, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Warning: Failed to append to {path}: {e}")
