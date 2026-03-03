import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from api.services.storage_service import StorageService, get_storage_service


class TestStorageService:
    """Test storage service operations with proper resource management."""

    @pytest.fixture
    def storage_service(self):
        return get_storage_service()

    @pytest.mark.asyncio
    async def test_s3_client_context_manager(self, storage_service):
        """Test that S3 client is properly closed after use."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            # Test successful operation
            mock_client.put_object.return_value = None

            result = await storage_service.upload_to_s3('test-bucket', 'test-key', b'test data')

            assert result is True
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_s3_client_context_manager_exception(self, storage_service):
        """Test that S3 client is closed even when exception occurs."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            # Simulate exception during upload
            mock_client.put_object.side_effect = Exception("Upload failed")

            result = await storage_service.upload_to_s3('test-bucket', 'test-key', b'test data')

            assert result is False
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_from_s3_success(self, storage_service):
        """Test successful download from S3."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            mock_body = MagicMock()
            mock_body.read.return_value = b'test content'
            mock_client.get_object.return_value = {'Body': mock_body}

            result = await storage_service.download_from_s3('test-bucket', 'test-key')

            assert result == b'test content'
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_from_s3_not_found(self, storage_service):
        """Test download from S3 when object doesn't exist."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            from botocore.exceptions import ClientError
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            error = ClientError(
                error_response={'Error': {'Code': 'NoSuchKey'}},
                operation_name='GetObject'
            )
            mock_client.get_object.side_effect = error

            result = await storage_service.download_from_s3('test-bucket', 'test-key')

            assert result is None
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_from_s3_success(self, storage_service):
        """Test successful delete from S3."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            mock_client.delete_object.return_value = None

            result = await storage_service.delete_from_s3('test-bucket', 'test-key')

            assert result is True
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_content_s3(self, storage_service):
        """Test fetching content from S3 URI."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            mock_body = MagicMock()
            mock_body.read.return_value = b'{"test": "content"}'
            mock_client.get_object.return_value = {'Body': mock_body}

            result = await storage_service.fetch_content('s3://test-bucket/test-key')

            assert result == '{"test": "content"}'
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_content_local(self, storage_service, tmp_path):
        """Test fetching content from local file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("local content")

        result = await storage_service.fetch_content(str(test_file))

        assert result == "local content"

    @pytest.mark.asyncio
    async def test_store_content_s3(self, storage_service):
        """Test storing content to S3."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            mock_client.put_object.return_value = None

            result = await storage_service.store_content('test content', 'test-key')

            assert result == 's3://soulsense-archival/test-key'
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_content_local(self, storage_service, tmp_path):
        """Test storing content locally."""
        with patch('api.services.storage_service.get_settings_instance') as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings_instance.storage_type = 'local'
            mock_settings.return_value = mock_settings_instance

            result = await storage_service.store_content('test content', 'test-key')

            assert 'test-key' in result
            # Verify file was created
            assert os.path.exists(result)

    @pytest.mark.asyncio
    async def test_delete_file_s3(self, storage_service):
        """Test deleting file from S3."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            mock_client.delete_object.return_value = None

            result = await storage_service.delete_file('s3://test-bucket/test-key')

            assert result is True
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_local(self, storage_service, tmp_path):
        """Test deleting local file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = await storage_service.delete_file(str(test_file))

        assert result is True
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_multiple_s3_operations_no_leak(self, storage_service):
        """Test multiple S3 operations to ensure no file descriptor leaks."""
        with patch('api.services.storage_service.boto3') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.put_object.return_value = None

            # Perform multiple operations
            for i in range(10):
                await storage_service.upload_to_s3('test-bucket', f'test-key-{i}', b'test data')

            # Verify close was called for each operation
            assert mock_client.close.call_count == 10