"""HTTP client for the Code Analyzer agent API."""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import config

logger = logging.getLogger(__name__)


class CodeAnalyzerClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.CODE_ANALYZER_BASE_URL).rstrip("/")
        # Long timeout — first-time indexing can take several minutes
        self.client = httpx.Client(timeout=360.0)

    def execute(
        self,
        message: str,
        user_id: str = "default",
        confirmed: bool = False,
        target_tools: Optional[list] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "message": message,
            "confirmed": confirmed,
        }
        if target_tools:
            payload["target_tools"] = target_tools
        if parameters:
            payload["parameters"] = parameters

        try:
            resp = self.client.post(f"{self.base_url}/api/execute", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("CodeAnalyzerClient.execute error: %s", e)
            return {"error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        self.client.close()
