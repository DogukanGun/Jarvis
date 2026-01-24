"""Tests for Storage client."""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from app.clients.storage_client.client import StorageClient, MockS3Client


class TestStorageClient:
    """Tests for StorageClient."""

    def test_init(self):
        """Test client initialization."""
        client = StorageClient(
            endpoint="localhost:9000",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
        )

        assert client.endpoint == "localhost:9000"
        assert client.bucket == "test-bucket"
        assert client._client is None

    def test_generate_key(self):
        """Test key generation."""
        client = StorageClient()
        key = client._generate_key("test-job-123", "png")

        assert "renders" in key
        assert "test-job-123" in key
        assert key.endswith(".png")

    def test_get_content_type(self):
        """Test content type detection."""
        client = StorageClient()

        assert client._get_content_type("png") == "image/png"
        assert client._get_content_type("jpg") == "image/jpeg"
        assert client._get_content_type("mp4") == "video/mp4"
        assert client._get_content_type("unknown") == "application/octet-stream"

    def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        client = StorageClient()
        client._client = MockS3Client()

        result = client.upload_file(
            file_path="/nonexistent/file.png",
            job_id="test-123",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_upload_file_mock(self):
        """Test upload with mock client."""
        client = StorageClient(public_url="http://localhost:9000")
        client._client = MockS3Client()

        # Create a temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = client.upload_file(
                file_path=temp_path,
                job_id="test-123",
            )

            assert result["success"] is True
            assert "test-123" in result["url"]
            assert result["bucket"] == "media-renders"
        finally:
            os.unlink(temp_path)

    def test_upload_bytes_mock(self):
        """Test bytes upload with mock client."""
        client = StorageClient(public_url="http://localhost:9000")
        client._client = MockS3Client()

        result = client.upload_bytes(
            data=b"fake image data",
            job_id="test-456",
            extension="png",
        )

        assert result["success"] is True
        assert "test-456" in result["url"]


class TestMockS3Client:
    """Tests for MockS3Client."""

    def test_head_bucket(self):
        """Test mock head_bucket."""
        mock = MockS3Client()
        mock.head_bucket(Bucket="test")  # Should not raise

    def test_create_bucket(self):
        """Test mock create_bucket."""
        mock = MockS3Client()
        mock.create_bucket(Bucket="test")  # Should not raise

    def test_upload_fileobj(self):
        """Test mock upload_fileobj."""
        import io

        mock = MockS3Client()
        mock.upload_fileobj(
            io.BytesIO(b"data"),
            "bucket",
            "key",
            ExtraArgs={"ContentType": "image/png"},
        )  # Should not raise
