"""
Dedupe Lookup Node

Checks if an episode with the same fingerprint already exists.
"""

from typing import Dict, Any
import logging

from ..state import MemoryWriteState
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def dedupe_lookup(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Look up existing episode by fingerprint.

    If found, we'll reinforce instead of insert.

    Args:
        state: Current graph state

    Returns:
        State updates with existing_episode_id, existing_episode, is_duplicate
    """
    user_id = state.get("user_id")
    fingerprint = state.get("fingerprint")

    if not user_id or not fingerprint:
        logger.warning("Missing user_id or fingerprint for dedupe lookup")
        return {
            "existing_episode_id": None,
            "existing_episode": None,
            "is_duplicate": False
        }

    try:
        repo = get_episode_repository()
        existing = repo.get_episode_by_fingerprint(user_id, fingerprint)

        from app.monitor import get_monitor
        monitor = get_monitor()

        if existing:
            logger.info(f"Found duplicate episode: {existing.id} (count={existing.reinforcement_count})")
            monitor.emit("episode_deduplicated", {
                "graph": "memory_write_graph",
                "node": "dedupe_lookup",
                "existing_episode_id": existing.id,
                "reinforcement_count": existing.reinforcement_count,
            })
            return {
                "existing_episode_id": existing.id,
                "existing_episode": existing.model_dump(),
                "is_duplicate": True
            }

        logger.debug("No duplicate found")
        return {
            "existing_episode_id": None,
            "existing_episode": None,
            "is_duplicate": False
        }

    except Exception as e:
        logger.error(f"Dedupe lookup error: {str(e)}")
        # On error, treat as not duplicate (will insert new)
        return {
            "existing_episode_id": None,
            "existing_episode": None,
            "is_duplicate": False
        }
