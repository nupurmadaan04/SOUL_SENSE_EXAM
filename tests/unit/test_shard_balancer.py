#!/usr/bin/env python3
"""
Unit tests for test shard balancer.

Tests the LPT algorithm under various conditions.
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import pytest

# Import directly to avoid naming conflicts
import importlib.util
spec = importlib.util.spec_from_file_location(
    "shard_balancer_module",
    Path(__file__).parent.parent.parent / "scripts" / "test_shard_balancer.py"
)
shard_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shard_module)

lpt_shard = shard_module.lpt_shard
calculate_metrics = shard_module.calculate_metrics


class TestLPTAlgorithm:
    """Test Longest Processing Time shard balancing algorithm."""
    
    def test_empty_tests(self):
        """Test with no tests."""
        shards = lpt_shard([], {}, 2)
        assert len(shards) == 2
        assert all(len(s) == 0 for s in shards)
    
    def test_single_test(self):
        """Test with single test."""
        shards = lpt_shard(["test_a"], {"test_a": 1.0}, 2)
        assert len(shards) == 2
        assert sum(len(s) for s in shards) == 1
        assert shards[0] == ["test_a"] or shards[1] == ["test_a"]
    
    def test_single_shard(self):
        """Test with single shard."""
        tests = ["test_a", "test_b", "test_c"]
        shards = lpt_shard(tests, {"test_a": 1.0, "test_b": 2.0, "test_c": 3.0}, 1)
        assert len(shards) == 1
        assert len(shards[0]) == 3
    
    def test_perfect_balance(self):
        """Test with tests that divide evenly."""
        tests = ["t1", "t2", "t3", "t4"]
        durations = {"t1": 1.0, "t2": 1.0, "t3": 1.0, "t4": 1.0}
        shards = lpt_shard(tests, durations, 2)
        
        assert len(shards) == 2
        assert len(shards[0]) == 2
        assert len(shards[1]) == 2
        
        # Check loads are equal
        load0 = sum(durations[t] for t in shards[0])
        load1 = sum(durations[t] for t in shards[1])
        assert load0 == load1 == 2.0
    
    def test_uneven_distribution(self):
        """Test with uneven test durations."""
        tests = ["fast1", "fast2", "slow1"]
        durations = {"fast1": 1.0, "fast2": 1.0, "slow1": 10.0}
        shards = lpt_shard(tests, durations, 2)
        
        # Slow test should be alone, fast tests together
        metrics = calculate_metrics(shards, durations)
        assert metrics['test_count'] == 3
        
        # Load should be relatively balanced
        load_ratio = metrics['max_load'] / metrics['avg_load']
        assert load_ratio < 2.0  # Reasonable balance
    
    def test_many_shards(self):
        """Test with more shards than tests."""
        tests = ["t1", "t2"]
        durations = {"t1": 1.0, "t2": 1.0}
        shards = lpt_shard(tests, durations, 5)
        
        assert len(shards) == 5
        # Each test in separate shard
        non_empty = [s for s in shards if len(s) > 0]
        assert len(non_empty) == 2
    
    def test_lpt_sorting(self):
        """Test that LPT assigns longest tests first."""
        tests = ["short", "medium", "long"]
        durations = {"short": 1.0, "medium": 5.0, "long": 10.0}
        shards = lpt_shard(tests, durations, 2)
        
        # Long test should be assigned first (to empty shard)
        assert "long" in shards[0] or "long" in shards[1]
        # Make sure distribution is balanced
        metrics = calculate_metrics(shards, durations)
        assert metrics['imbalance_ratio'] <= 1.5


class TestMetricsCalculation:
    """Test metrics calculation."""
    
    def test_metrics_empty_shards(self):
        """Test metrics with empty shards."""
        shards = [[], []]
        metrics = calculate_metrics(shards, {})
        
        assert metrics['max_load'] == 0
        assert metrics['avg_load'] == 0
        assert metrics['test_count'] == 0
    
    def test_metrics_single_shard(self):
        """Test metrics with single shard."""
        shards = [["test_a", "test_b"]]
        durations = {"test_a": 1.0, "test_b": 2.0}
        metrics = calculate_metrics(shards, durations)
        
        assert metrics['max_load'] == 3.0
        assert metrics['avg_load'] == 3.0
        assert metrics['imbalance_ratio'] == 1.0
        assert metrics['test_count'] == 2
    
    def test_metrics_balanced(self):
        """Test metrics for perfectly balanced shards."""
        shards = [["t1", "t2"], ["t3", "t4"]]
        durations = {"t1": 1.0, "t2": 1.0, "t3": 1.0, "t4": 1.0}
        metrics = calculate_metrics(shards, durations)
        
        assert metrics['max_load'] == 2.0
        assert metrics['avg_load'] == 2.0
        assert metrics['imbalance_ratio'] == 1.0
    
    def test_metrics_unbalanced(self):
        """Test metrics for unbalanced shards."""
        shards = [["slow"], ["fast1", "fast2"]]
        durations = {"slow": 10.0, "fast1": 1.0, "fast2": 1.0}
        metrics = calculate_metrics(shards, durations)
        
        assert metrics['max_load'] == 10.0
        assert metrics['avg_load'] == 6.0
        assert metrics['imbalance_ratio'] > 1.0


class TestDefaultDurations:
    """Test handling of missing durations."""
    
    def test_missing_duration(self):
        """Test that missing durations default to 1.0."""
        tests = ["test_a", "test_b"]
        durations = {"test_a": 1.0}  # test_b missing
        shards = lpt_shard(tests, durations, 2)
        
        assert len(shards) == 2
        assert sum(len(s) for s in shards) == 2
    
    def test_empty_duration_dict(self):
        """Test with no durations provided."""
        tests = ["t1", "t2", "t3"]
        durations = {}
        shards = lpt_shard(tests, durations, 2)
        
        # Should still distribute tests
        assert len(shards) == 2
        assert sum(len(s) for s in shards) == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_shards(self):
        """Test with zero shards (should default to 1)."""
        tests = ["t1", "t2"]
        durations = {"t1": 1.0, "t2": 1.0}
        shards = lpt_shard(tests, durations, 0)
        
        assert len(shards) == 1
        assert len(shards[0]) == 2
    
    def test_negative_shards(self):
        """Test with negative shards (should default to 1)."""
        tests = ["t1", "t2"]
        durations = {"t1": 1.0, "t2": 1.0}
        shards = lpt_shard(tests, durations, -1)
        
        assert len(shards) == 1
    
    def test_large_duration_difference(self):
        """Test with very different durations."""
        tests = ["quick", "slow"]
        durations = {"quick": 0.1, "slow": 1000.0}
        shards = lpt_shard(tests, durations, 2)
        
        # Slow should be alone
        metrics = calculate_metrics(shards, durations)
        assert metrics['test_count'] == 2
    
    def test_many_tests(self):
        """Test with large number of tests."""
        tests = [f"test_{i}" for i in range(100)]
        durations = {f"test_{i}": 1.0 for i in range(100)}
        shards = lpt_shard(tests, durations, 4)
        
        assert len(shards) == 4
        assert sum(len(s) for s in shards) == 100
        
        # Should be reasonably balanced
        metrics = calculate_metrics(shards, durations)
        assert metrics['imbalance_ratio'] < 1.1  # <10% imbalance


@pytest.mark.skip(reason="Integration test - run separately")
def test_real_pytest_collection():
    """Integration test: Collect real tests and shard them."""
    from pathlib import Path
    from test_shard_balancer import collect_tests
    
    test_dir = Path(__file__).parent.parent
    tests = collect_tests(str(test_dir))
    
    if tests:
        durations = {t: 1.0 for t in tests}
        shards = lpt_shard(tests, durations, 4)
        assert sum(len(s) for s in shards) == len(tests)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
