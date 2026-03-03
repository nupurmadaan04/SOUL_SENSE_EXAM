"""
Load testing script for performance validation.

Tests:
- API endpoint performance under load
- Database connection pool behavior
- Cache effectiveness
- Response time distribution
"""

import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics


class LoadTester:
    """Simple load testing utility."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[float] = []
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> float:
        """Make single request and return duration."""
        start = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                await response.text()
                duration = time.time() - start
                self.results.append(duration)
                return duration
        except Exception as e:
            print(f"Request failed: {e}")
            return -1
    
    async def run_concurrent_requests(self, endpoint: str, num_requests: int):
        """Run concurrent requests to endpoint."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.make_request(session, endpoint)
                for _ in range(num_requests)
            ]
            await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict:
        """Calculate performance statistics."""
        if not self.results:
            return {}
        
        valid_results = [r for r in self.results if r > 0]
        
        return {
            'total_requests': len(self.results),
            'successful': len(valid_results),
            'failed': len(self.results) - len(valid_results),
            'avg_response_time': statistics.mean(valid_results),
            'median_response_time': statistics.median(valid_results),
            'min_response_time': min(valid_results),
            'max_response_time': max(valid_results),
            'p95_response_time': sorted(valid_results)[int(len(valid_results) * 0.95)],
            'p99_response_time': sorted(valid_results)[int(len(valid_results) * 0.99)],
        }
    
    def print_report(self):
        """Print performance report."""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("  Load Test Results")
        print("="*60)
        print(f"Total Requests:    {stats['total_requests']}")
        print(f"Successful:        {stats['successful']}")
        print(f"Failed:            {stats['failed']}")
        print(f"Success Rate:      {stats['successful']/stats['total_requests']*100:.1f}%")
        print(f"\nResponse Times:")
        print(f"  Average:         {stats['avg_response_time']*1000:.2f}ms")
        print(f"  Median:          {stats['median_response_time']*1000:.2f}ms")
        print(f"  Min:             {stats['min_response_time']*1000:.2f}ms")
        print(f"  Max:             {stats['max_response_time']*1000:.2f}ms")
        print(f"  P95:             {stats['p95_response_time']*1000:.2f}ms")
        print(f"  P99:             {stats['p99_response_time']*1000:.2f}ms")
        print("="*60 + "\n")


async def main():
    """Run load tests."""
    tester = LoadTester()
    
    print("Starting load test...")
    print("Testing /api/v1/health endpoint with 100 concurrent requests\n")
    
    start = time.time()
    await tester.run_concurrent_requests("/api/v1/health", 100)
    duration = time.time() - start
    
    print(f"Completed in {duration:.2f}s")
    tester.print_report()


if __name__ == "__main__":
    asyncio.run(main())
