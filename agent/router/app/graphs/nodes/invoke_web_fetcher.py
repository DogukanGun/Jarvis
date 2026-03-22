"""Invoke the Web Fetcher agent."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_web_fetcher(state: RouterGraphState) -> Dict[str, Any]:
    """Fetch web page content via the web fetcher agent."""
    from app.clients.web_fetcher_client import WebFetcherClient

    tool_args = state.get("tool_args", {})
    url = tool_args.get("url", "")

    if not url:
        # Try to extract URL from message
        message = state.get("message", "")
        import re
        urls = re.findall(r'https?://[^\s<>"]+', message)
        url = urls[0] if urls else ""

    if not url:
        return {
            "tool_results": {"web_fetcher": {"error": "No URL provided"}},
            "tools_used": ["web_fetcher"],
        }

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
