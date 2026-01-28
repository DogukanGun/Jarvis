"""Web fetch tool wrapper."""

from langchain_core.tools import tool

from .base import call_tool_sync


@tool
def web_fetch_tool(url: str, extract_mode: str = "markdown", max_chars: int = 50000) -> str:
    """Fetch and extract readable content from a URL.

    Args:
        url: The HTTP or HTTPS URL to fetch.
        extract_mode: Extraction mode - "markdown" or "text". Default: "markdown".
        max_chars: Maximum characters to return. Default: 50000.

    Returns:
        Extracted content from the URL as markdown or text.
    """
    result = call_tool_sync("web_fetch", {
        "url": url,
        "extractMode": extract_mode,
        "maxChars": max_chars,
    })

    # Return the text content if available
    if isinstance(result, dict) and "text" in result:
        return result["text"]
    return str(result)
