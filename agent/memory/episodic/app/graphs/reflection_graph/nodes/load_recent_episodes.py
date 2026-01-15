"""
Load Recent Episodes Node

Fetches episodes from the last N days for pattern analysis.
"""

from typing import Dict, Any
import logging

from ..state import ReflectionState
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def load_recent_episodes(state: ReflectionState) -> Dict[str, Any]:
    """
    Load recent episodes from SQLite for reflection.

    Args:
        state: Current graph state

    Returns:
        State updates with recent_episodes
    """
    from app.config import config

    user_id = state.get("user_id")
    lookback_days = state.get("lookback_days") or config.REFLECTION_LOOKBACK_DAYS

    if not user_id:
        logger.error("Missing user_id for reflection")
        return {
            "recent_episodes": [],
            "episode_count": 0,
            "errors": ["user_id is required"]
        }

    try:
        repo = get_episode_repository()

        # Get recent episodes (not promoted, not deleted)
        episodes = repo.get_recent_episodes(
            user_id=user_id,
            days=lookback_days,
            limit=200  # Process up to 200 episodes
        )

        # Filter out already promoted
        unpromoted = [
            ep.model_dump() for ep in episodes
            if not ep.promoted_to_mem0
        ]

        logger.info(f"Loaded {len(unpromoted)} recent episodes for user {user_id}")

        return {
            "recent_episodes": unpromoted,
            "episode_count": len(unpromoted)
        }

    except Exception as e:
        error_msg = f"Error loading episodes: {str(e)}"
        logger.error(error_msg)
        return {
            "recent_episodes": [],
            "episode_count": 0,
            "errors": state.get("errors", []) + [error_msg]
        }
