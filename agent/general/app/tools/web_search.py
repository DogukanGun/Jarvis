"""Web search tool wrapper."""

from langchain_core.tools import tool

from .base import call_tool_sync


@tool
def web_search_tool(query: str, count: int = 5, provider: str = "brave") -> str:
    """Search the web using Brave Search or Perplexity API.

    Args:
        query: The search query string.
        count: Number of results to return (1-10). Default: 5.
        provider: Search provider - "brave" or "perplexity". Default: "brave".

    Returns:
        Search results as JSON string with titles, URLs, and snippets.
    """
    result = call_tool_sync("web_search", {
        "query": query,
        "count": count,
        "provider": provider,
    })
    return str(result)
