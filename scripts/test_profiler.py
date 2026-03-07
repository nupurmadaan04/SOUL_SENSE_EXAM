#!/usr/bin/env python3
"""
Test Profiler: Records test execution times for shard balancing.

Usage:
    python scripts/test_profiler.py tests/ --output data/test_durations.json
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

def run_pytest_with_durations(test_path: str) -> Dict[str, float]:
    """Run pytest and collect test durations."""
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "--collect-only",
        "-q",
        "--tb=no"
    ]
    
    # First, collect all tests
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Now run with durations
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=no",
        "-m", "not flaky",  # Skip quarantined tests
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    durations = {}
    
    # Parse pytest output for test names and durations
    for line in result.stdout.split('\n'):
        if 'PASSED' in line or 'FAILED' in line or 'SKIPPED' in line:
            parts = line.split()
            if len(parts) > 0:
                test_name = parts[0]
                # Extract duration from brackets (e.g., "1.23s")
                if '[' in line and 's]' in line:
                    duration_str = line[line.rfind('[')+1:line.rfind(']')]
                    try:
                        duration = float(duration_str.rstrip('s'))
                        durations[test_name] = duration
                    except ValueError:
                        durations[test_name] = 1.0  # Default to 1s if parse fails
    
    return durations

def profile_tests(test_path: str, output_file: str) -> None:
    """Profile tests and save durations to JSON."""
    print(f"📊 Profiling tests in {test_path}...")
    durations = run_pytest_with_durations(test_path)
    
    if not durations:
        print("⚠️  No test durations found. Using default values.")
        # Fallback: estimate based on test file count
        test_files = list(Path(test_path).glob("test_*.py"))
        durations = {str(f): 1.0 for f in test_files}
    
    # Save to file
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(durations, f, indent=2)
    
    print(f"✅ Saved {len(durations)} test durations to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_profiler.py <test_path> [--output FILE]")
        sys.exit(1)
    
    test_path = sys.argv[1]
    output = "data/test_durations.json"
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]
    
    profile_tests(test_path, output)
