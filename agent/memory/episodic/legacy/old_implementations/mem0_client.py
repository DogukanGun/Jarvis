"""
Mem0 API Client

Handles HTTP communication with mem0 memory service.
Provides factory pattern for easy mocking in tests.
"""

import httpx
from typing import Any, Dict, Optional
import os


class Mem0Client:
    """Client for mem0 API operations"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Mem0 client.

        Args:
            api_key: Mem0 API key (defaults to MEM0_API_KEY env var)
            base_url: Base URL for mem0 API (defaults to MEM0_BASE_URL env var or standard endpoint)
        """
        self.api_key = api_key or os.getenv("MEM0_API_KEY", "")
        self.base_url = base_url or os.getenv("MEM0_BASE_URL", "https://api.mem0.ai/v1")
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_all(self, user_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieve all memories for a user.

        Args:
            user_id: User identifier
            filters: Optional filters for memory retrieval

        Returns:
            Response dict with structure:
            {
                "success": bool,
                "message": str,
                "data": Any  # Could be list, dict, or other
            }

        Raises:
            Exception: On HTTP errors or connection failures
        """
        url = f"{self.base_url}/memories/"
        params = {"user_id": user_id}

        if filters:
            # Add filters as query params
            params.update(filters)

        try:
            response = self.client.get(
                url,
                params=params,
                headers=self._get_headers()
            )

            # Raise for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Normalize to expected structure
            if isinstance(data, dict):
                # If already has success/message/data structure, use it
                if "success" in data or "data" in data:
                    return {
                        "success": data.get("success", True),
                        "message": data.get("message", "ok"),
                        "data": data.get("data", data)
                    }
                # Otherwise wrap the dict as data
                return {
                    "success": True,
                    "message": "ok",
                    "data": data
                }
            elif isinstance(data, list):
                # If response is a list, wrap it
                return {
                    "success": True,
                    "message": "ok",
                    "data": data
                }
            else:
                # Other types
                return {
                    "success": True,
                    "message": "ok",
                    "data": data
                }

        except httpx.HTTPStatusError as e:
            # HTTP error (4xx, 5xx)
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {str(e)}",
                "data": None
            }
        except httpx.RequestError as e:
            # Connection error, timeout, etc.
            return {
                "success": False,
                "message": f"Request error: {str(e)}",
                "data": None
            }
        except Exception as e:
            # Other errors
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }


# Factory function for easy mocking in tests
_client_instance: Optional[Mem0Client] = None


def get_mem0_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> Mem0Client:
    """
    Factory function to get Mem0 client instance.

    This function can be easily monkeypatched in tests to return a fake client.

    Args:
        api_key: Optional API key override
        base_url: Optional base URL override

    Returns:
        Mem0Client instance
    """
    global _client_instance

    # For simplicity, create new instance each time
    # In production, you might want to cache/reuse
    return Mem0Client(api_key=api_key, base_url=base_url)


def normalize_mem0_items(data: Any) -> list:
    """
    Normalize mem0 response data into a stable list of dict items.

    The mem0 API returns data in various formats:
    - List of memory objects
    - Dict with memories under a key (memories/items/results/data)
    - Single memory object
    - None or empty

    Args:
        data: Raw data from mem0 API response

    Returns:
        List of memory dict objects (always returns a list, never None)
    """
    if data is None:
        return []

    if isinstance(data, list):
        return _normalize_list(data)

    if isinstance(data, dict):
        # Try common keys that might contain the memories list
        for key in ("memories", "items", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return _normalize_list(value)

        # Check if the dict itself is a single memory object
        # Look for common memory fields
        memory_indicators = ("text", "content", "memory", "message", "id")
        if any(k in data for k in memory_indicators):
            return [data]

        # Empty dict or unrecognized structure
        return []

    # Other types (str, int, etc.) - ignore
    return []


def _normalize_list(lst: list) -> list:
    """
    Normalize a list to contain only valid memory items.

    Args:
        lst: List of items (could be dicts, strings, or other)

    Returns:
        List of dict items
    """
    out = []
    for item in lst:
        if isinstance(item, dict):
            # Dict items are kept as-is
            out.append(item)
        elif isinstance(item, str) and item.strip():
            # String items are wrapped in a dict
            out.append({"text": item})
        # Ignore other types (None, int, etc.)

    return out


def safe_str(value: Any, max_length: int = 200) -> str:
    """
    Safely convert any value to string for logging.

    Args:
        value: Value to convert
        max_length: Maximum length of output string

    Returns:
        String representation, truncated if needed
    """
    try:
        s = str(value)
        if len(s) > max_length:
            return s[:max_length] + "..."
        return s
    except Exception:
        return "<unable to convert to string>"
