"""
Supermemory API Client

Handles communication with self-hosted Supermemory service.
Drop-in replacement for Mem0Client with enhanced capabilities
(user profiles, relational versioning, temporal grounding).
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SupermemoryClient:
    """Client for Supermemory API operations (self-hosted or cloud)"""

    def __init__(self, base_url: str = "http://localhost:8787", api_key: str = "local-dev-key"):
        """
        Initialize Supermemory client.

        Args:
            base_url: Base URL for Supermemory API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Supermemory SDK client."""
        if self._client is None:
            from supermemory import Supermemory
            self._client = Supermemory(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30.0,
                max_retries=2,
            )
        return self._client

    def close(self):
        """Close the client."""
        if self._client is not None:
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_all(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve all memories for a user via profile endpoint.

        Maps to Mem0Client.get_all() interface.

        Args:
            user_id: User identifier (used as container_tag)

        Returns:
            Response dict with {success, message, data}
        """
        try:
            client = self._get_client()
            response = client.profile(container_tag=user_id)

            # Combine static + dynamic profile items
            items = []
            if hasattr(response, 'profile') and response.profile:
                profile = response.profile
                if hasattr(profile, 'static') and profile.static:
                    for mem in profile.static:
                        items.append(_memory_to_dict(mem, source="static"))
                if hasattr(profile, 'dynamic') and profile.dynamic:
                    for mem in profile.dynamic:
                        items.append(_memory_to_dict(mem, source="dynamic"))

            return {
                "success": True,
                "message": "ok",
                "data": items
            }

        except Exception as e:
            logger.error(f"Supermemory get_all error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def search(self, user_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories for a user.

        Maps to Mem0Client.search() interface.

        Args:
            user_id: User identifier (used as container_tag)
            query: Search query
            limit: Max number of results

        Returns:
            Response dict with {success, message, data}
        """
        try:
            client = self._get_client()
            response = client.search.memories(
                q=query,
                container_tag=user_id,
                limit=limit,
            )

            items = []
            if hasattr(response, 'results') and response.results:
                for result in response.results:
                    items.append(_search_result_to_dict(result))

            return {
                "success": True,
                "message": "ok",
                "data": items
            }

        except Exception as e:
            logger.error(f"Supermemory search error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def add(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a new memory.

        Maps to Mem0Client.add() interface.

        Args:
            user_id: User identifier (used as container_tag)
            text: Memory text content
            metadata: Optional metadata dict

        Returns:
            Response dict with {success, message, data}
        """
        try:
            client = self._get_client()

            kwargs = {
                "content": text,
                "container_tag": user_id,
            }
            if metadata:
                kwargs["metadata"] = metadata

            response = client.add(**kwargs)

            return {
                "success": True,
                "message": "ok",
                "data": {
                    "id": getattr(response, 'id', None),
                    "status": getattr(response, 'status', 'added'),
                }
            }

        except Exception as e:
            logger.error(f"Supermemory add error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def add_messages(self, user_id: str, messages: list, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add memories from conversation messages.

        Converts message list to text and adds as a single memory.

        Args:
            user_id: User identifier
            messages: List of message dicts with 'role' and 'content'
            metadata: Optional metadata dict

        Returns:
            Response dict
        """
        # Convert messages to text format
        parts = []
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")

        text = "\n".join(parts)
        return self.add(user_id=user_id, text=text, metadata=metadata)

    def get_profile(self, user_id: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user profile with static facts and dynamic context.

        This is a Supermemory-specific feature not available in Mem0.

        Args:
            user_id: User identifier (used as container_tag)
            query: Optional search query to include in results

        Returns:
            Profile dict with {static, dynamic, search_results}
        """
        try:
            client = self._get_client()

            kwargs = {"container_tag": user_id}
            if query:
                kwargs["q"] = query

            response = client.profile(**kwargs)

            result = {
                "static": [],
                "dynamic": [],
                "search_results": None,
            }

            if hasattr(response, 'profile') and response.profile:
                profile = response.profile
                if hasattr(profile, 'static') and profile.static:
                    result["static"] = [_memory_to_dict(m) for m in profile.static]
                if hasattr(profile, 'dynamic') and profile.dynamic:
                    result["dynamic"] = [_memory_to_dict(m) for m in profile.dynamic]

            if hasattr(response, 'search_results') and response.search_results:
                sr = response.search_results
                result["search_results"] = {
                    "results": [_search_result_to_dict(r) for r in (sr.results or [])],
                    "total": getattr(sr, 'total', 0),
                    "timing": getattr(sr, 'timing', 0),
                }

            return result

        except Exception as e:
            logger.error(f"Supermemory profile error: {e}")
            return {
                "static": [],
                "dynamic": [],
                "search_results": None,
                "error": str(e),
            }

    def health_check(self) -> bool:
        """Check if Supermemory server is healthy."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


def _memory_to_dict(memory, source: str = None) -> dict:
    """Convert a Supermemory memory object to a plain dict."""
    result = {}
    for attr in ("id", "content", "text", "memory", "created_at", "updated_at", "metadata"):
        val = getattr(memory, attr, None)
        if val is not None:
            result[attr] = val

    # Normalize content field to 'text' for compatibility with Mem0 format
    if "content" in result and "text" not in result:
        result["text"] = result.pop("content")
    if "memory" in result and "text" not in result:
        result["text"] = result.pop("memory")

    if source:
        result["source"] = source

    return result


def _search_result_to_dict(result) -> dict:
    """Convert a Supermemory search result to a plain dict."""
    out = {}
    for attr in ("id", "content", "text", "memory", "score", "metadata", "created_at"):
        val = getattr(result, attr, None)
        if val is not None:
            out[attr] = val

    # Normalize to 'text'
    if "content" in out and "text" not in out:
        out["text"] = out.pop("content")
    if "memory" in out and "text" not in out:
        out["text"] = out.pop("memory")

    return out


def get_supermemory_client(base_url: Optional[str] = None, api_key: Optional[str] = None) -> SupermemoryClient:
    """
    Factory function to get Supermemory client instance.

    Args:
        base_url: Optional base URL override (default from config)
        api_key: Optional API key override (default from config)

    Returns:
        SupermemoryClient instance
    """
    from app.config import config

    base_url = base_url or config.SUPERMEMORY_BASE_URL
    api_key = api_key or config.SUPERMEMORY_API_KEY

    return SupermemoryClient(base_url=base_url, api_key=api_key)
