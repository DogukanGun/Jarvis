"""
Mem0 API Client

Handles HTTP communication with local mem0 memory service.
Based on OpenAPI spec from mem0/openaidocs.json.
"""

import httpx
from typing import Any, Dict, Optional


class Mem0Client:
    """Client for local mem0 API operations"""

    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        """
        Initialize Mem0 client for local server.

        Args:
            base_url: Base URL for mem0 API (default: localhost:8080)
            api_key: Optional API key (not required for local setup)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers (auth optional for local setup)"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_all(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve all memories for a user.

        Uses POST /memory/get-all endpoint (local API).

        Args:
            user_id: User identifier

        Returns:
            Response dict with structure:
            {
                "success": bool,
                "message": str,
                "data": Any
            }
        """
        url = f"{self.base_url}/memory/get-all"
        payload = {"user_id": user_id}

        try:
            response = self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )

            response.raise_for_status()
            data = response.json()

            # Local API returns {success, message, data} directly
            if isinstance(data, dict) and "success" in data:
                return data

            # Normalize if needed
            return {
                "success": True,
                "message": "ok",
                "data": data
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {str(e)}",
                "data": None
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "message": f"Request error: {str(e)}",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def search(self, user_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories for a user.

        Uses POST /memory/search endpoint (local API).

        Args:
            user_id: User identifier
            query: Search query
            limit: Max number of results (default: 5, max: 100)

        Returns:
            Response dict with structure:
            {
                "success": bool,
                "message": str,
                "data": Any
            }
        """
        url = f"{self.base_url}/memory/search"
        payload = {
            "query": query,
            "user_id": user_id,
            "limit": min(limit, 100)
        }

        try:
            response = self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )

            response.raise_for_status()
            data = response.json()

            # Local API returns {success, message, data} directly
            if isinstance(data, dict) and "success" in data:
                return data

            # Normalize if needed
            return {
                "success": True,
                "message": "ok",
                "data": data
            }

        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {str(e)}",
                "data": None
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "message": f"Request error: {str(e)}",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def add(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a new memory.

        Uses POST /memory/add endpoint (local API).

        Args:
            user_id: User identifier
            text: Memory text content
            metadata: Optional metadata dict

        Returns:
            Response dict
        """
        url = f"{self.base_url}/memory/add"
        payload = {
            "text": text,
            "user_id": user_id
        }
        if metadata:
            payload["metadata"] = metadata

        try:
            response = self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "success" in data:
                return data
            return {"success": True, "message": "ok", "data": data}

        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"HTTP {e.response.status_code}: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "data": None}

    def add_messages(self, user_id: str, messages: list, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add memories from conversation messages.

        Uses POST /memory/add-messages endpoint (local API).

        Args:
            user_id: User identifier
            messages: List of message dicts with 'role' and 'content'
            metadata: Optional metadata dict

        Returns:
            Response dict
        """
        url = f"{self.base_url}/memory/add-messages"
        payload = {
            "messages": messages,
            "user_id": user_id
        }
        if metadata:
            payload["metadata"] = metadata

        try:
            response = self.client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "success" in data:
                return data
            return {"success": True, "message": "ok", "data": data}

        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"HTTP {e.response.status_code}: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "data": None}

    def health_check(self) -> bool:
        """Check if mem0 server is healthy."""
        try:
            response = self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False


def get_mem0_client(base_url: Optional[str] = None, api_key: Optional[str] = None) -> Mem0Client:
    """
    Factory function to get Mem0 client instance.

    Args:
        base_url: Optional base URL override (default from config)
        api_key: Optional API key (not required for local setup)

    Returns:
        Mem0Client instance
    """
    from app.config import config

    base_url = base_url or config.MEM0_BASE_URL
    api_key = api_key or config.MEM0_API_KEY or None

    return Mem0Client(base_url=base_url, api_key=api_key)
