"""Invoke the Swiss Army Knife security agent (fire-and-forget).

Starts the job via HTTP and returns immediately — no polling.
The result arrives later via Kafka → router Kafka consumer → WebSocket broadcast.
This mirrors how invoke_thinker works for the research pipeline.
"""

import logging
from typing import Any, Dict

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_swiss_knife(state: RouterGraphState) -> Dict[str, Any]:
    """Start async swiss-knife execution and return immediately.

    The result arrives later via Kafka → router consumer → WebSocket.
    generate_response already handles status="started" and produces the
    "Security scan started!" acknowledgment message.
    """
    from app.clients.swiss_knife_client import SwissKnifeClient

    message = state.get("message", "")
    user_id = state.get("user_id", "default")

    client = SwissKnifeClient()
    try:
        async_result = client.execute_async(message=message, user_id=user_id)
        job_id = async_result.get("job_id", "")

        if not job_id or async_result.get("error"):
            raise RuntimeError(async_result.get("error", "Failed to start async job"))

        logger.info("Swiss knife async job started: %s (fire-and-forget, result via Kafka)", job_id)
        client.close()

        tools_used = state.get("tools_used", [])
        tools_used.append("swiss-army-knife")
        tool_results = state.get("tool_results", {})
        tool_results["swiss_knife"] = {
            "status": "started",
            "job_id": job_id,
            "monitor_url": "http://localhost:3003",
        }
        return {"tool_results": tool_results, "tools_used": tools_used}

    except Exception as e:
        logger.error("Swiss knife invocation failed: %s", e)
        client.close()
        tools_used = state.get("tools_used", [])
        tools_used.append("swiss-army-knife")
        tool_results = state.get("tool_results", {})
        tool_results["swiss_knife"] = {"error": str(e)}
        return {"tool_results": tool_results, "tools_used": tools_used}
