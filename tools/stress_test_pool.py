#!/usr/bin/env python3
"""
Stress test harness for connection pool exhaustion (#1216).
Simulates high concurrency to test pool stability and session reuse.

Usage:
    python tools/stress_test_pool.py --url http://localhost:8000 --concurrency 2000 --duration 60

Requirements:
    pip install aiohttp
"""

import asyncio
import aiohttp
import argparse
import time
import statistics
from typing import List, Tuple

async def make_request(session: aiohttp.ClientSession, url: str, endpoint: str) -> Tuple[float, bool]:
    """Make a single request and return (response_time, success)."""
    start_time = time.time()
    try:
        async with session.get(f"{url}{endpoint}") as response:
            await response.text()  # Consume response
            return time.time() - start_time, response.status == 200
    except Exception as e:
        print(f"Request failed: {e}")
        return time.time() - start_time, False

async def worker(session: aiohttp.ClientSession, url: str, endpoints: List[str], request_count: int, results: List[Tuple[float, bool]]):
    """Worker coroutine to make multiple requests."""
    for _ in range(request_count):
        endpoint = endpoints[_ % len(endpoints)]  # Cycle through endpoints
        result = await make_request(session, url, endpoint)
        results.append(result)

async def stress_test(url: str, concurrency: int, duration: int = 60):
    """Run stress test with given concurrency for specified duration."""
    # Representative endpoints to test (adjust based on your API)
    endpoints = [
        "/api/v1/health",  # Health check
        "/api/v1/users/me",  # User profile (requires auth, but for demo)
        "/api/v1/exams/list",  # Exam list
    ]

    # For simplicity, we'll hit health endpoint mostly
    endpoints = ["/api/v1/health"] * len(endpoints)

    connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
    timeout = aiohttp.ClientTimeout(total=30)  # 30s timeout per request

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        results: List[Tuple[float, bool]] = []
        start_time = time.time()

        # Create worker tasks
        tasks = []
        requests_per_worker = max(1, (concurrency * duration) // concurrency)  # Rough estimate

        for _ in range(concurrency):
            task = asyncio.create_task(worker(session, url, endpoints, requests_per_worker, results))
            tasks.append(task)

        # Run for specified duration
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=duration)
        except asyncio.TimeoutError:
            pass  # Expected

        end_time = time.time()

        # Analyze results
        total_requests = len(results)
        successful_requests = sum(1 for _, success in results if success)
        response_times = [rt for rt, _ in results]

        print("
=== Stress Test Results ===")
        print(f"Duration: {end_time - start_time:.2f}s")
        print(f"Concurrency: {concurrency}")
        print(f"Total requests: {total_requests}")
        print(f"Successful requests: {successful_requests}")
        print(f"Success rate: {successful_requests / total_requests * 100:.2f}%" if total_requests > 0 else "0%")

        if response_times:
            print(f"Average response time: {statistics.mean(response_times):.3f}s")
            print(f"Median response time: {statistics.median(response_times):.3f}s")
            print(f"95th percentile: {statistics.quantiles(response_times, n=20)[18]:.3f}s")  # 95th
            print(f"Max response time: {max(response_times):.3f}s")

        # Check for pool exhaustion indicators
        slow_requests = sum(1 for rt in response_times if rt > 5.0)  # >5s considered slow
        print(f"Requests >5s: {slow_requests} ({slow_requests / total_requests * 100:.2f}%)" if total_requests > 0 else "0")

        if successful_requests / total_requests < 0.95:  # <95% success
            print("⚠️  WARNING: High failure rate - possible pool exhaustion!")
        if slow_requests / total_requests > 0.1:  # >10% slow
            print("⚠️  WARNING: High latency - check pool configuration!")

def main():
    parser = argparse.ArgumentParser(description="Stress test for connection pool")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--concurrency", type=int, default=100, help="Number of concurrent connections")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")

    args = parser.parse_args()

    print(f"Starting stress test: {args.concurrency} concurrent connections for {args.duration}s")
    print(f"Target URL: {args.url}")

    asyncio.run(stress_test(args.url, args.concurrency, args.duration))

if __name__ == "__main__":
    main()