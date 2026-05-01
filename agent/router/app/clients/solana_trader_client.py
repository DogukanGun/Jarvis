"""HTTP client for the Solana Trader (Node + SAK) service."""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import config

logger = logging.getLogger(__name__)


class SolanaTraderClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.SOLANA_TRADER_BASE_URL).rstrip("/")
        # Swaps and Pump.fun launches can take 30+ seconds end-to-end
        self.client = httpx.Client(timeout=120.0)

    def health_check(self) -> bool:
        try:
            r = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    def balance(self) -> Dict[str, Any]:
        try:
            r = self.client.get(f"{self.base_url}/api/balance")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Trader.balance error: %s", e)
            return {"error": str(e)}

    def execute_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = self.client.post(f"{self.base_url}/api/execute-intent", json=intent)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Trader.execute_intent error: %s", e)
            return {"error": str(e)}

    def swap(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = self.client.post(f"{self.base_url}/api/swap", json=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Trader.swap error: %s", e)
            return {"error": str(e)}

    def transfer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = self.client.post(f"{self.base_url}/api/transfer", json=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Trader.transfer error: %s", e)
            return {"error": str(e)}

    def price(self, token: str) -> Dict[str, Any]:
        try:
            r = self.client.post(f"{self.base_url}/api/price", json={"token": token})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def token_info(self, mint: str) -> Dict[str, Any]:
        try:
            r = self.client.post(f"{self.base_url}/api/token-info", json={"mint": mint})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def close(self) -> None:
        self.client.close()
