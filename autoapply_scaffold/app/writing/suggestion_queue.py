"""
Sequential suggestion queue system with stable IDs and deduplication.

Manages per-role suggestion queues with:
- Stable UUID-based IDs
- FIFO queue of pending suggestions
- Accepted/rejected tracking
- Trigram similarity deduplication
- Quantification enforcement
"""
import uuid
import json
import re
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict
from typing import List, Optional, Set, Dict
from datetime import datetime


@dataclass
class Suggestion:
    """Single bullet suggestion with metadata."""
    id: str
    role_key: str
    text: str
    score: float  # 1-10 scale
    model: str  # claude, gpt, gemini
    citations: List[str]
    created_at: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> 'Suggestion':
        return Suggestion(**d)


class SuggestionQueue:
    """
    Per-role suggestion queue with deduplication and state persistence.

    Tracks:
    - pending: deque of suggestions to show
    - accepted: list of approved bullets
    - rejected_ids: set of rejected IDs
    - history_texts: set of normalized texts for deduplication
    """

    def __init__(self, role_key: str, quota: int):
        self.role_key = role_key
        self.quota = quota
        self.pending: deque[Suggestion] = deque()
        self.accepted: List[Suggestion] = []
        self.rejected_ids: Set[str] = set()
        self.history_texts: Set[str] = set()  # Normalized texts for dedup

    def _normalize_text(self, text: str) -> str:
        """Normalize text for deduplication (lowercase, collapse whitespace)."""
        return re.sub(r'\s+', ' ', text.lower().strip())

    def _trigram_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity of trigrams."""
        def get_trigrams(s: str) -> Set[str]:
            s = self._normalize_text(s)
            return {s[i:i+3] for i in range(len(s)-2)}

        t1 = get_trigrams(text1)
        t2 = get_trigrams(text2)

        if not t1 or not t2:
            return 0.0

        intersection = len(t1 & t2)
        union = len(t1 | t2)

        return intersection / union if union > 0 else 0.0

    def is_duplicate(self, text: str, threshold: float = 0.85) -> bool:
        """Check if text is too similar to any accepted/rejected text."""
        normalized = self._normalize_text(text)

        # Exact match
        if normalized in self.history_texts:
            return True

        # Similarity check against all history
        for hist_text in self.history_texts:
            if self._trigram_similarity(text, hist_text) > threshold:
                return True

        return False

    def has_quantification(self, text: str) -> bool:
        """Check if text contains quantified outcomes (%, $, or numbers)."""
        patterns = [
            r'\d+%',  # Percentages
            r'\$\d+',  # Dollar amounts
            r'\[\$[A-Z]\]',  # Placeholder like [$Y]
            r'\[X%\]',  # Placeholder like [X%]
            r'\[N\]',  # Placeholder like [N]
            r'\[[\d\w]+%?\]',  # General placeholders
            r'\d+[\+\-]?',  # Numbers with optional +/-
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def add_suggestions(self, suggestions: List[Suggestion]) -> int:
        """Add new suggestions to queue, filtering duplicates. Returns count added."""
        added = 0
        for sugg in suggestions:
            # Check quantification
            if not self.has_quantification(sugg.text):
                print(f"Skipping suggestion without quantification: {sugg.text[:50]}...")
                continue

            # Check for duplicate
            if self.is_duplicate(sugg.text):
                print(f"Skipping duplicate suggestion: {sugg.text[:50]}...")
                continue

            # Add to queue and history
            self.pending.append(sugg)
            self.history_texts.add(self._normalize_text(sugg.text))
            added += 1

        return added

    def pop_next(self) -> Optional[Suggestion]:
        """Get next suggestion from queue."""
        if self.pending:
            return self.pending.popleft()
        return None

    def accept(self, suggestion_id: str, suggestion_text: str) -> bool:
        """Mark suggestion as accepted. Returns True if found and accepted."""
        # Try to find in pending
        for i, sugg in enumerate(self.pending):
            if sugg.id == suggestion_id:
                self.accepted.append(sugg)
                del self.pending[i]
                return True

        # Maybe already accepted? Check accepted list
        for sugg in self.accepted:
            if sugg.id == suggestion_id:
                return True  # Already accepted

        return False

    def reject(self, suggestion_id: str) -> bool:
        """Mark suggestion as rejected. Returns True if found."""
        # Try to find in pending
        for i, sugg in enumerate(self.pending):
            if sugg.id == suggestion_id:
                self.rejected_ids.add(suggestion_id)
                del self.pending[i]
                return True

        # Already rejected?
        if suggestion_id in self.rejected_ids:
            return True

        return False

    def is_complete(self) -> bool:
        """Check if quota is met."""
        return len(self.accepted) >= self.quota

    def needs_refill(self, min_pending: int = 3) -> bool:
        """Check if queue needs more suggestions."""
        return len(self.pending) < min_pending and not self.is_complete()

    def to_dict(self) -> Dict:
        """Serialize to dict for persistence."""
        return {
            'role_key': self.role_key,
            'quota': self.quota,
            'pending': [s.to_dict() for s in self.pending],
            'accepted': [s.to_dict() for s in self.accepted],
            'rejected_ids': list(self.rejected_ids),
            'history_texts': list(self.history_texts)
        }

    @staticmethod
    def from_dict(d: Dict) -> 'SuggestionQueue':
        """Deserialize from dict."""
        queue = SuggestionQueue(d['role_key'], d['quota'])
        queue.pending = deque([Suggestion.from_dict(s) for s in d.get('pending', [])])
        queue.accepted = [Suggestion.from_dict(s) for s in d.get('accepted', [])]
        queue.rejected_ids = set(d.get('rejected_ids', []))
        queue.history_texts = set(d.get('history_texts', []))
        return queue


class QueueManager:
    """
    Manages all role queues for a job.

    Handles persistence to out/queues/{job_id}.json
    """

    def __init__(self, job_id: str, quotas: Dict[str, int]):
        self.job_id = job_id
        self.quotas = quotas
        self.queues: Dict[str, SuggestionQueue] = {}

        # Initialize queues for all roles
        for role_key, quota in quotas.items():
            self.queues[role_key] = SuggestionQueue(role_key, quota)

        # Try to load existing state
        self.load()

    def _get_path(self) -> Path:
        """Get path to queue state file."""
        queue_dir = Path("out/queues")
        queue_dir.mkdir(parents=True, exist_ok=True)
        return queue_dir / f"{self.job_id}.json"

    def save(self):
        """Save all queues to disk."""
        data = {
            'job_id': self.job_id,
            'updated_at': datetime.now().isoformat(),
            'queues': {role_key: queue.to_dict() for role_key, queue in self.queues.items()}
        }
        self._get_path().write_text(json.dumps(data, indent=2))

    def load(self):
        """Load queues from disk if exists."""
        path = self._get_path()
        if path.exists():
            data = json.loads(path.read_text())
            for role_key, queue_data in data.get('queues', {}).items():
                if role_key in self.queues:
                    self.queues[role_key] = SuggestionQueue.from_dict(queue_data)

    def get_queue(self, role_key: str) -> Optional[SuggestionQueue]:
        """Get queue for role."""
        return self.queues.get(role_key)

    def all_complete(self) -> bool:
        """Check if all roles are complete."""
        return all(q.is_complete() for q in self.queues.values())
