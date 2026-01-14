"""
S3 storage implementation.
"""
from typing import Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from django.conf import settings


class S3Storage:
    """S3 storage wrapper."""

    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket = settings.AWS_STORAGE_BUCKET_NAME

    def upload_file(
        self,
        file_obj,
        folder: str = "",
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to S3 and return the URL."""
        if filename is None:
            filename = str(uuid4())

        key = f"{folder}/{filename}" if folder else filename

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs=extra_args,
        )

        return self.get_url(key)

    def delete_file(self, key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_url(self, key: str) -> str:
        """Get the URL for a file."""
        return f"{settings.AWS_S3_ENDPOINT_URL}/{self.bucket}/{key}"

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for temporary access."""
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expiration,
        )

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
