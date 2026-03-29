"""HTTP client for the Swiss Army Knife agent API."""

import httpx
import logging
from typing import Any, Dict, List, Optional

from app.config import config

logger = logging.getLogger(__name__)


class SwissKnifeClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.SWISS_KNIFE_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=120.0)

    def execute(
        self,
        message: str,
        user_id: str = "default",
        target_tools: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute security tools via the swiss-army-knife agent."""
        payload = {"user_id": user_id, "message": message, "confirmed": True}
        if target_tools:
            payload["target_tools"] = target_tools
        if parameters:
            payload["parameters"] = parameters

        try:
            resp = self.client.post(f"{self.base_url}/api/execute", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Swiss knife execute error: {e}")
            return {"error": str(e)}

    def execute_async(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        """Start async execution."""
        try:
            resp = self.client.post(
                f"{self.base_url}/api/execute/async",
                json={"user_id": user_id, "message": message, "confirmed": True},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def confirm(self, job_id: str, confirmed: bool = True) -> Dict[str, Any]:
        """Confirm or deny HIGH/CRITICAL tool execution."""
        try:
            resp = self.client.post(
                f"{self.base_url}/api/execute/confirm/{job_id}",
                json={"confirmed": confirmed},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def job_status(self, job_id: str) -> Dict[str, Any]:
        try:
            resp = self.client.get(f"{self.base_url}/api/jobs/{job_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def list_tools(self) -> Dict[str, Any]:
        try:
            resp = self.client.get(f"{self.base_url}/api/tools")
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
