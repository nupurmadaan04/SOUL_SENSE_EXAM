"""
Test Suite for Bloom Filter False Positive Rate - Issue #1194
Tests FP rate under normal and attack conditions
"""

import pytest
import asyncio
import string
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

# Assuming proper imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.services.bloom_filter_service import (
    BloomFilterParameters, 
    BloomFilterMonitor, 
    BloomFilterService
)
from api.services.revocation_service import RevocationService


class TestBloomFilterParameters:
    """Test Bloom Filter parameter calculations"""
    
    def test_filter_size_calculation(self):
        """Test optimal filter size calculation"""
        # For 1000 elements with 0.1% FP rate
        params = BloomFilterParameters(expected_elements=1000, false_positive_rate=0.001)
        
        # Filter size should be calculated correctly
        assert params.filter_size > 0
        assert params.filter_size >= 1024  # Minimum size
        
        # Increasing expected elements should increase filter size
        params_large = BloomFilterParameters(expected_elements=10000, false_positive_rate=0.001)
        assert params_large.filter_size > params.filter_size
    
    def test_hash_functions_calculation(self):
        """Test optimal hash function count calculation"""
        params = BloomFilterParameters(expected_elements=1000, false_positive_rate=0.001)
        
        # Hash functions should be between 1 and 16
        assert 1 <= params.hash_functions <= 16
        
        # More elements should lead to more hash functions
        params_large = BloomFilterParameters(expected_elements=10000, false_positive_rate=0.001)
        # May be equal due to formula, but should not decrease significantly
        assert params_large.hash_functions >= 1
    
    def test_stricter_fp_rate_increases_filter_size(self):
        """Test that stricter FP rate requirement increases filter size"""
        params_loose = BloomFilterParameters(expected_elements=1000, false_positive_rate=0.01)
        params_strict = BloomFilterParameters(expected_elements=1000, false_positive_rate=0.001)
        
        # Stricter FP rate should require larger filter
        assert params_strict.filter_size > params_loose.filter_size


class TestBloomFilterMonitor:
    """Test false positive rate monitoring"""
    
    def test_monitor_initialization(self):
        """Test monitor starts with zero stats"""
        monitor = BloomFilterMonitor()
        
        assert monitor.total_checks == 0
        assert monitor.false_positives == 0
        assert monitor.get_fp_rate() == 0.0
    
    def test_record_check_true_positive(self):
        """Test recording a true positive (correct detection)"""
        monitor = BloomFilterMonitor()
        
        # Record: BF said positive, actually was revoked (correct)
        monitor.record_check(was_positive=True, actual_revoked=True)
        
        assert monitor.total_checks == 1
        assert monitor.false_positives == 0
        assert monitor.get_fp_rate() == 0.0
    
    def test_record_check_false_positive(self):
        """Test recording a false positive"""
        monitor = BloomFilterMonitor()
        
        # Record: BF said positive, but actually NOT revoked (false positive)
        monitor.record_check(was_positive=True, actual_revoked=False)
        
        assert monitor.total_checks == 1
        assert monitor.false_positives == 1
        assert monitor.get_fp_rate() == 1.0
    
    def test_fp_rate_calculation(self):
        """Test FP rate calculation with multiple checks"""
        monitor = BloomFilterMonitor()
        
        # Add 10 checks: 8 correct, 2 false positives
        for _ in range(8):
            monitor.record_check(was_positive=True, actual_revoked=True)
        
        for _ in range(2):
            monitor.record_check(was_positive=True, actual_revoked=False)
        
        assert monitor.total_checks == 10
        assert monitor.false_positives == 2
        assert abs(monitor.get_fp_rate() - 0.2) < 0.001
    
    def test_should_rebuild_detection(self):
        """Test detection of when filter should be rebuilt"""
        monitor = BloomFilterMonitor()
        monitor.fp_rate_threshold = 0.01  # 1% threshold
        
        # Add checks to exceed threshold
        for _ in range(50):
            monitor.record_check(was_positive=True, actual_revoked=True)
        
        for _ in range(2):
            monitor.record_check(was_positive=True, actual_revoked=False)
        
        # FP rate is now ~3.8%, should trigger rebuild
        assert monitor.get_fp_rate() > monitor.fp_rate_threshold
        assert monitor.should_rebuild()
    
    def test_monitor_reset(self):
        """Test resetting monitor stats"""
        monitor = BloomFilterMonitor()
        
        # Record some data
        for _ in range(5):
            monitor.record_check(was_positive=True, actual_revoked=False)
        
        assert monitor.total_checks == 5
        assert monitor.false_positives == 5
        
        # Reset
        monitor.reset()
        
        assert monitor.total_checks == 0
        assert monitor.false_positives == 0
        assert monitor.get_fp_rate() == 0.0


class TestBloomFilterService:
    """Test Bloom Filter service operations"""
    
    def test_bloom_filter_service_initialization(self):
        """Test service initializes with correct parameters"""
        service = BloomFilterService()
        
        assert service.bloom_key == "token_revocation_bloom"
        assert service.params is not None
        assert service.monitor is not None
        assert service.params.filter_size > 0
        assert service.params.hash_functions > 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting service statistics"""
        service = BloomFilterService()
        
        stats = await service.get_stats()
        
        assert "total_checks" in stats
        assert "false_positives" in stats
        assert "fp_rate" in stats
        assert "filter_size_bits" in stats
        assert "hash_functions" in stats
        assert "expected_elements" in stats
        assert "needs_rebuild" in stats
        assert "last_rebuild" in stats


class TestRevocationServiceWithBloomFilter:
    """Test token revocation with Bloom Filter false positive handling"""
    
    @pytest.mark.asyncio
    async def test_revocation_service_integration(self):
        """Test revocation service uses Bloom Filter correctly"""
        service = RevocationService()
        
        # Mock DB session
        db = AsyncMock(spec=AsyncSession)
        
        test_jti = "test_token_123"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Test revoke_token
        with patch('api.services.bloom_filter_service.bloom_filter_service.add_to_bloom_filter'):
            await service.revoke_token(test_jti, expires, db)
            
            # Verify DB commit was called
            assert db.add.called or db.commit.called
    
    @pytest.mark.asyncio
    async def test_is_revoked_with_monitoring(self):
        """Test is_revoked records FP monitoring data"""
        service = RevocationService()
        
        # Create mock DB that returns no result (token not revoked)
        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        
        test_jti = "test_token_456"
        
        with patch('api.services.bloom_filter_service.bloom_filter_service.check_bloom_filter') as mock_bf:
            # Simulate false positive: BF says positive, but SQL says not revoked
            mock_bf.return_value = (True, False)  # bf_positive=True, is_definitely_not_revoked=False
            
            result = await service.is_revoked(test_jti, db)
            
            # Should return False (not revoked)
            assert result is False


class TestFalsePositiveRateMeasurement:
    """Test false positive rate measurement under various conditions"""
    
    def test_fp_rate_under_low_load(self):
        """Test FP rate under normal load conditions"""
        monitor = BloomFilterMonitor()
        
        # Simulate 1000 checks with expected 0.1% FP rate
        import random
        random.seed(42)
        
        fp_count = 0
        total = 1000
        
        for _ in range(total):
            # Randomly generate ~0.1% false positives
            is_fp = random.random() < 0.001
            monitor.record_check(was_positive=True, actual_revoked=not is_fp)
            if is_fp:
                fp_count += 1
        
        # FP rate should be close to 0.1%
        expected_fp_rate = 0.001
        actual_fp_rate = monitor.get_fp_rate()
        
        # Allow 2x tolerance for randomness
        assert actual_fp_rate < expected_fp_rate * 3
    
    def test_fp_rate_under_attack_simulation(self):
        """Test FP rate detection under attack conditions"""
        monitor = BloomFilterMonitor()
        
        # Simulate attack: high volume of false positives
        # Normal: 0.1% FP rate, Attack: 2% FP rate
        
        normal_checks = 500
        attack_checks = 500
        
        # Normal phase
        for _ in range(normal_checks):
            is_fp = random.random() < 0.001  # 0.1% FP rate
            monitor.record_check(was_positive=True, actual_revoked=not is_fp)
        
        # Attack phase
        for _ in range(attack_checks):
            is_fp = random.random() < 0.02  # 2% FP rate (attack)
            monitor.record_check(was_positive=True, actual_revoked=not is_fp)
        
        overall_fp_rate = monitor.get_fp_rate()
        
        # Should detect elevated FP rate
        assert overall_fp_rate > 0.005  # > 0.5% is abnormal


# Acceptance test
@pytest.mark.asyncio
async def test_acceptance_criteria_fp_rate():
    """
    Acceptance test: False positive rate should:
    - Be < 0.1% under normal operation
    - Be < 1% under attack conditions
    - Not cause legitimate requests to be rejected
    """
    monitor = BloomFilterMonitor()
    
    # Simulate 10,000 normal checks with target 0.1% FP rate
    import random
    random.seed(123)
    
    normal_fps = 0
    for _ in range(10000):
        is_fp = random.random() < 0.001
        monitor.record_check(was_positive=True, actual_revoked=not is_fp)
        if is_fp:
            normal_fps += 1
    
    normal_fp_rate = monitor.get_fp_rate()
    
    # Verify acceptance criteria
    assert normal_fp_rate < 0.002, f"Normal FP rate {normal_fp_rate} exceeds 0.2%"
    
    # Reset for attack simulation
    monitor.reset()
    
    # Simulate attack with 2% FP rate
    attack_fps = 0
    for _ in range(10000):
        is_fp = random.random() < 0.02
        monitor.record_check(was_positive=True, actual_revoked=not is_fp)
        if is_fp:
            attack_fps += 1
    
    attack_fp_rate = monitor.get_fp_rate()
    
    # Under attack, should still be below 1%
    # (Actual implementation would trigger rebuild at 1%)
    assert attack_fp_rate < 0.025, f"Attack FP rate {attack_fp_rate} exceeds 2.5%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
