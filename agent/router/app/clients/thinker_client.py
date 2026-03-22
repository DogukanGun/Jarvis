"""HTTP client for the Thinker agent API."""

import httpx
import logging
from typing import Any, Dict, Optional

from app.config import config

logger = logging.getLogger(__name__)


class ThinkerClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.THINKER_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def start_pipeline(
        self,
        topic: str,
        agent: str = "claude",
        max_problems: Optional[int] = None,
        max_accepted: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Start a thinker pipeline run (fire-and-forget)."""
        payload = {"topic": topic, "agent": agent}
        if max_problems is not None:
            payload["max_problems"] = max_problems
        if max_accepted is not None:
            payload["max_accepted"] = max_accepted

        try:
            resp = self.client.post(f"{self.base_url}/api/pipeline/start", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Thinker start_pipeline error: {e}")
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Check if the thinker pipeline is running."""
        try:
            resp = self.client.get(f"{self.base_url}/api/pipeline/status")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"running": False, "error": str(e)}

    def get_state(self) -> Dict[str, Any]:
        """Get the current pipeline state snapshot."""
        try:
            resp = self.client.get(f"{self.base_url}/api/state")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()
