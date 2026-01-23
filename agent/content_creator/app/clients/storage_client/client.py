"""
Storage Client for MinIO/S3.

Handles file uploads for generated media.
"""
import logging
import os
from datetime import datetime
from typing import Optional, BinaryIO
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageClient:
    """
    S3-compatible storage client for MinIO.

    Handles:
    - Uploading generated images/videos
    - Generating public URLs
    - Managing bucket lifecycle
    """

    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "media-renders",
        use_ssl: bool = False,
        public_url: str = "http://localhost:9000",
    ):
        """
        Initialize storage client.

        Args:
            endpoint: MinIO/S3 endpoint
            access_key: Access key ID
            secret_key: Secret access key
            bucket: Default bucket name
            use_ssl: Whether to use SSL
            public_url: Public URL for accessing uploaded files
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.use_ssl = use_ssl
        self.public_url = public_url.rstrip('/')
        self._client = None

    def _init_client(self):
        """Initialize S3 client lazily."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                protocol = "https" if self.use_ssl else "http"
                endpoint_url = f"{protocol}://{self.endpoint}"

                self._client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    config=Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'},
                    ),
                )
                logger.info(f"S3 client initialized for {endpoint_url}")

                # Ensure bucket exists
                self._ensure_bucket()

            except ImportError:
                logger.warning("boto3 not installed, using mock client")
                self._client = MockS3Client()
            except Exception as e:
                logger.warning(f"S3 client init failed: {e}, using mock")
                self._client = MockS3Client()

    def _ensure_bucket(self):
        """Ensure the bucket exists, create if not."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
            logger.debug(f"Bucket {self.bucket} exists")
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created bucket {self.bucket}")
            except Exception as e:
                logger.warning(f"Could not create bucket {self.bucket}: {e}")

    def _generate_key(self, job_id: str, extension: str) -> str:
        """
        Generate a unique object key with date-based path.

        Args:
            job_id: Job ID for the render
            extension: File extension (e.g., 'png', 'mp4')

        Returns:
            Object key like 'renders/2024/01/23/job_id.png'
        """
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        return f"renders/{date_path}/{job_id}.{extension}"

    def upload_file(
        self,
        file_path: str,
        job_id: str,
        extension: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> dict:
        """
        Upload a file to storage.

        Args:
            file_path: Local path to file
            job_id: Job ID for naming
            extension: Override file extension
            content_type: Override content type

        Returns:
            dict with 'success', 'url', 'error', 'bucket', 'key'
        """
        self._init_client()

        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "url": None,
                    "error": f"File not found: {file_path}",
                    "bucket": self.bucket,
                    "key": "",
                }

            # Determine extension and content type
            ext = extension or path.suffix.lstrip('.')
            key = self._generate_key(job_id, ext)

            content_type = content_type or self._get_content_type(ext)

            # Upload
            extra_args = {"ContentType": content_type}

            with open(file_path, 'rb') as f:
                self._client.upload_fileobj(
                    f,
                    self.bucket,
                    key,
                    ExtraArgs=extra_args,
                )

            url = f"{self.public_url}/{self.bucket}/{key}"
            logger.info(f"Uploaded {file_path} to {url}")

            return {
                "success": True,
                "url": url,
                "error": None,
                "bucket": self.bucket,
                "key": key,
            }

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                "success": False,
                "url": None,
                "error": str(e),
                "bucket": self.bucket,
                "key": "",
            }

    def upload_bytes(
        self,
        data: bytes,
        job_id: str,
        extension: str,
        content_type: Optional[str] = None,
    ) -> dict:
        """
        Upload bytes directly to storage.

        Args:
            data: File content as bytes
            job_id: Job ID for naming
            extension: File extension
            content_type: Content type

        Returns:
            dict with 'success', 'url', 'error', 'bucket', 'key'
        """
        self._init_client()

        try:
            key = self._generate_key(job_id, extension)
            content_type = content_type or self._get_content_type(extension)

            import io
            self._client.upload_fileobj(
                io.BytesIO(data),
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )

            url = f"{self.public_url}/{self.bucket}/{key}"
            logger.info(f"Uploaded {len(data)} bytes to {url}")

            return {
                "success": True,
                "url": url,
                "error": None,
                "bucket": self.bucket,
                "key": key,
            }

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                "success": False,
                "url": None,
                "error": str(e),
                "bucket": self.bucket,
                "key": "",
            }

    def _get_content_type(self, extension: str) -> str:
        """Get content type from extension."""
        content_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "webm": "video/webm",
        }
        return content_types.get(extension.lower(), "application/octet-stream")

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Object key to delete

        Returns:
            True if successful
        """
        self._init_client()

        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted {key} from {self.bucket}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False


class MockS3Client:
    """Mock S3 client for testing/fallback."""

    def head_bucket(self, Bucket):
        pass

    def create_bucket(self, Bucket):
        pass

    def upload_fileobj(self, Fileobj, Bucket, Key, ExtraArgs=None):
        logger.debug(f"[MOCK] Would upload to {Bucket}/{Key}")

    def delete_object(self, Bucket, Key):
        logger.debug(f"[MOCK] Would delete {Bucket}/{Key}")


# Singleton instance
_storage_instance: Optional[StorageClient] = None


def get_storage_client() -> StorageClient:
    """
    Get singleton storage client instance.

    Returns:
        StorageClient instance
    """
    global _storage_instance

    if _storage_instance is None:
        from app.config import config
        _storage_instance = StorageClient(
            endpoint=config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            bucket=config.MINIO_BUCKET,
            use_ssl=config.MINIO_USE_SSL,
            public_url=config.MINIO_PUBLIC_URL,
        )

    return _storage_instance
