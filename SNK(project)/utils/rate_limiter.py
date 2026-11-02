"""
In-Memory Rate Limiting Engine (Sliding Window Algorithm)
Provides zero-dependency rate limiting for authentication and biometric punch endpoints
to prevent brute-force and credential stuffing attacks without external Redis services.
"""
import time
from typing import Dict, List, Tuple
from collections import defaultdict


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter tracking request timestamps per client key."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.default_max_requests = max_requests
        self.default_window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        max_requests: int = None,
        window_seconds: int = None,
    ) -> Tuple[bool, int, float]:
        """
        Evaluates whether a request from 'key' (e.g. client IP) is permitted.
        Returns:
            Tuple of (is_allowed: bool, remaining_requests: int, retry_after_seconds: float)
        """
        now = time.time()
        max_req = max_requests or self.default_max_requests
        win_sec = window_seconds or self.default_window_seconds

        timestamps = self._history[key]
        cutoff = now - win_sec

        # Prune timestamps outside window
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self._history[key] = valid_timestamps

        if len(valid_timestamps) >= max_req:
            oldest_in_window = valid_timestamps[0]
            retry_after = max(0.0, round((oldest_in_window + win_sec) - now, 2))
            return False, 0, retry_after

        # Record this request
        valid_timestamps.append(now)
        remaining = max_req - len(valid_timestamps)
        return True, remaining, 0.0

    def reset_key(self, key: str):
        """Clears rate limit history for a specific client key."""
        self._history.pop(key, None)

    def clear_all(self):
        """Resets all tracked rate limit histories."""
        self._history.clear()


# Pre-configured instances (30 login attempts/min, 60 punch attempts/min)
login_rate_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60)
punch_rate_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)
