import logging
import os
from datetime import datetime, UTC
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional

logger = logging.getLogger("api.storage")

class StorageService:
    """
    Handles hard-deletion of archived S3 blobs and provides utility 
    methods for storage-related operations in the Soul Sense distributed environment.
    """

    @staticmethod
    def get_s3_client():
        """
        Initializes the Boto3 S3 client using environment variables or IAM role.
        """
        # Note: In a real prod environment, AWS keys are handled per-session or IAM role.
        return boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    @staticmethod
    async def hard_delete_user_blobs(user_id: int) -> int:
        """
        Scans S3 bucket for all objects related to a user (exports, backups, logs)
        and performs a permanent 'Hard Delete'.
        
        S3 key convention: users/{user_id}/...
        Returns: Number of objects successfully purged.
        """
        s3 = StorageService.get_s3_client()
        bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "soul-sense-exports")
        prefix = f"users/{user_id}/"
        
        count = 0
        try:
            # 1. List objects by prefix
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            # 2. Collect keys for batch deletion
            delete_batch = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        delete_batch.append({'Key': obj['Key']})
                        count += 1
                        
                        # S3 delete_objects limit is 1000 per request
                        if len(delete_batch) >= 1000:
                            s3.delete_objects(Bucket=bucket, Delete={'Objects': delete_batch})
                            delete_batch = []
            
            # 3. Final batch
            if delete_batch:
                s3.delete_objects(Bucket=bucket, Delete={'Objects': delete_batch})
                
            logger.info(f"Permanently purged {count} S3 blobs for user {user_id}")
            return count

        except ClientError as e:
            logger.error(f"S3 hard-delete failed for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected storage error: {e}")
            raise

    @staticmethod
    def invalidate_presigned_url(object_key: str) -> None:
        """
        Pre-signed URLs cannot be 'revoked' directly via API without rotating keys.
        The architected solution is to DELETE the underlying object, 
        rendering the URL useless (returns 404).
        """
        s3 = StorageService.get_s3_client()
        bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "soul-sense-exports")
        
        try:
            s3.delete_object(Bucket=bucket, Key=object_key)
            logger.info(f"Invalidated URL by deleting source object: {object_key}")
        except ClientError as e:
            logger.error(f"Failed to invalidate URL for {object_key}: {e}")
            raise
