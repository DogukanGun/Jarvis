"""HTTP client for the Web Fetcher agent API."""

import httpx
import logging
from typing import Any, Dict, Optional

from app.config import config

logger = logging.getLogger(__name__)


class WebFetcherClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.WEB_FETCHER_BASE_URL).rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def fetch_page(self, url: str, max_chars: int = 50000) -> Dict[str, Any]:
        """Fetch a single page's content."""
        try:
            resp = self.client.post(
                f"{self.base_url}/page",
                json={"url": url, "max_chars": max_chars},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Web fetcher fetch_page error: {e}")
            return {"error": str(e)}

    def fetch_site_pages(self, url: str, max_pages: int = 50) -> Dict[str, Any]:
        """List discoverable URLs from a seed URL."""
        try:
            resp = self.client.post(
                f"{self.base_url}/site/pages",
                json={"url": url, "max_pages": max_pages},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Web fetcher fetch_site_pages error: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()
