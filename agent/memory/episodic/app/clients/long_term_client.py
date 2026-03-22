"""
Long-Term Memory Client Abstraction

Backend-agnostic client that delegates to either Mem0 or Supermemory
based on configuration. Allows switching backends without changing
graph node code.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LongTermMemoryClient:
    """Unified client for long-term memory operations."""

    def __init__(self, backend: str = None):
        """
        Initialize with configured backend.

        Args:
            backend: "mem0" or "supermemory" (default from config)
        """
        from app.config import config
        self.backend = backend or config.LONG_TERM_BACKEND
        self._client = None

    def _get_client(self):
        """Lazy-initialize the underlying client."""
        if self._client is None:
            if self.backend == "supermemory":
                from app.clients.supermemory_client import get_supermemory_client
                self._client = get_supermemory_client()
            else:
                from app.clients.mem0_client import get_mem0_client
                self._client = get_mem0_client()
        return self._client

    def get_all(self, user_id: str) -> Dict[str, Any]:
        """Retrieve all memories for a user."""
        return self._get_client().get_all(user_id)

    def search(self, user_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search memories for a user."""
        return self._get_client().search(user_id=user_id, query=query, limit=limit)

    def add(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a new memory."""
        return self._get_client().add(user_id=user_id, text=text, metadata=metadata)

    def add_messages(self, user_id: str, messages: list, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add memories from conversation messages."""
        return self._get_client().add_messages(user_id=user_id, messages=messages, metadata=metadata)

    def get_profile(self, user_id: str, query: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get user profile (Supermemory-only).

        Returns None if backend doesn't support profiles.
        """
        if self.backend == "supermemory":
            return self._get_client().get_profile(user_id=user_id, query=query)
        return None

    def health_check(self) -> bool:
        """Check if the backend is healthy."""
        return self._get_client().health_check()

    def close(self):
        """Close the underlying client."""
        if self._client is not None:
            self._client.close()


# Module-level singleton
_long_term_client: Optional[LongTermMemoryClient] = None


def get_long_term_client(backend: str = None) -> LongTermMemoryClient:
    """
    Get or create the long-term memory client singleton.

    Args:
        backend: Optional backend override

    Returns:
        LongTermMemoryClient instance
    """
    global _long_term_client

    if _long_term_client is None or (backend and _long_term_client.backend != backend):
        _long_term_client = LongTermMemoryClient(backend=backend)

    return _long_term_client
