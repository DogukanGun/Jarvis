"""HTTP client for the Legal RAG agent API."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import config

logger = logging.getLogger(__name__)


class LegalRagClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or config.LEGAL_RAG_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=120.0)

    def query(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        payload = {"user_id": user_id, "message": message, "stream": False}
        try:
            resp = self.client.post(f"{self.base_url}/api/query", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("LegalRagClient.query error: %s", e)
            return {"error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        self.client.close()
