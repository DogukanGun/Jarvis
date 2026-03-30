"""HTTP client for the Vision agent API."""

import httpx
import logging
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)


class VisionClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.VISION_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=15.0)

    def detect(self, image_b64: str, confidence: float = 0.4) -> dict:
        resp = self.client.post(
            f"{self.base_url}/api/detect",
            json={"image_b64": image_b64, "confidence_threshold": confidence},
        )
        resp.raise_for_status()
        return resp.json()

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()
