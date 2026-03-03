import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from backend.fastapi.api.utils.cgroup_memory_monitor import (
    CGroupMemoryMonitor, MemoryPressure, get_memory_monitor
)

class TestCGroupMemoryMonitor:
    
    def test_pressure_level_calculation(self):
        """Test pressure level thresholds."""
        monitor = CGroupMemoryMonitor()
        assert monitor._calculate_pressure_level(50) == "none"
        assert monitor._calculate_pressure_level(70) == "low"
        assert monitor._calculate_pressure_level(80) == "medium"
        assert monitor._calculate_pressure_level(90) == "high"
        assert monitor._calculate_pressure_level(98) == "critical"
    
    @patch('pathlib.Path.exists')
    def test_cgroup_v2_detection(self, mock_exists):
        """Test cgroup v2 detection."""
        mock_exists.return_value = True
        monitor = CGroupMemoryMonitor()
        assert monitor.cgroup_version == 2
    
    @patch('pathlib.Path.exists')
    def test_cgroup_v1_detection(self, mock_exists):
        """Test cgroup v1 detection."""
        def exists_side_effect(path):
            return "memory.limit_in_bytes" in str(path)
        mock_exists.side_effect = exists_side_effect
        monitor = CGroupMemoryMonitor()
        assert monitor.cgroup_version == 1
    
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.exists')
    def test_cgroup_v1_metrics(self, mock_exists, mock_read):
        """Test reading cgroup v1 metrics."""
        mock_exists.return_value = True
        mock_read.side_effect = ["1073741824", "2147483648"]  # 1GB used, 2GB limit
        
        monitor = CGroupMemoryMonitor()
        monitor.cgroup_version = 1
        pressure = monitor._read_cgroup_v1()
        
        assert pressure.usage_bytes == 1073741824
        assert pressure.limit_bytes == 2147483648
        assert pressure.usage_percent == 50.0
        assert pressure.pressure_level == "none"
        assert pressure.is_containerized is True
    
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.exists')
    def test_cgroup_v2_metrics(self, mock_exists, mock_read):
        """Test reading cgroup v2 metrics."""
        mock_exists.return_value = True
        mock_read.side_effect = ["1610612736", "2147483648"]  # 1.5GB used, 2GB limit
        
        monitor = CGroupMemoryMonitor()
        monitor.cgroup_version = 2
        pressure = monitor._read_cgroup_v2()
        
        assert pressure.usage_bytes == 1610612736
        assert pressure.limit_bytes == 2147483648
        assert 74 < pressure.usage_percent < 76
        assert pressure.pressure_level == "low"
    
    @patch('psutil.virtual_memory')
    def test_fallback_metrics(self, mock_psutil):
        """Test fallback to psutil when cgroups unavailable."""
        mock_mem = MagicMock()
        mock_mem.used = 8589934592  # 8GB
        mock_mem.total = 17179869184  # 16GB
        mock_mem.percent = 50.0
        mock_psutil.return_value = mock_mem
        
        monitor = CGroupMemoryMonitor()
        monitor.is_available = False
        pressure = monitor._get_fallback_metrics()
        
        assert pressure.usage_bytes == 8589934592
        assert pressure.is_containerized is False
        assert pressure.pressure_level == "none"
    
    def test_should_throttle(self):
        """Test throttling decision logic."""
        monitor = CGroupMemoryMonitor()
        
        with patch.object(monitor, 'get_memory_pressure') as mock_pressure:
            mock_pressure.return_value = MemoryPressure(
                usage_bytes=1000, limit_bytes=2000, 
                usage_percent=90, pressure_level="high", is_containerized=True
            )
            assert monitor.should_throttle() is True
            
            mock_pressure.return_value = MemoryPressure(
                usage_bytes=1000, limit_bytes=2000,
                usage_percent=50, pressure_level="none", is_containerized=True
            )
            assert monitor.should_throttle() is False
    
    def test_metrics_dict_format(self):
        """Test metrics dictionary output format."""
        monitor = CGroupMemoryMonitor()
        
        with patch.object(monitor, 'get_memory_pressure') as mock_pressure:
            mock_pressure.return_value = MemoryPressure(
                usage_bytes=1073741824, limit_bytes=2147483648,
                usage_percent=50.0, pressure_level="none", is_containerized=True
            )
            
            metrics = monitor.get_metrics_dict()
            assert "usage_mb" in metrics
            assert "limit_mb" in metrics
            assert "usage_percent" in metrics
            assert "pressure_level" in metrics
            assert metrics["usage_mb"] == 1024.0
            assert metrics["limit_mb"] == 2048.0
    
    def test_unlimited_cgroup_handling(self):
        """Test handling of unlimited cgroup memory."""
        monitor = CGroupMemoryMonitor()
        monitor.cgroup_version = 1
        
        with patch('pathlib.Path.read_text') as mock_read:
            # Simulate unlimited cgroup (very large number)
            mock_read.side_effect = ["1073741824", "9223372036854775807"]
            
            with patch('os.sysconf') as mock_sysconf:
                mock_sysconf.side_effect = [4096, 524288]  # 2GB physical RAM
                pressure = monitor._read_cgroup_v1()
                
                assert pressure.limit_bytes == 4096 * 524288
                assert pressure.usage_percent < 100

    def test_singleton_pattern(self):
        """Test global monitor singleton."""
        monitor1 = get_memory_monitor()
        monitor2 = get_memory_monitor()
        assert monitor1 is monitor2
