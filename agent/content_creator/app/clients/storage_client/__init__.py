"""Storage client for MinIO/S3."""
from app.clients.storage_client.client import (
    StorageClient,
    get_storage_client,
)

__all__ = [
    "StorageClient",
    "get_storage_client",
]
