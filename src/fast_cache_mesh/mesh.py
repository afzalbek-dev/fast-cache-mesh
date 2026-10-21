import asyncio
import functools
import hashlib
import inspect
import random
from typing import Any, Callable, Dict, Optional, Tuple

from .l1_memory import L1MemoryCache
from .l2_sqlite import L2SQLiteCache
from .singleflight import SingleFlightGroup


class CacheMesh:
    """Two-tier (L1 Memory + L2 SQLite) cache with SingleFlight stampede guard and TTL jitter."""

    def __init__(
        self,
        l1_maxsize: int = 1000,
        l2_db_path: str = ":memory:",
        enable_l2: bool = True,
    ):
        self.l1 = L1MemoryCache(maxsize=l1_maxsize)
        self.enable_l2 = enable_l2
        self.l2 = L2SQLiteCache(db_path=l2_db_path) if enable_l2 else None
        self.singleflight = SingleFlightGroup()

        self._hits_l1 = 0
        self._hits_l2 = 0
        self._misses = 0

    def _apply_jitter(self, ttl: Optional[float], jitter_factor: float = 0.1) -> Optional[float]:
        if ttl is None or jitter_factor <= 0:
            return ttl
        # Add random variation between -jitter_factor and +jitter_factor
        delta = ttl * jitter_factor * (random.random() * 2 - 1)
        return max(1.0, ttl + delta)

    async def get_or_set(
        self,
        key: str,
        loader: Callable[..., Any],
        ttl: Optional[float] = 60.0,
        jitter: float = 0.1,
    ) -> Any:
        # 1. Check L1 memory
        hit, val = self.l1.get(key)
        if hit:
            self._hits_l1 += 1
            return val

        # 2. Check L2 sqlite
        if self.enable_l2 and self.l2:
            hit2, val2 = self.l2.get(key)
            if hit2:
                self._hits_l2 += 1
                # Populate back to L1
                actual_ttl = self._apply_jitter(ttl, jitter)
                self.l1.set(key, val2, ttl=actual_ttl)
                return val2

        self._misses += 1

        # 3. Not in cache -> SingleFlight to prevent stampede
        actual_ttl = self._apply_jitter(ttl, jitter)

        async def _compute():
            if inspect.iscoroutinefunction(loader):
                res = await loader()
            else:
                res = loader()

            self.l1.set(key, res, ttl=actual_ttl)
            if self.enable_l2 and self.l2:
                self.l2.set(key, res, ttl=actual_ttl)
            return res

        return await self.singleflight.execute(key, _compute)

    def invalidate(self, key: str) -> None:
        self.l1.delete(key)
        if self.enable_l2 and self.l2:
            self.l2.delete(key)

    def stats(self) -> Dict[str, Any]:
        total = self._hits_l1 + self._hits_l2 + self._misses
        hit_ratio = ((self._hits_l1 + self._hits_l2) / total) if total > 0 else 0.0
        return {
            "hits_l1": self._hits_l1,
            "hits_l2": self._hits_l2,
            "misses": self._misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
        }


def cache_mesh(
    mesh_instance: Optional[CacheMesh] = None,
    ttl: float = 60.0,
    jitter: float = 0.1,
    key_prefix: str = "cache",
) -> Callable:
    """Decorator to cache results of async or sync functions with CacheMesh."""
    _mesh = mesh_instance or CacheMesh()

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            call_repr = f"{fn.__name__}:{str(args)}:{str(kwargs)}"
            key = f"{key_prefix}:{hashlib.sha256(call_repr.encode()).hexdigest()[:16]}"

            return await _mesh.get_or_set(
                key=key,
                loader=lambda: fn(*args, **kwargs),
                ttl=ttl,
                jitter=jitter,
            )

        async_wrapper.cache_mesh = _mesh
        return async_wrapper

    return decorator
