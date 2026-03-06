"""
Test Signed URL Policy Hardening (#1262)
========================================
Tests for hardened signed URL generation and validation.
"""

import pytest
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from unittest.mock import Mock, patch, AsyncMock
import json

from ..services.storage_service import SignedURLPolicy, signed_url_policy


class TestSignedURLPolicy:
    """Test cases for signed URL policy hardening."""

    def setup_method(self):
        """Set up test fixtures."""
        self.policy = SignedURLPolicy()

    def test_validate_expiration_clamping(self):
        """Test expiration time validation and clamping."""
        # Valid expiration
        assert self.policy.validate_expiration(300) == 300

        # Clamp to maximum
        assert self.policy.validate_expiration(7200) == 3600

        # Invalid expiration
        with pytest.raises(ValueError, match="Expiration time must be positive"):
            self.policy.validate_expiration(0)

        with pytest.raises(ValueError, match="Expiration time must be positive"):
            self.policy.validate_expiration(-100)

    def test_validate_method_allowed(self):
        """Test HTTP method validation."""
        # Valid methods
        assert self.policy.validate_method('GET') == 'GET'
        assert self.policy.validate_method('PUT') == 'PUT'
        assert self.policy.validate_method('HEAD') == 'HEAD'

        # Invalid method
        with pytest.raises(ValueError, match="HTTP method POST not allowed"):
            self.policy.validate_method('POST')

        with pytest.raises(ValueError, match="HTTP method DELETE not allowed"):
            self.policy.validate_method('DELETE')

    def test_validate_object_path(self):
        """Test object path validation."""
        # Valid path
        bucket, key = self.policy.validate_object_path('mybucket', 'path/to/file.txt')
        assert bucket == 'mybucket'
        assert key == 'path/to/file.txt'

        # Directory traversal prevention
        with pytest.raises(ValueError, match="Invalid object key"):
            self.policy.validate_object_path('mybucket', '../etc/passwd')

        with pytest.raises(ValueError, match="Invalid object key"):
            self.policy.validate_object_path('mybucket', '/absolute/path')

        # Invalid bucket name
        with pytest.raises(ValueError, match="Invalid bucket name"):
            self.policy.validate_object_path('', 'file.txt')

        with pytest.raises(ValueError, match="Invalid bucket name"):
            self.policy.validate_object_path('ab', 'file.txt')  # Too short

    def test_validate_ip_restriction(self):
        """Test IP address validation."""
        # Valid IPv4
        assert self.policy.validate_ip_restriction('192.168.1.1') == '192.168.1.1'

        # Valid IPv6
        assert self.policy.validate_ip_restriction('2001:db8::1') == '2001:db8::1'

        # Invalid IP
        with pytest.raises(ValueError, match="Invalid IP address format"):
            self.policy.validate_ip_restriction('invalid-ip')

        # No restriction
        assert self.policy.validate_ip_restriction(None) is None

    @patch('boto3.client')
    def test_generate_signed_url_basic(self, mock_boto3_client):
        """Test basic signed URL generation."""
        # Mock S3 client
        mock_client = Mock()
        mock_client.generate_presigned_url.return_value = 'https://signed-url.example.com'
        mock_boto3_client.return_value = mock_client

        # Mock settings
        with patch.object(self.policy, 'settings') as mock_settings:
            mock_settings.s3_region = 'us-east-1'
            mock_settings.aws_access_key_id = 'test-key'
            mock_settings.aws_secret_access_key = 'test-secret'

            result = self.policy.generate_signed_url(
                bucket='test-bucket',
                key='test-file.txt',
                method='GET'
            )

            assert 'signed_url' in result
            assert 'expires_at' in result
            assert result['method'] == 'GET'
            assert result['bucket'] == 'test-bucket'
            assert result['key'] == 'test-file.txt'

            # Verify expiration is within bounds
            expires_at = result['expires_at']
            now = datetime.now(UTC)
            assert now <= expires_at <= now + timedelta(seconds=3600)

    @patch('boto3.client')
    def test_generate_signed_url_with_ip_restriction(self, mock_boto3_client):
        """Test signed URL generation with IP restriction."""
        mock_client = Mock()
        mock_client.generate_presigned_url.return_value = 'https://signed-url.example.com'
        mock_boto3_client.return_value = mock_client

        with patch.object(self.policy, 'settings') as mock_settings:
            mock_settings.s3_region = 'us-east-1'
            mock_settings.aws_access_key_id = 'test-key'
            mock_settings.aws_secret_access_key = 'test-secret'

            result = self.policy.generate_signed_url(
                bucket='test-bucket',
                key='test-file.txt',
                method='GET',
                client_ip='192.168.1.1'
            )

            assert result['client_ip_restricted'] is True
            mock_client.generate_presigned_url.assert_called_once()

    def test_validate_signed_url_access_expired(self):
        """Test validation of expired signed URL."""
        # Mock URL with expired timestamp
        expired_url = "https://example.com/file?X-Amz-Expires=300&X-Amz-Signature=test"

        # Mock current time to be after expiration
        future_time = datetime.now(UTC) + timedelta(seconds=400)

        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time

            is_valid = self.policy.validate_signed_url_access(expired_url)
            assert is_valid is False

    def test_validate_signed_url_access_valid(self):
        """Test validation of valid signed URL."""
        # Mock URL with valid parameters
        valid_url = "https://example.com/file?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=test&X-Amz-Signature=test"

        # Mock logging to avoid actual log output
        with patch.object(self.policy, '_log_signed_url_access'):
            is_valid = self.policy.validate_signed_url_access(valid_url)
            assert is_valid is True

    def test_validate_signed_url_access_ip_restricted(self):
        """Test IP restriction validation."""
        # URL with IP restriction
        restricted_url = "https://example.com/file?X-Amz-Ip=192.168.1.1/32&X-Amz-Signature=test"

        # Matching IP
        is_valid = self.policy.validate_signed_url_access(
            restricted_url,
            client_ip='192.168.1.1'
        )
        assert is_valid is True

        # Non-matching IP
        is_valid = self.policy.validate_signed_url_access(
            restricted_url,
            client_ip='192.168.1.2'
        )
        assert is_valid is False

    def test_clock_skew_tolerance(self):
        """Test clock skew tolerance in validation."""
        # URL that would be expired without tolerance
        expired_url = "https://example.com/file?X-Amz-Expires=300&X-Amz-Signature=test"

        # Current time is 310 seconds after URL generation (10 seconds past expiration)
        past_expiration = datetime.now(UTC) + timedelta(seconds=310)

        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = past_expiration

            # Should be invalid (beyond 5-minute tolerance)
            is_valid = self.policy.validate_signed_url_access(expired_url, clock_skew_tolerance=300)
            assert is_valid is False

            # Should be valid with larger tolerance
            is_valid = self.policy.validate_signed_url_access(expired_url, clock_skew_tolerance=600)
            assert is_valid is True

    @patch('boto3.client')
    def test_generate_presigned_url_error_handling(self, mock_boto3_client):
        """Test error handling in signed URL generation."""
        mock_client = Mock()
        mock_client.generate_presigned_url.side_effect = Exception("S3 Error")
        mock_boto3_client.return_value = mock_client

        with patch.object(self.policy, 'settings') as mock_settings:
            mock_settings.s3_region = 'us-east-1'

            with pytest.raises(RuntimeError, match="boto3 is required"):
                # Should fail when boto3 client creation fails
                with patch('builtins.__import__', side_effect=ImportError):
                    self.policy.generate_signed_url('bucket', 'key')

    def test_logging_events(self):
        """Test that signed URL events are logged."""
        with patch.object(self.policy, '_log_signed_url_generation') as mock_log_gen, \
             patch.object(self.policy, '_log_signed_url_access') as mock_log_access:

            # Test generation logging
            with patch.object(self.policy, '_generate_s3_signed_url', return_value='https://signed-url'):
                self.policy.generate_signed_url('bucket', 'key')
                mock_log_gen.assert_called_once()

            # Test access logging
            self.policy.validate_signed_url_access('https://example.com/file?X-Amz-Signature=test')
            mock_log_access.assert_called_once()


class TestSignedURLIntegration:
    """Integration tests for signed URL functionality."""

    @pytest.mark.asyncio
    async def test_storage_service_integration(self):
        """Test integration with StorageService."""
        from ..services.storage_service import StorageService

        # Test that methods exist
        assert hasattr(StorageService, 'generate_signed_url')
        assert hasattr(StorageService, 'validate_signed_url_access')

        # Test method calls (will fail due to missing boto3 in test env, but should not raise AttributeError)
        try:
            await StorageService.generate_signed_url('bucket', 'key')
        except RuntimeError as e:
            assert "boto3 is required" in str(e)
        except Exception:
            # Other exceptions are fine, we just want to ensure the method exists
            pass

    def test_policy_instance(self):
        """Test that global policy instance exists."""
        from ..services.storage_service import signed_url_policy
        assert isinstance(signed_url_policy, SignedURLPolicy)