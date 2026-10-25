from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from app.core.errors import fail

_windows: dict[tuple, deque[float]] = defaultdict(deque)
_lock = Lock()


def limit(key, count=5, seconds=60):
    with _lock:
        now = monotonic()
        q = _windows[key]
        while q and q[0] < now - seconds:
            q.popleft()
        if len(q) >= count:
            fail("RATE_LIMITED", 429)
        q.append(now)
