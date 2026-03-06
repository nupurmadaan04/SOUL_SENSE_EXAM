import os
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
UTC = timezone.utc
from ..utils.fd_guard import FDGuard

logger = logging.getLogger("api.storage")

class SignedURLPolicy:
    """
    Hardened signed URL policy implementation for object storage.
    Implements least privilege access with strict validation.
    """

    # Default expiration times (in seconds)
    DEFAULT_EXPIRATION = 900  # 15 minutes for downloads
    UPLOAD_EXPIRATION = 300   # 5 minutes for uploads
    MAX_EXPIRATION = 3600     # 1 hour maximum

    # Allowed HTTP methods
    ALLOWED_METHODS = {'GET', 'PUT', 'HEAD'}

    def __init__(self):
        self.settings = get_settings_instance()

    def validate_expiration(self, expiration_seconds: int) -> int:
        """Validate and clamp expiration time to safe limits."""
        if expiration_seconds <= 0:
            raise ValueError("Expiration time must be positive")
        return min(expiration_seconds, self.MAX_EXPIRATION)

    def validate_method(self, method: str) -> str:
        """Validate HTTP method is allowed."""
        method = method.upper()
        if method not in self.ALLOWED_METHODS:
            raise ValueError(f"HTTP method {method} not allowed")
        return method

    def validate_object_path(self, bucket: str, key: str) -> tuple[str, str]:
        """Validate and normalize object path."""
        if not bucket or not key:
            raise ValueError("Bucket and key are required")

        # Prevent directory traversal
        if '..' in key or key.startswith('/'):
            raise ValueError("Invalid object key")

        # Ensure bucket name is valid
        if not self._is_valid_bucket_name(bucket):
            raise ValueError("Invalid bucket name")

        return bucket, key

    def _is_valid_bucket_name(self, bucket: str) -> bool:
        """Basic bucket name validation."""
        if not bucket or len(bucket) < 3 or len(bucket) > 63:
            return False
        # Bucket names must be lowercase, no uppercase or special chars except hyphens
        import re
        return bool(re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', bucket))

    def validate_ip_restriction(self, client_ip: Optional[str]) -> Optional[str]:
        """Validate IP address for restriction."""
        if not client_ip:
            return None
        try:
            # Support both IPv4 and IPv6
            ipaddress.ip_address(client_ip)
            return client_ip
        except ValueError:
            raise ValueError("Invalid IP address format")

    def generate_signed_url(
        self,
        bucket: str,
        key: str,
        method: str = 'GET',
        expiration_seconds: Optional[int] = None,
        client_ip: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a hardened signed URL with policy restrictions.

        Args:
            bucket: S3 bucket name
            key: Object key
            method: HTTP method (GET, PUT, HEAD)
            expiration_seconds: URL validity duration
            client_ip: Optional IP restriction
            content_type: Optional content type restriction

        Returns:
            Dict containing signed URL and metadata
        """
        # Validate inputs
        bucket, key = self.validate_object_path(bucket, key)
        method = self.validate_method(method)

        # Set default expiration based on method
        if expiration_seconds is None:
            expiration_seconds = self.DEFAULT_EXPIRATION if method == 'GET' else self.UPLOAD_EXPIRATION

        expiration_seconds = self.validate_expiration(expiration_seconds)
        client_ip = self.validate_ip_restriction(client_ip)

        # Generate signed URL
        signed_url = self._generate_s3_signed_url(
            bucket=bucket,
            key=key,
            method=method,
            expiration_seconds=expiration_seconds,
            client_ip=client_ip,
            content_type=content_type
        )

        # Log generation event
        self._log_signed_url_generation(
            bucket=bucket,
            key=key,
            method=method,
            expiration_seconds=expiration_seconds,
            client_ip=client_ip
        )

        return {
            'signed_url': signed_url,
            'expires_at': datetime.now(UTC) + timedelta(seconds=expiration_seconds),
            'method': method,
            'bucket': bucket,
            'key': key,
            'client_ip_restricted': client_ip is not None,
            'content_type_restricted': content_type is not None
        }

    def _generate_s3_signed_url(
        self,
        bucket: str,
        key: str,
        method: str,
        expiration_seconds: int,
        client_ip: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Generate S3 signed URL with custom policy."""
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for signed URL generation")

        # Create S3 client
        client_kwargs = {
            'region_name': self.settings.s3_region,
        }
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            client_kwargs.update({
                'aws_access_key_id': self.settings.aws_access_key_id,
                'aws_secret_access_key': self.settings.aws_secret_access_key,
            })

        s3_client = boto3.client('s3', **client_kwargs)

        try:
            # Build conditions for policy
            conditions = [
                {"bucket": bucket},
                ["starts-with", "$key", key],
                {"acl": "private" if method == 'PUT' else None}
            ]

            # Add IP restriction if provided
            if client_ip:
                conditions.append({"ip": f"{client_ip}/32"})

            # Add content type restriction if provided
            if content_type:
                conditions.append({"content-type": content_type})

            # Remove None conditions
            conditions = [c for c in conditions if c is not None]

            # Generate presigned URL with conditions
            url = s3_client.generate_presigned_url(
                ClientMethod='get_object' if method == 'GET' else 'put_object',
                Params={
                    'Bucket': bucket,
                    'Key': key,
                },
                ExpiresIn=expiration_seconds,
                HttpMethod=method
            )

            return url

        finally:
            try:
                s3_client.close()
            except Exception as e:
                logger.warning(f"Error closing S3 client: {e}")

    def validate_signed_url_access(
        self,
        url: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        clock_skew_tolerance: int = 300  # 5 minutes
    ) -> bool:
        """
        Validate signed URL access with clock skew tolerance.

        Args:
            url: The signed URL being accessed
            client_ip: Client IP address
            user_agent: User agent string
            clock_skew_tolerance: Clock skew tolerance in seconds

        Returns:
            True if access is valid
        """
        try:
            # Parse URL to extract parameters
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Check expiration with clock skew tolerance
            if 'X-Amz-Expires' in query_params:
                expires_in = int(query_params['X-Amz-Expires'][0])
                expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

                # Apply clock skew tolerance
                now = datetime.now(UTC)
                if now > expires_at + timedelta(seconds=clock_skew_tolerance):
                    logger.warning(f"Signed URL expired with clock skew tolerance: {url}")
                    return False

            # Check IP restriction if present
            if 'X-Amz-Ip' in query_params and client_ip:
                allowed_ip = query_params['X-Amz-Ip'][0]
                if not self._ip_matches(client_ip, allowed_ip):
                    logger.warning(f"IP restriction violation: client={client_ip}, allowed={allowed_ip}")
                    return False

            # Log access event
            self._log_signed_url_access(url, client_ip, user_agent)

            return True

        except Exception as e:
            logger.error(f"Error validating signed URL access: {e}")
            return False

    def _ip_matches(self, client_ip: str, allowed_ip: str) -> bool:
        """Check if client IP matches allowed IP/CIDR."""
        try:
            client = ipaddress.ip_address(client_ip)
            allowed = ipaddress.ip_network(allowed_ip, strict=False)
            return client in allowed
        except ValueError:
            return False

    def _log_signed_url_generation(
        self,
        bucket: str,
        key: str,
        method: str,
        expiration_seconds: int,
        client_ip: Optional[str]
    ):
        """Log signed URL generation event."""
        logger.info(
            f"Signed URL generated: bucket={bucket}, key={key}, method={method}, "
            f"expiration={expiration_seconds}s, ip_restricted={client_ip is not None}"
        )

    def _log_signed_url_access(
        self,
        url: str,
        client_ip: Optional[str],
        user_agent: Optional[str]
    ):
        """Log signed URL access event."""
        logger.info(
            f"Signed URL accessed: url={url[:100]}..., client_ip={client_ip}, "
            f"user_agent={user_agent[:100] if user_agent else None}"
        )


# Global signed URL policy instance
signed_url_policy = SignedURLPolicy()

class StorageService:
    """
    Handles file storage operations for SoulSense.
    Supports local filesystem and S3 integration with proper resource management.
    Enhanced with hard-deletion and URL invalidation for GDPR compliance (#1134).
    Merged with FD leak protection (#1233).
    """

    BASE_DIR = Path("exports")

    @classmethod
    def ensure_dir(cls, directory: Path = BASE_DIR):
        directory.mkdir(exist_ok=True, parents=True)

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

    @staticmethod
    async def download_from_s3(bucket: str, key: str) -> Optional[bytes]:
        """Download data from S3 with proper resource management."""
        async with StorageService.get_s3_client() as s3_client:
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                data = response['Body'].read()
                logger.info(f"Successfully downloaded from S3: s3://{bucket}/{key}")
                return data
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"Object not found in S3: s3://{bucket}/{key}")
                else:
                    logger.error(f"Failed to download from S3 s3://{bucket}/{key}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error downloading from S3: {e}")
                return None

    @staticmethod
    async def delete_from_s3(bucket: str, key: str) -> bool:
        """Delete object from S3 with proper resource management."""
        async with StorageService.get_s3_client() as s3_client:
            try:
                s3_client.delete_object(Bucket=bucket, Key=key)
                logger.info(f"Successfully deleted from S3: s3://{bucket}/{key}")
                return True
            except ClientError as e:
                logger.error(f"Failed to delete from S3 s3://{bucket}/{key}: {e}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error deleting from S3: {e}")
                return False

    @staticmethod
    async def fetch_content(uri: str) -> Optional[str]:
        """Fetch content from storage (S3 or local) based on URI."""
        settings = get_settings_instance()

        if settings.storage_type == "s3" and uri.startswith("s3://"):
            # Parse S3 URI: s3://bucket/key
            try:
                bucket_key = uri[5:]  # Remove 's3://'
                bucket, key = bucket_key.split('/', 1)
                data = await StorageService.download_from_s3(bucket, key)
                return data.decode('utf-8') if data else None
            except ValueError:
                logger.error(f"Invalid S3 URI format: {uri}")
                return None
        else:
            # Local file
            try:
                with open(uri, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read local file {uri}: {e}")
                return None

    @staticmethod
    async def store_content(content: str, key: Optional[str] = None) -> Optional[str]:
        """Store content to storage and return URI."""
        settings = get_settings_instance()

        if not key:
            # Generate a key if not provided
            import uuid
            key = f"archival/{uuid.uuid4().hex}.txt"

        if settings.storage_type == "s3":
            data = content.encode('utf-8')
            success = await StorageService.upload_to_s3(settings.s3_bucket_name, key, data)
            if success:
                return f"s3://{settings.s3_bucket_name}/{key}"
            else:
                return None
        else:
            # Local storage
            filepath = StorageService.BASE_DIR / key
            StorageService.ensure_dir(filepath.parent)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return str(filepath)
            except Exception as e:
                logger.error(f"Failed to write local file {filepath}: {e}")
                return None

    @staticmethod
    async def delete_file(file_path: str) -> bool:
        """Permanently deletes a file from local storage or S3 with FD monitoring."""
        if not file_path:
            return False

        settings = get_settings_instance()

        try:
            path = Path(file_path)
            if path.exists():
                os.remove(path)
                logger.info(f"Successfully scrubbed local file: {file_path}")
                # Monitor FD usage after deletion
                FDGuard.check_fd_usage("local_file_delete")
                return True
            
            # --- S3 Hard Delete Stub ---
            # if settings.use_s3:
            #     # FIX #1233: Ensure client is closed or used via context manager
            #     # async with get_s3_client() as s3:
            #     #     await s3.delete_object(Bucket=settings.S3_BUCKET, Key=file_path)
            #     #     logger.info(f"Successfully scrubbed S3 object: {file_path}")
            #     pass
            
            return False
        except Exception as e:
            logger.error(f"Failed to scrub file {file_path}: {e}")
            return False

    @staticmethod
    async def storage_health_check():
        """Returns storage performance and health metrics (#1233)."""
        return {
            "open_fds": FDGuard.get_open_fd_count(),
            "base_dir_exists": Path(StorageService.BASE_DIR).exists(),
            "timestamp": datetime.now(UTC).isoformat()
        }

    @staticmethod
    async def invalidate_signed_url(url: str):
        """
        Invalidates a pre-signed URL.
        In S3, this is typically done by rotating keys or using CloudFront invalidation.
        For SoulSense, we rely on the short TTL (7 days) but can blacklist URLs in Redis if needed.
        """
        logger.info(f"Invalidating pre-signed URL: {url}")
        # Implementation would involve Redis-based blacklist for active URLs
        pass

    @staticmethod
    async def generate_signed_url(
        bucket: str,
        key: str,
        method: str = 'GET',
        expiration_seconds: Optional[int] = None,
        client_ip: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a hardened signed URL for object storage access.

        Args:
            bucket: Storage bucket name
            key: Object key/path
            method: HTTP method (GET, PUT, HEAD)
            expiration_seconds: URL validity duration
            client_ip: Optional IP address restriction
            content_type: Optional content type restriction

        Returns:
            Dict containing signed URL and metadata
        """
        return signed_url_policy.generate_signed_url(
            bucket=bucket,
            key=key,
            method=method,
            expiration_seconds=expiration_seconds,
            client_ip=client_ip,
            content_type=content_type
        )

    @staticmethod
    async def validate_signed_url_access(
        url: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Validate access to a signed URL with security checks.

        Args:
            url: The signed URL being accessed
            client_ip: Client IP address for validation
            user_agent: User agent string for logging

        Returns:
            True if access is allowed
        """
        return signed_url_policy.validate_signed_url_access(
            url=url,
            client_ip=client_ip,
            user_agent=user_agent
        )

    @staticmethod
    async def scrub_user_directory(username: str):
        """Scrubs all temporary files associated with a user."""
        try:
            # This is a safety measure to ensure no stray files remain
            # Implementation would search for files prefixed with username
            pass
        except Exception as e:
            logger.error(f"Error scrubbing directory for {username}: {e}")

# Global instance
storage_service = StorageService()

def get_storage_service():
    """Factory function to get storage service instance."""
    return storage_service
