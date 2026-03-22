"""Invoke the Thinker agent (fire-and-forget)."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_thinker(state: RouterGraphState) -> Dict[str, Any]:
    """Start a thinker research pipeline. Returns immediately."""
    from app.clients.thinker_client import ThinkerClient

    tool_args = state.get("tool_args", {})
    topic = tool_args.get("topic", state.get("message", ""))

    try:
        client = ThinkerClient()
        result = client.start_pipeline(topic=topic, agent="claude")
        client.close()

        if "error" in result:
            logger.error(f"Thinker invocation error: {result['error']}")
            return {
                "tool_results": {"thinker": {"error": result["error"]}},
                "tools_used": ["thinker"],
            }

        logger.info(f"Thinker pipeline started: {result}")
        return {
            "tool_results": {
                "thinker": {
                    "status": "started",
                    "topic": topic,
                    "pid": result.get("pid"),
                    "monitor_url": "http://localhost:3000",
                }
            },
            "tools_used": ["thinker"],
        }

    except Exception as e:
        logger.error(f"Thinker invocation failed: {e}")
        return {
            "tool_results": {"thinker": {"error": str(e)}},
            "tools_used": ["thinker"],
        }
