"""Invoke the Swiss Army Knife security agent."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_swiss_knife(state: RouterGraphState) -> Dict[str, Any]:
    """Invoke the Swiss Army Knife agent for security/network tasks."""
    from app.clients.swiss_knife_client import SwissKnifeClient

    message = state.get("message", "")
    user_id = state.get("user_id", "default")
    tool_args = state.get("tool_args", {})

    client = SwissKnifeClient()
    try:
        result = client.execute(
            message=message,
            user_id=user_id,
            target_tools=tool_args.get("target_tools"),
            parameters=tool_args.get("parameters"),
        )
        client.close()

        tools_used = state.get("tools_used", [])
        tools_used.append("swiss-army-knife")

        tool_results = state.get("tool_results", {})
        tool_results["swiss_knife"] = result

        return {
            "tool_results": tool_results,
            "tools_used": tools_used,
        }
    except Exception as e:
        logger.error(f"Swiss knife invocation failed: {e}")
        client.close()
        return {
            "tool_results": state.get("tool_results", {}),
            "tools_used": state.get("tools_used", []),
        }
