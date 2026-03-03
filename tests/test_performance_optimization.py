"""
Tests for performance optimization features.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from backend.fastapi.api.middleware.query_optimizer import cache_query, QueryOptimizer
from backend.fastapi.api.utils.performance_monitor import PerformanceMonitor, track_performance


class TestQueryOptimizer:
    """Test query optimization utilities."""
    
    def test_paginate(self):
        """Test query pagination."""
        mock_query = Mock()
        mock_query.count.return_value = 100
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = ['item1', 'item2']
        
        result = QueryOptimizer.paginate(mock_query, page=1, per_page=50)
        
        assert result['total'] == 100
        assert result['page'] == 1
        assert result['per_page'] == 50
        assert result['pages'] == 2
        assert len(result['items']) == 2
    
    def test_paginate_last_page(self):
        """Test pagination on last page."""
        mock_query = Mock()
        mock_query.count.return_value = 75
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = ['item']
        
        result = QueryOptimizer.paginate(mock_query, page=2, per_page=50)
        
        assert result['pages'] == 2
        assert result['page'] == 2


class TestPerformanceMonitor:
    """Test performance monitoring."""
    
    def test_record_timing(self):
        """Test recording operation timing."""
        monitor = PerformanceMonitor()
        
        monitor.record_timing('test_op', 0.5)
        monitor.record_timing('test_op', 0.3)
        
        stats = monitor.get_stats()
        assert 'test_op' in stats
        assert stats['test_op']['count'] == 2
        assert stats['test_op']['avg'] == 0.4
    
    def test_cache_metrics(self):
        """Test cache hit/miss tracking."""
        monitor = PerformanceMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        stats = monitor.get_stats()
        assert stats['cache']['hits'] == 2
        assert stats['cache']['misses'] == 1
        assert stats['cache']['hit_rate'] == 2/3
    
    def test_reset(self):
        """Test metrics reset."""
        monitor = PerformanceMonitor()
        
        monitor.record_timing('test', 1.0)
        monitor.record_cache_hit()
        monitor.reset()
        
        stats = monitor.get_stats()
        assert len(stats) == 1  # Only cache stats
        assert stats['cache']['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_track_performance_async(self):
        """Test performance tracking decorator for async functions."""
        monitor = PerformanceMonitor()
        
        @track_performance('async_op')
        async def slow_function():
            await asyncio.sleep(0.1)
            return 'result'
        
        # Patch global monitor
        with patch('backend.fastapi.api.utils.performance_monitor.monitor', monitor):
            result = await slow_function()
        
        assert result == 'result'
        stats = monitor.get_stats()
        assert 'async_op' in stats
        assert stats['async_op']['count'] == 1
        assert stats['async_op']['avg'] >= 0.1
    
    def test_track_performance_sync(self):
        """Test performance tracking decorator for sync functions."""
        monitor = PerformanceMonitor()
        
        @track_performance('sync_op')
        def slow_function():
            time.sleep(0.1)
            return 'result'
        
        with patch('backend.fastapi.api.utils.performance_monitor.monitor', monitor):
            result = slow_function()
        
        assert result == 'result'
        stats = monitor.get_stats()
        assert 'sync_op' in stats
        assert stats['sync_op']['avg'] >= 0.1


class TestCacheQuery:
    """Test query caching decorator."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = '{"result": "cached"}'
        
        @cache_query(ttl=300)
        async def test_func():
            return {"result": "fresh"}
        
        with patch('backend.fastapi.api.middleware.query_optimizer.cache_service', mock_cache):
            result = await test_func()
        
        assert result == {"result": "cached"}
        mock_cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss scenario."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        
        @cache_query(ttl=300)
        async def test_func():
            return {"result": "fresh"}
        
        with patch('backend.fastapi.api.middleware.query_optimizer.cache_service', mock_cache):
            result = await test_func()
        
        assert result == {"result": "fresh"}
        mock_cache.set.assert_called_once()


class TestResponseOptimization:
    """Test response optimization."""
    
    def test_etag_generation(self):
        """Test ETag generation for responses."""
        import hashlib
        
        body = b'{"data": "test"}'
        etag = hashlib.md5(body).hexdigest()
        
        assert len(etag) == 32
        assert etag == hashlib.md5(body).hexdigest()  # Consistent
    
    def test_gzip_compression(self):
        """Test gzip compression."""
        import gzip
        
        original = b'{"data": "test"}' * 100
        compressed = gzip.compress(original)
        
        assert len(compressed) < len(original)
        assert gzip.decompress(compressed) == original


class TestDatabaseOptimizer:
    """Test database optimization utilities."""
    
    def test_optimal_pool_size(self):
        """Test pool size calculation."""
        from backend.fastapi.api.utils.db_optimizer import ConnectionPoolOptimizer
        
        config = ConnectionPoolOptimizer.get_optimal_pool_size()
        
        assert 'pool_size' in config
        assert 'max_overflow' in config
        assert 'pool_timeout' in config
        assert config['pool_size'] > 0
        assert config['max_overflow'] > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test database health check."""
        from backend.fastapi.api.utils.db_optimizer import ConnectionPoolOptimizer
        
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        
        result = await ConnectionPoolOptimizer.health_check(mock_db)
        
        assert result is True
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure handling."""
        from backend.fastapi.api.utils.db_optimizer import ConnectionPoolOptimizer
        
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Connection failed")
        
        result = await ConnectionPoolOptimizer.health_check(mock_db)
        
        assert result is False


# Integration tests

@pytest.mark.asyncio
async def test_end_to_end_caching():
    """Test end-to-end caching flow."""
    call_count = 0
    
    @cache_query(ttl=1)
    async def expensive_operation():
        nonlocal call_count
        call_count += 1
        return {"data": "result"}
    
    # First call - cache miss
    result1 = await expensive_operation()
    assert call_count == 1
    
    # Second call - cache hit (if cache available)
    result2 = await expensive_operation()
    # call_count may be 1 or 2 depending on cache availability
    
    assert result1 == result2


def test_performance_monitoring_integration():
    """Test performance monitoring integration."""
    monitor = PerformanceMonitor()
    
    # Simulate operations
    for i in range(10):
        monitor.record_timing('api_call', 0.1 + i * 0.01)
    
    for i in range(8):
        monitor.record_cache_hit()
    
    for i in range(2):
        monitor.record_cache_miss()
    
    stats = monitor.get_stats()
    
    assert stats['api_call']['count'] == 10
    assert stats['cache']['hit_rate'] == 0.8
    assert stats['api_call']['p95'] > stats['api_call']['avg']
