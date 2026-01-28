"""Browser automation tool wrapper."""

from langchain_core.tools import tool

from .base import call_tool_sync


@tool
def browser_tool(
    action: str,
    url: str | None = None,
    page_id: str | None = None,
    selector: str | None = None,
    text: str | None = None,
    full_page: bool = False,
) -> str:
    """Control a headless browser for web automation.

    Args:
        action: Browser action - "status", "tabs", "open", "close", "navigate", "snapshot", "screenshot", "click", "type"
        url: URL to navigate to (for open/navigate actions)
        page_id: Page ID to operate on (required for most actions after open)
        selector: CSS selector for click/type actions
        text: Text to type (for type action)
        full_page: Take full page screenshot (for screenshot action)

    Returns:
        Result of the browser action as JSON string.

    Examples:
        - browser_tool(action="open", url="https://example.com") -> Opens page, returns pageId
        - browser_tool(action="snapshot", page_id="page_1") -> Gets page content
        - browser_tool(action="click", page_id="page_1", selector="button.submit")
        - browser_tool(action="type", page_id="page_1", selector="input#search", text="query")
    """
    args = {"action": action}
    if url:
        args["url"] = url
    if page_id:
        args["pageId"] = page_id
    if selector:
        args["selector"] = selector
    if text:
        args["text"] = text
    if full_page:
        args["fullPage"] = full_page

    result = call_tool_sync("browser", args)
    return str(result)
