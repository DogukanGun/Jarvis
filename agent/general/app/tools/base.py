"""Base HTTP tool client for calling the tool server."""

import httpx
from typing import Any

from ..config import get_config


async def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the HTTP tool server."""
    config = get_config()
    url = f"{config.tool_server_url}/tools/{tool_name}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json={"args": args})
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise Exception(data.get("error", "Unknown error"))

        return data.get("result", {})


def call_tool_sync(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the HTTP tool server (synchronous)."""
    config = get_config()
    url = f"{config.tool_server_url}/tools/{tool_name}"

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json={"args": args})
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise Exception(data.get("error", "Unknown error"))

        return data.get("result", {})
