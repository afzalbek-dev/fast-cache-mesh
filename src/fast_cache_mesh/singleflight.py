import asyncio
from typing import Any, Callable, Dict, Tuple


class SingleFlightGroup:
    """Prevents cache stampedes by ensuring only one inflight execution per key."""

    def __init__(self):
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def execute(self, key: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            if key in self._in_flight:
                future = self._in_flight[key]
                # Release lock while waiting for future
                return await future

            # We are the leader for this key
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._in_flight[key] = future

        try:
            if asyncio.iscoroutinefunction(fn):
                res = await fn(*args, **kwargs)
            else:
                res = fn(*args, **kwargs)
            future.set_result(res)
            return res
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)
