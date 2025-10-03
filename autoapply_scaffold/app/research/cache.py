"""
Caching layer for Perplexity research results.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict


def _get_jd_hash(jd_text: str) -> str:
    """Get SHA256 hash of job description for cache key."""
    return hashlib.sha256(jd_text.encode('utf-8')).hexdigest()[:16]


def _get_cache_path(jd_hash: str, cache_dir: str = "out/cache/perplexity") -> Path:
    """Get path to cached result file."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path / f"{jd_hash}.json"


def get_cached_research(jd_text: str, cache_ttl: int = 3600, cache_dir: str = "out/cache/perplexity") -> Optional[Dict]:
    """
    Get cached Perplexity research result if available and not expired.

    Args:
        jd_text: Job description text to hash
        cache_ttl: Time to live in seconds (default 1 hour)
        cache_dir: Directory for cache files

    Returns:
        Cached result dict or None if not found/expired
    """
    jd_hash = _get_jd_hash(jd_text)
    cache_file = _get_cache_path(jd_hash, cache_dir)

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding='utf-8'))

        # Check expiry
        cached_at = datetime.fromisoformat(data.get('cached_at', ''))
        expiry_time = cached_at + timedelta(seconds=cache_ttl)

        if datetime.now() > expiry_time:
            # Expired, delete cache
            cache_file.unlink()
            return None

        return data.get('result')

    except Exception as e:
        print(f"Cache read error: {e}")
        return None


def save_cached_research(jd_text: str, result: Dict, cache_dir: str = "out/cache/perplexity"):
    """
    Save Perplexity research result to cache.

    Args:
        jd_text: Job description text to hash
        result: Research result to cache
        cache_dir: Directory for cache files
    """
    jd_hash = _get_jd_hash(jd_text)
    cache_file = _get_cache_path(jd_hash, cache_dir)

    try:
        data = {
            'jd_hash': jd_hash,
            'cached_at': datetime.now().isoformat(),
            'result': result
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except Exception as e:
        print(f"Cache write error: {e}")
