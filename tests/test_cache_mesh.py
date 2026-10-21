import asyncio
import time
import unittest
from fast_cache_mesh import CacheMesh, cache_mesh


class TestCacheMesh(unittest.TestCase):
    def test_l1_l2_caching_and_promotion(self):
        async def run_test():
            mesh = CacheMesh(l1_maxsize=2, l2_db_path=":memory:")
            compute_count = 0

            def slow_loader():
                nonlocal compute_count
                compute_count += 1
                return {"data": 123}

            # 1. Miss -> Compute
            res1 = await mesh.get_or_set("user:1", slow_loader, ttl=10)
            self.assertEqual(res1, {"data": 123})
            self.assertEqual(compute_count, 1)

            # 2. Hit L1
            res2 = await mesh.get_or_set("user:1", slow_loader, ttl=10)
            self.assertEqual(res2, {"data": 123})
            self.assertEqual(compute_count, 1)

            # 3. Evict from L1 by adding other keys
            await mesh.get_or_set("user:2", lambda: "val2", ttl=10)
            await mesh.get_or_set("user:3", lambda: "val3", ttl=10)

            # user:1 evicted from L1, but exists in L2!
            res3 = await mesh.get_or_set("user:1", slow_loader, ttl=10)
            self.assertEqual(res3, {"data": 123})
            self.assertEqual(compute_count, 1)  # Still 1 because served from L2!

            stats = mesh.stats()
            self.assertEqual(stats["hits_l1"], 1)
            self.assertEqual(stats["hits_l2"], 1)

        asyncio.run(run_test())

    def test_single_flight_stampede_prevention(self):
        async def run_test():
            mesh = CacheMesh()
            invocations = 0

            async def expensive_calc():
                nonlocal invocations
                invocations += 1
                await asyncio.sleep(0.05)
                return 42

            # Launch 10 concurrent requests for the exact same uncached key
            tasks = [
                mesh.get_or_set("heavy:query", expensive_calc, ttl=10)
                for _ in range(10)
            ]
            results = await asyncio.gather(*tasks)

            self.assertEqual(results, [42] * 10)
            # The calculation function MUST be invoked exactly ONCE due to single flight!
            self.assertEqual(invocations, 1)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
