"""Invoke the Web Fetcher agent."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """Ensure URL has a scheme. Adds https:// to bare domains like www.certhub.de."""
    url = url.strip()
    if url and "://" not in url:
        url = "https://" + url
    return url


def invoke_web_fetcher(state: RouterGraphState) -> Dict[str, Any]:
    """Fetch web page content via the web fetcher agent."""
    import re
    from app.clients.web_fetcher_client import WebFetcherClient

    tool_args = state.get("tool_args", {})
    url = tool_args.get("url", "")

    if not url:
        # Try to extract URL from message — match both full URLs and bare domains (www.x.com)
        message = state.get("message", "")
        patterns = [
            r'https?://[^\s<>"\']+',                      # full URL
            r'(?<!\w)(?:www\.)[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s<>"\']*)?',  # www.domain.com
        ]
        for pattern in patterns:
            found = re.findall(pattern, message)
            if found:
                url = found[0]
                break

    if not url:
        return {
            "tool_results": {"web_fetcher": {"error": "No URL found in the request"}},
            "tools_used": ["web_fetcher"],
        }

    url = _normalize_url(url)

    try:
        client = WebFetcherClient()
        result = client.fetch_page(url=url)
        client.close()

        if "error" in result:
            return {
                "tool_results": {"web_fetcher": {"error": result["error"]}},
                "tools_used": ["web_fetcher"],
            }

        logger.info(f"Fetched page: {result.get('title', url)}")
        return {
            "tool_results": {
                "web_fetcher": {
                    "url": result.get("url", url),
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:5000],  # Limit for LLM context
                }
            },
            "tools_used": ["web_fetcher"],
        }

    except Exception as e:
        logger.error(f"Web fetch failed: {e}")
        return {
            "tool_results": {"web_fetcher": {"error": str(e)}},
            "tools_used": ["web_fetcher"],
        }
