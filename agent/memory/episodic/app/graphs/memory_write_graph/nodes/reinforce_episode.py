"""
Reinforce Episode Node

Increments count and updates last_seen for existing episode.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from ..state import MemoryWriteState
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def reinforce_episode(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Reinforce an existing episode.

    Increments reinforcement_count and updates last_seen.

    Args:
        state: Current graph state

    Returns:
        State updates with episode_id, episode, action_taken, new_reinforcement_count
    """
    existing_episode_id = state.get("existing_episode_id")
    existing_episode = state.get("existing_episode")

    if not existing_episode_id:
        logger.error("No existing episode to reinforce")
        return {
            "episode_id": None,
            "episode": None,
            "action_taken": "failed",
            "errors": state.get("errors", []) + ["No existing episode to reinforce"]
        }

    try:
        repo = get_episode_repository()

        # Reinforce the episode
        success = repo.reinforce_episode(existing_episode_id)

        if not success:
            logger.warning(f"Failed to reinforce episode: {existing_episode_id}")
            return {
                "episode_id": existing_episode_id,
                "episode": existing_episode,
                "action_taken": "failed",
                "errors": state.get("errors", []) + ["Reinforce operation failed"]
            }

        # Get updated episode
        updated = repo.get_episode_by_id(existing_episode_id)
        new_count = updated.reinforcement_count if updated else (existing_episode.get("reinforcement_count", 1) + 1)

        logger.info(f"Reinforced episode: {existing_episode_id} (new count={new_count})")

        return {
            "episode_id": existing_episode_id,
            "episode": updated.model_dump() if updated else existing_episode,
            "action_taken": "reinforced",
            "new_reinforcement_count": new_count
        }

    except Exception as e:
        error_msg = f"Reinforce error: {str(e)}"
        logger.error(error_msg)
        return {
            "episode_id": existing_episode_id,
            "episode": existing_episode,
            "action_taken": "failed",
            "errors": state.get("errors", []) + [error_msg]
        }
