import time
from collections import defaultdict, deque

from fastapi import Depends

from app.core.config import settings
from app.core.exceptions import RateLimitError

# In-memory sliding window. Fine for one process; swap for Redis if you run several workers.
_hits: dict[str, deque] = defaultdict(deque)


def reset_rate_limits() -> None:
    _hits.clear()


def check_rate_limit(key: str, limit: int | None = None, window: int = 60) -> None:
    limit = limit if limit is not None else settings.RATE_LIMIT_PER_MINUTE
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise RateLimitError("Rate limit exceeded. Please wait before retrying.")
    q.append(now)
