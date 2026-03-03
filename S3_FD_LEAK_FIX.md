# S3 Operations File Descriptor Leak Fix (#1189)

## Overview

This document describes the fix for file descriptor leaks in S3 operations that could lead to resource exhaustion under high load or during network failures.

## Problem Description

**Issue**: S3 client connections were not properly closed on exceptions, leading to file descriptor exhaustion from cloud operations.

**Impact**:
- File descriptor leaks during S3 operations
- Potential system resource exhaustion
- Application instability under load
- Memory leaks from unclosed connections

**Edge Cases**:
- Timeout during upload operations
- Partial file write failures
- Network connectivity issues
- S3 service unavailability

## Root Cause

The original implementation did not use proper resource management for S3 clients. When exceptions occurred during S3 operations, client connections remained open, consuming file descriptors that were never released.

## Solution

### 1. Context-Managed S3 Client

Implemented an async context manager for S3 client lifecycle management:

```python
@staticmethod
@asynccontextmanager
async def get_s3_client():
    """Context manager for S3 client to ensure proper cleanup."""
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is required for S3 operations. Install it via pip.")

    settings = get_settings_instance()
    client = None
    try:
        # Create S3 client with proper configuration
        client_kwargs = {
            'region_name': settings.s3_region,
        }
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs.update({
                'aws_access_key_id': settings.aws_access_key_id,
                'aws_secret_access_key': settings.aws_secret_access_key,
            })

        client = boto3.client('s3', **client_kwargs)
        yield client
    finally:
        # Ensure client is properly closed to prevent FD leaks
        if client:
            try:
                client.close()
            except Exception as e:
                logger.warning(f"Error closing S3 client: {e}")
```

### 2. Safe S3 Operations

All S3 operations now use the context manager:

```python
@staticmethod
async def upload_to_s3(bucket: str, key: str, data: bytes) -> bool:
    """Upload data to S3 with proper resource management."""
    async with StorageService.get_s3_client() as s3_client:
        try:
            s3_client.put_object(Bucket=bucket, Key=key, Body=data)
            logger.info(f"Successfully uploaded to S3: s3://{bucket}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3 s3://{bucket}/{key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False
```

### 3. Journal Archival System

Implemented automated archival of stale journal entries to cold storage:

- Journals older than `archival_threshold_years` (default: 2 years) are moved to S3
- Database content is cleared and `archive_pointer` is set to S3 URI
- Seamless retrieval via `fetch_content()` method

## Files Modified

### Core Implementation
- `backend/fastapi/api/services/storage_service.py` - Added S3 client management
- `backend/fastapi/api/services/data_archival_service.py` - Added archival logic
- `backend/fastapi/api/celery_tasks.py` - Added background archival task

### Configuration
- `backend/fastapi/api/config.py` - S3 settings already present
- `backend/fastapi/requirements.txt` - Added boto3 dependency

### Testing
- `backend/fastapi/tests/unit/test_storage_service.py` - Comprehensive test suite

## Configuration

### Environment Variables

```bash
# S3 Configuration
STORAGE_TYPE=s3
S3_BUCKET_NAME=soulsense-archival
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Archival Settings
ARCHIVAL_THRESHOLD_YEARS=2
```

### Dependencies

```txt
boto3>=1.28.0
```

## Testing

### Unit Tests

Run the storage service tests:

```bash
cd backend/fastapi
python -m pytest tests/unit/test_storage_service.py -v
```

### Integration Tests

For full integration testing with AWS S3:

1. Configure AWS credentials
2. Run archival demo:
   ```bash
   python demo_archival.py
   ```

### Stress Testing

To test FD leak prevention under load:

```python
# Simulate multiple S3 operations
for i in range(1000):
    await storage_service.upload_to_s3(bucket, f"test-{i}", b"test data")
# Verify no FD leaks (check system file descriptor count)
```

## Monitoring

### File Descriptor Monitoring

Monitor open file descriptors:

```bash
# Linux
lsof -p $(pgrep python) | wc -l

# Windows (PowerShell)
Get-Process python | Select-Object -ExpandProperty Handles
```

### S3 Operation Metrics

Key metrics to monitor:
- S3 operation success/failure rates
- Client connection pool size
- Memory usage during bulk operations
- File descriptor count over time

## Best Practices

### 1. Always Use Context Managers

```python
# ✅ Good
async with StorageService.get_s3_client() as client:
    client.put_object(...)

# ❌ Bad
client = boto3.client('s3')
client.put_object(...)  # Potential leak
```

### 2. Handle Exceptions Properly

```python
try:
    async with StorageService.get_s3_client() as client:
        client.put_object(...)
except Exception as e:
    logger.error(f"S3 operation failed: {e}")
    # Client is automatically closed by context manager
```

### 3. Configure Timeouts

Set appropriate timeouts for S3 operations to prevent hanging connections:

```python
# In boto3 client config
client = boto3.client('s3',
    config=Config(
        region_name='us-east-1',
        read_timeout=60,
        retries={'max_attempts': 3}
    )
)
```

## Troubleshooting

### Common Issues

1. **"boto3 not installed"**
   - Install boto3: `pip install boto3>=1.28.0`

2. **"AWS credentials not found"**
   - Configure AWS credentials via environment variables or AWS CLI
   - Check IAM permissions for S3 operations

3. **File descriptor leaks still occurring**
   - Ensure all S3 operations use the context manager
   - Check for direct boto3.client() usage outside the service
   - Monitor with `lsof` or process explorer

4. **S3 timeouts**
   - Increase timeout values in client configuration
   - Implement retry logic with exponential backoff

### Debug Logging

Enable debug logging for S3 operations:

```python
import logging
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

## Security Considerations

- AWS credentials are properly configured and rotated
- S3 bucket policies restrict access appropriately
- Data encryption at rest and in transit
- Audit logging for all S3 operations

## Performance Impact

- Minimal performance impact from context manager overhead
- Improved reliability from proper resource cleanup
- Reduced memory usage from closed connections
- Better scalability under high load

## Future Improvements

1. **Connection Pooling**: Implement connection pooling for better performance
2. **Circuit Breaker**: Add circuit breaker pattern for S3 failures
3. **Metrics**: Add detailed metrics for S3 operations
4. **Multi-region**: Support for multi-region S3 deployments
5. **Backup Storage**: Fallback to local storage when S3 is unavailable

## Related Issues

- #1125: Automated Cold Storage Archival Pipeline
- #1134: GDPR Compliance for Data Deletion
- #1189: File Descriptor Leak in S3 Operations (This fix)

## Verification

To verify the fix is working:

1. Run the test suite
2. Monitor file descriptor count during S3 operations
3. Simulate network failures and verify cleanup
4. Check logs for proper client closure messages

The fix ensures that all S3 client connections are properly managed and closed, preventing file descriptor exhaustion and improving system stability.</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\S3_FD_LEAK_FIX.md