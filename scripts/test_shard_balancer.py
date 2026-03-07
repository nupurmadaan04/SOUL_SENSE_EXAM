#!/usr/bin/env python3
"""
Test Shard Balancer: Distributes tests across shards using LPT algorithm.

Uses Longest Processing Time (LPT) greedy algorithm to minimize makespan
(total execution time with parallel workers).

Usage:
    python scripts/test_shard_balancer.py tests/ --shards 4 --output shards.json
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def collect_tests(test_path: str) -> List[str]:
    """Collect all test files."""
    test_dir = Path(test_path)
    if not test_dir.exists():
        return []
    
    return [str(f) for f in test_dir.glob("test_*.py")]


def load_durations(duration_file: str) -> Dict[str, float]:
    """Load test durations from JSON file."""
    if not Path(duration_file).exists():
        return {}
    
    with open(duration_file) as f:
        return json.load(f)


def create_default_durations(tests: List[str]) -> Dict[str, float]:
    """Create default durations (1s per test)."""
    return {test: 1.0 for test in tests}


def lpt_shard(tests: List[str], durations: Dict[str, float], num_shards: int) -> List[List[str]]:
    """
    Longest Processing Time (LPT) algorithm for load balancing.
    
    Greedy approach:
    1. Sort tests by duration (descending)
    2. Assign each test to shard with minimum current load
    
    Args:
        tests: List of test names
        durations: Dict of test -> duration
        num_shards: Number of parallel shards
    
    Returns:
        List of shard assignments (each shard is a list of tests)
    """
    if num_shards < 1:
        num_shards = 1
    
    # Initialize shards with zero load
    shards: List[List[str]] = [[] for _ in range(num_shards)]
    shard_loads: List[float] = [0.0] * num_shards
    
    # Sort tests by duration (longest first)
    sorted_tests = sorted(tests, key=lambda t: durations.get(t, 1.0), reverse=True)
    
    # Assign each test to least-loaded shard
    for test in sorted_tests:
        duration = durations.get(test, 1.0)
        # Find shard with minimum load
        min_idx = shard_loads.index(min(shard_loads))
        shards[min_idx].append(test)
        shard_loads[min_idx] += duration
    
    return shards


def calculate_metrics(shards: List[List[str]], durations: Dict[str, float]) -> Dict:
    """Calculate shard balancing metrics."""
    shard_loads = []
    for shard in shards:
        load = sum(durations.get(test, 1.0) for test in shard)
        shard_loads.append(load)
    
    max_load = max(shard_loads) if shard_loads else 0
    avg_load = sum(shard_loads) / len(shard_loads) if shard_loads else 0
    imbalance = max_load / avg_load if avg_load > 0 else 1.0
    
    return {
        "shard_loads": shard_loads,
        "max_load": max_load,
        "avg_load": avg_load,
        "imbalance_ratio": imbalance,
        "test_count": sum(len(s) for s in shards),
    }


def balance_and_save(test_path: str, num_shards: int, duration_file: str = "data/test_durations.json", output_file: str = "data/shards.json") -> None:
    """Balance tests into shards and save JSON."""
    print(f"🎯 Collecting tests from {test_path}...")
    tests = collect_tests(test_path)
    
    if not tests:
        print(f"❌ No tests found in {test_path}")
        sys.exit(1)
    
    print(f"📊 Loading durations from {duration_file}...")
    durations = load_durations(duration_file)
    
    if not durations:
        print(f"⚠️  No durations found. Using default 1.0s per test.")
        durations = create_default_durations(tests)
    
    print(f"⚖️  Running LPT algorithm with {num_shards} shards...")
    shards = lpt_shard(tests, durations, num_shards)
    metrics = calculate_metrics(shards, durations)
    
    # Prepare output
    output = {
        "shards": shards,
        "metrics": metrics,
        "config": {
            "algorithm": "lpt",
            "num_shards": num_shards,
            "test_count": len(tests),
        }
    }
    
    # Save JSON
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print(f"\n✅ Shard assignments saved to {output_file}")
    print(f"   Tests: {metrics['test_count']}")
    print(f"   Shards: {num_shards}")
    print(f"   Max Load: {metrics['max_load']:.1f}s")
    print(f"   Avg Load: {metrics['avg_load']:.1f}s")
    print(f"   Imbalance: {metrics['imbalance_ratio']:.2f}x")
    print()
    
    # Show shard breakdown
    for i, shard in enumerate(shards):
        load = metrics['shard_loads'][i]
        print(f"   Shard {i}: {len(shard)} tests, {load:.1f}s load")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_shard_balancer.py <test_path> --shards N [--durations FILE] [--output FILE]")
        sys.exit(1)
    
    test_path = sys.argv[1]
    num_shards = 2
    duration_file = "data/test_durations.json"
    output_file = "data/shards.json"
    
    # Parse args
    if "--shards" in sys.argv:
        idx = sys.argv.index("--shards")
        num_shards = int(sys.argv[idx + 1])
    
    if "--durations" in sys.argv:
        idx = sys.argv.index("--durations")
        duration_file = sys.argv[idx + 1]
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_file = sys.argv[idx + 1]
    
    balance_and_save(test_path, num_shards, duration_file, output_file)
