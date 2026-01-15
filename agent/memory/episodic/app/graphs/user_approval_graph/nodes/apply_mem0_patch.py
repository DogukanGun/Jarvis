"""
Apply Mem0 Patch Node

Writes approved memory to mem0 long-term storage.
"""

from typing import Dict, Any
import logging

from ..state import ApprovalState
from app.clients.mem0_client import get_mem0_client
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def apply_mem0_patch(state: ApprovalState) -> Dict[str, Any]:
    """
    Write approved memory to mem0.

    Uses the proposed_value (or edited_value if edited).
    Marks episode as promoted in SQLite.

    Args:
        state: Current graph state

    Returns:
        State updates with mem0 write result
    """
    proposal = state.get("proposal", {})
    episode_id = state.get("episode_id") or proposal.get("episode_id")
    user_id = state.get("user_id") or proposal.get("user_id")
    approval_status = state.get("approval_status")

    # Get the value to write
    if approval_status == "edited":
        value_to_write = state.get("edited_value") or proposal.get("proposed_value")
    else:
        value_to_write = proposal.get("proposed_value")

    if not value_to_write or not user_id:
        logger.error("Missing value or user_id for mem0 write")
        return {
            "mem0_write_success": False,
            "mem0_error": "Missing required data"
        }

    try:
        # Write to mem0
        mem0_client = get_mem0_client()

        result = mem0_client.add(
            user_id=user_id,
            text=value_to_write,
            metadata={
                "source": "episode_promotion",
                "episode_id": episode_id,
                "proposal_id": proposal.get("id"),
                "original_confidence": proposal.get("confidence")
            }
        )

        if not result.get("success"):
            error_msg = result.get("message", "Unknown error")
            logger.error(f"Mem0 write failed: {error_msg}")
            return {
                "mem0_write_success": False,
                "mem0_write_result": result,
                "mem0_error": error_msg
            }

        logger.info(f"Successfully wrote to mem0 for user {user_id}")

        # Mark episode as promoted in SQLite
        if episode_id:
            try:
                repo = get_episode_repository()
                repo.update_episode(episode_id, {
                    "promoted_to_mem0": True
                })
                logger.debug(f"Marked episode {episode_id} as promoted")
            except Exception as e:
                logger.warning(f"Failed to mark episode as promoted: {e}")

        return {
            "mem0_write_success": True,
            "mem0_write_result": result,
            "mem0_error": None
        }

    except Exception as e:
        error_msg = f"Mem0 write error: {str(e)}"
        logger.error(error_msg)
        return {
            "mem0_write_success": False,
            "mem0_write_result": None,
            "mem0_error": error_msg
        }
