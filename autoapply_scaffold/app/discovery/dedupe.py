"""
Deduplication tracker with persistence.
Tracks seen jobs to prevent duplicate applications.
"""
import json
from pathlib import Path

DEDUPE_FILE = Path("out/dedupe.json")

# In-memory cache
_seen = set()
_loaded = False


def _load():
    """Load dedupe state from disk."""
    global _seen, _loaded
    if _loaded:
        return
    if DEDUPE_FILE.exists():
        try:
            with open(DEDUPE_FILE, 'r') as f:
                data = json.load(f)
                _seen = set(data.get('seen', []))
        except Exception:
            _seen = set()
    _loaded = True


def _save():
    """Save dedupe state to disk."""
    DEDUPE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DEDUPE_FILE, 'w') as f:
        json.dump({'seen': list(_seen)}, f, indent=2)


def seen(key: str) -> bool:
    """Check if a job key has been seen before."""
    _load()
    return key in _seen


def mark(key: str):
    """Mark a job key as seen."""
    _load()
    _seen.add(key)
    _save()

def unmark(key: str):
    """Remove a previously marked key."""
    if not key:
        return
    _load()
    if key in _seen:
        _seen.remove(key)
        _save()
