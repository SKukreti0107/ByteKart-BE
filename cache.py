"""Lightweight in-memory TTL cache — no Redis needed.

Used for rarely-changing data (categories, subcategories, brands) to
skip DB round-trips on every public page load.
"""

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        if key in self._store:
            ts, value = self._store[key]
            if time.monotonic() - ts < self._ttl:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str):
        self._store.pop(key, None)


cache = TTLCache(ttl_seconds=300)  # 5-minute TTL
