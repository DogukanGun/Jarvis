"""
Insert Episode Node

Creates a new episode in SQLite storage.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from ..state import MemoryWriteState
from app.storage import get_episode_repository, Episode

logger = logging.getLogger(__name__)


def insert_episode(state: MemoryWriteState) -> Dict[str, Any]:
    """
    Insert a new episode into storage.

    Creates episode with count=1, first_seen=now, last_seen=now.

    Args:
        state: Current graph state

    Returns:
        State updates with episode_id, episode, action_taken
    """
    user_id = state.get("user_id")
    fingerprint = state.get("fingerprint")
    candidates = state.get("redacted_candidates", state.get("episode_candidates", []))

    if not user_id or not fingerprint or not candidates:
        logger.error("Missing required data for episode insertion")
        return {
            "episode_id": None,
            "episode": None,
            "action_taken": "failed",
            "errors": state.get("errors", []) + ["Missing data for insertion"]
        }

    candidate = candidates[0]
    now = datetime.utcnow()

    try:
        # Create Episode model
        episode = Episode(
            user_id=user_id,
            fingerprint=fingerprint,
            text=candidate.get("text", ""),
            summary=candidate.get("summary"),
            episode_type=candidate.get("episode_type", "interaction"),
            task_type=candidate.get("task_type"),
            app=candidate.get("app"),
            entities=candidate.get("entities", []),
            first_seen=now,
            last_seen=now,
            importance_score=candidate.get("importance_score", 0.5),
            confidence=candidate.get("confidence", 1.0),
            reinforcement_count=1
        )

        # Insert into repository
        repo = get_episode_repository()
        episode_id = repo.insert_episode(episode)

        logger.info(f"Inserted new episode: {episode_id}")

        # Emit monitor event
        from app.monitor import get_monitor
        get_monitor().emit("episode_inserted", {
            "graph": "memory_write_graph",
            "node": "insert_episode",
            "episode_id": episode_id,
            "user_id": user_id,
            "episode_type": candidate.get("episode_type", "interaction"),
        })

        return {
            "episode_id": episode_id,
            "episode": episode.model_dump(),
            "action_taken": "inserted",
            "new_reinforcement_count": 1
        }

    except Exception as e:
        error_msg = f"Episode insertion error: {str(e)}"
        logger.error(error_msg)
        return {
            "episode_id": None,
            "episode": None,
            "action_taken": "failed",
            "errors": state.get("errors", []) + [error_msg]
        }
