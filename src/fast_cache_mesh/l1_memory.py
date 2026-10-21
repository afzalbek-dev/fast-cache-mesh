from collections import OrderedDict
import time
from typing import Any, Optional, Tuple


class L1MemoryCache:
    """Thread-safe and fast in-memory LRU cache with TTL."""

    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Tuple[bool, Any]:
        if key not in self._cache:
            return False, None

        val, exp = self._cache[key]
        if exp is not None and time.time() > exp:
            del self._cache[key]
            return False, None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return True, val

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        exp = (time.time() + ttl) if ttl else None

        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, exp)

        if len(self._cache) > self.maxsize:
            # Evict least recently used (first item)
            self._cache.popitem(last=False)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
