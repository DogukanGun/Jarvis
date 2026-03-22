"""Retrieve relevant memory context before processing."""

from typing import Any, Dict
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def retrieve_memory(state: RouterGraphState) -> Dict[str, Any]:
    """Fetch relevant episodes and context from the memory system."""
    from app.clients.memory_client import MemoryClient

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
