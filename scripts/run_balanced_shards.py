#!/usr/bin/env python3
"""
Balanced Shard Runner: Executes test shards in parallel.

Reads shard assignments from JSON and runs each shard with pytest.
Aggregates results and reports metrics.

Usage:
    python scripts/run_balanced_shards.py --shards data/shards.json
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import time


def load_shards(shard_file: str) -> Tuple[List[List[str]], Dict]:
    """Load shard assignments from JSON."""
    with open(shard_file) as f:
        data = json.load(f)
    return data["shards"], data.get("metrics", {})


def run_shard(shard_idx: int, tests: List[str], timeout: int = 600) -> Tuple[bool, Dict]:
    """
    Run a single shard with pytest.
    
    Returns:
        (success, metrics) tuple
    """
    if not tests:
        return True, {"passed": 0, "failed": 0, "skipped": 0, "duration": 0}
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "-m", "not flaky",  # Skip quarantined
        "--timeout=180",
    ] + tests
    
    print(f"  [Shard {shard_idx}] Running {len(tests)} tests...")
    
    start = time.time()
    result = subprocess.run(cmd, timeout=timeout)
    duration = time.time() - start
    
    success = result.returncode == 0
    metrics = {
        "passed": result.returncode == 0,
        "duration": duration,
        "test_count": len(tests),
    }
    
    return success, metrics


def run_all_shards(shards: List[List[str]], parallel: bool = True) -> Tuple[bool, Dict]:
    """
    Run all shards, optionally in parallel.
    
    Returns:
        (all_passed, metrics) tuple
    """
    print(f"\n🚀 Running {len(shards)} shards...")
    
    results = []
    start_time = time.time()
    
    if parallel:
        # For now, run sequentially (CI handles parallelism via job matrix)
        # In future, could use multiprocessing here
        for i, shard in enumerate(shards):
            success, metrics = run_shard(i, shard)
            results.append((success, metrics))
            if not success:
                print(f"  ❌ Shard {i} failed")
            else:
                print(f"  ✅ Shard {i} passed ({metrics['duration']:.1f}s)")
    else:
        for i, shard in enumerate(shards):
            success, metrics = run_shard(i, shard)
            results.append((success, metrics))
    
    total_duration = time.time() - start_time
    all_passed = all(r[0] for r in results)
    
    # Aggregate metrics
    total_tests = sum(r[1].get("test_count", 0) for r in results)
    total_metrics = {
        "total_shards": len(shards),
        "total_tests": total_tests,
        "total_duration": total_duration,
        "all_passed": all_passed,
    }
    
    return all_passed, total_metrics


def save_metrics(metrics: Dict, output_file: str = "reports/shard_metrics.json") -> None:
    """Save execution metrics to JSON."""
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n📊 Metrics saved to {output_file}")


if __name__ == "__main__":
    shard_file = "data/shards.json"
    parallel = True
    output = "reports/shard_metrics.json"
    
    # Parse args
    if "--shards" in sys.argv:
        idx = sys.argv.index("--shards")
        shard_file = sys.argv[idx + 1]
    
    if "--sequential" in sys.argv:
        parallel = False
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output = sys.argv[idx + 1]
    
    if not Path(shard_file).exists():
        print(f"❌ Shard file not found: {shard_file}")
        sys.exit(1)
    
    shards, balancing_metrics = load_shards(shard_file)
    all_passed, execution_metrics = run_all_shards(shards, parallel=parallel)
    
    # Combine metrics
    combined = {
        "balancing": balancing_metrics,
        "execution": execution_metrics,
    }
    
    save_metrics(combined, output)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"📈 Summary")
    print(f"{'='*50}")
    print(f"Total Shards: {execution_metrics['total_shards']}")
    print(f"Total Tests: {execution_metrics['total_tests']}")
    print(f"Total Time: {execution_metrics['total_duration']:.1f}s")
    print(f"Result: {'✅ PASS' if all_passed else '❌ FAIL'}")
    print(f"{'='*50}\n")
    
    sys.exit(0 if all_passed else 1)
