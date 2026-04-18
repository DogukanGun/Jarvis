"""Retrieve relevant memory context before processing."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def retrieve_memory(state: RouterGraphState) -> Dict[str, Any]:
    """Fetch relevant episodes and context from the memory system.

    Short-circuits if memory was already retrieved during the server's
    pre-classify phase — avoids a redundant HTTP round-trip.
    """
    from app.clients.memory_client import MemoryClient

    # Already populated by the classify phase in server.py — skip.
    if state.get("memory_episodes") is not None:
        logger.info("Memory already retrieved in classify phase, skipping")
        return {}

    user_id = state.get("user_id", "default")
    message = state.get("message", "")

    try:
        client = MemoryClient()
        result = client.query(user_id=user_id, prompt=message)
        client.close()

        episodes = result.get("episodes", [])
        logger.info(f"Retrieved {len(episodes)} memory episodes for user {user_id}")

        return {
            "memory_context": result,
            "memory_episodes": episodes,
        }

    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")
        return {
            "memory_context": {},
            "memory_episodes": [],
        }
