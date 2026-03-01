"""
Storage Service for Cloud Archival (#1125)
Handles interactions with AWS S3 or compatible storage services.
"""
import logging
import boto3
from botocore.exceptions import ClientError
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.s3_client = None
        
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.settings.aws_access_key_id,
                    aws_secret_access_key=self.settings.aws_secret_access_key,
                    region_name=self.settings.s3_region
                )
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")

    def upload_encrypted_content(self, key: str, content: str, metadata: dict = None) -> str:
        """
        Uploads encrypted content to cold storage.
        Returns the URI pointer.
        """
        if not self.s3_client:
            # Mock behavior if S3 is not configured (for dev/demo)
            logger.warning(f"S3 not configured. Simulating archival for {key}")
            return f"s3://{self.settings.s3_bucket_name}/{key}"

        try:
            self.s3_client.put_object(
                Bucket=self.settings.s3_bucket_name,
                Key=key,
                Body=content,
                Metadata=metadata or {}
            )
            return f"s3://{self.settings.s3_bucket_name}/{key}"
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            raise e

    def get_presigned_url(self, pointer: str, expires_in: int = 3600) -> str:
        """
        Generates a pre-signed URL for temporary access to archived data.
        """
        if not self.s3_client or not pointer.startswith("s3://"):
            # Mock behavior / fallback
            return f"https://mock-s3-storage.soulsense.io/{pointer.replace('s3://', '')}?token=temporary"

        try:
            # Extract bucket and key from s3://bucket/key
            path = pointer.replace("s3://", "")
            bucket, key = path.split("/", 1)
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            return ""

    async def fetch_content(self, pointer: str) -> str:
        """
        Directly fetches content from storage.
        """
        if not self.s3_client or not pointer.startswith("s3://"):
             # Simulation for demo
             return "ENC:simulated_archived_content_ciphertext"

        try:
            path = pointer.replace("s3://", "")
            bucket, key = path.split("/", 1)
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to fetch from S3: {e}")
            return ""

_storage_service = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
