"""HTTP client for the Memory agent API."""

import httpx
import logging
from typing import Any, Dict, Optional

from app.config import config

logger = logging.getLogger(__name__)


class MemoryClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.MEMORY_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def query(self, user_id: str, prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Query the memory system. Returns retrieved episodes and LLM output.
        Calls the /api/query endpoint on the memory monitor.
        """
        try:
            resp = self.client.post(
                f"{self.base_url}/api/query",
                json={
                    "user_id": user_id,
                    "prompt": prompt,
                    "context": context or {},
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Memory query error: {e}")
            return {"episodes": [], "error": str(e)}

    def get_episodes(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get recent episodes for a user."""
        try:
            resp = self.client.get(
                f"{self.base_url}/api/episodes",
                params={"user_id": user_id, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Memory get_episodes error: {e}")
            return {"episodes": [], "error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()
