"""
Submission rate limiter for auto-apply.

Ensures minimum time interval between job submissions to:
- Prevent API rate limiting (Perplexity, Claude, etc.)
- Maintain professional submission pace
- Avoid triggering anti-bot mechanisms on job boards
"""
import time
from pathlib import Path
from typing import Optional
import json
from datetime import datetime, timedelta


class SubmissionRateLimiter:
    """
    Enforces minimum time interval between job submissions.

    Persists state to disk so rate limiting survives server restarts.
    """

    def __init__(self, min_interval_seconds: int = 300, state_file: str = "out/submission_state.json"):
        """
        Args:
            min_interval_seconds: Minimum seconds between submissions (default 5 minutes)
            state_file: Path to persist last submission timestamp
        """
        self.min_interval_seconds = min_interval_seconds
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load last submission time from disk
        self.last_submission_time = self._load_last_submission_time()

    def _load_last_submission_time(self) -> Optional[float]:
        """Load last submission timestamp from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_submission_time')
            except Exception as e:
                print(f"Warning: Could not load submission state: {e}")
        return None

    def _save_last_submission_time(self, timestamp: float):
        """Save last submission timestamp to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'last_submission_time': timestamp,
                    'last_submission_datetime': datetime.fromtimestamp(timestamp).isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save submission state: {e}")

    def can_submit_now(self) -> bool:
        """Check if enough time has passed since last submission."""
        if self.last_submission_time is None:
            return True

        elapsed = time.time() - self.last_submission_time
        return elapsed >= self.min_interval_seconds

    def time_until_next_submission(self) -> float:
        """
        Get seconds until next submission is allowed.

        Returns:
            0 if submission allowed now, otherwise seconds to wait
        """
        if self.last_submission_time is None:
            return 0

        elapsed = time.time() - self.last_submission_time
        remaining = self.min_interval_seconds - elapsed
        return max(0, remaining)

    def record_submission(self, job_id: str):
        """
        Record a successful submission.

        Args:
            job_id: ID of the submitted job (for logging)
        """
        timestamp = time.time()
        self.last_submission_time = timestamp
        self._save_last_submission_time(timestamp)

        print(f"✓ Submission recorded: {job_id} at {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
        print(f"  Next submission allowed in {self.min_interval_seconds} seconds ({self.min_interval_seconds // 60} minutes)")

    def get_status(self) -> dict:
        """
        Get current rate limiter status.

        Returns:
            Dict with submission status info
        """
        can_submit = self.can_submit_now()
        wait_time = self.time_until_next_submission()

        status = {
            'can_submit': can_submit,
            'wait_seconds': round(wait_time, 1),
            'wait_minutes': round(wait_time / 60, 1),
            'min_interval_seconds': self.min_interval_seconds,
            'min_interval_minutes': self.min_interval_seconds // 60
        }

        if self.last_submission_time:
            status['last_submission_time'] = datetime.fromtimestamp(
                self.last_submission_time
            ).isoformat()
            status['next_submission_time'] = datetime.fromtimestamp(
                self.last_submission_time + self.min_interval_seconds
            ).isoformat()

        return status

    def wait_if_needed(self) -> float:
        """
        Block until submission is allowed (if rate limited).

        Returns:
            Seconds waited (0 if no wait needed)
        """
        wait_time = self.time_until_next_submission()

        if wait_time > 0:
            print(f"⏳ Rate limit active. Waiting {wait_time:.1f} seconds ({wait_time / 60:.1f} minutes) before next submission...")
            time.sleep(wait_time)
            return wait_time

        return 0


# Global rate limiter instance
_rate_limiter: Optional[SubmissionRateLimiter] = None


def get_rate_limiter(min_interval_seconds: int = 300) -> SubmissionRateLimiter:
    """
    Get or create the global rate limiter instance.

    Args:
        min_interval_seconds: Minimum seconds between submissions

    Returns:
        SubmissionRateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = SubmissionRateLimiter(min_interval_seconds)

    return _rate_limiter
