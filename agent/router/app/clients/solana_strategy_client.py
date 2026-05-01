"""HTTP client for the Solana Strategy (Python) service."""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import config

logger = logging.getLogger(__name__)


class SolanaStrategyClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.SOLANA_STRATEGY_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=180.0)

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
            r = self.client.post(f"{self.base_url}/api/execute", json=payload)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Strategy.execute error: %s", e)
            return {"error": str(e)}

    def health_check(self) -> bool:
        try:
            r = self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        self.client.close()
