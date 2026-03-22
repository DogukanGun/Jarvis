"""
Apply Long-Term Memory Patch Node

Writes approved memory to long-term storage (Supermemory or Mem0).
"""

from typing import Dict, Any
import logging

from ..state import ApprovalState
from app.clients.long_term_client import get_long_term_client
from app.storage import get_episode_repository

logger = logging.getLogger(__name__)


def apply_mem0_patch(state: ApprovalState) -> Dict[str, Any]:
    """
    Write approved memory to long-term storage.

    Uses the proposed_value (or edited_value if edited).
    Marks episode as promoted in SQLite.

    Args:
        state: Current graph state

    Returns:
        State updates with write result
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
        logger.error("Missing value or user_id for long-term memory write")
        return {
            "mem0_write_success": False,
            "mem0_error": "Missing required data"
        }

    try:
        # Write to long-term memory (Supermemory or Mem0)
        lt_client = get_long_term_client()

        result = lt_client.add(
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
            logger.error(f"Long-term memory write failed: {error_msg}")
            return {
                "mem0_write_success": False,
                "mem0_write_result": result,
                "mem0_error": error_msg
            }

        logger.info(f"Successfully wrote to long-term memory for user {user_id}")

        # Mark episode as promoted in SQLite
        if episode_id:
            try:
                repo = get_episode_repository()
                update_fields = {"promoted_to_mem0": True}

                # Store Supermemory external ID if available
                result_data = result.get("data", {})
                if result_data and result_data.get("id"):
                    update_fields["supermemory_id"] = result_data["id"]

                repo.update_episode(episode_id, update_fields)
                logger.debug(f"Marked episode {episode_id} as promoted")
            except Exception as e:
                logger.warning(f"Failed to mark episode as promoted: {e}")

        return {
            "mem0_write_success": True,
            "mem0_write_result": result,
            "mem0_error": None
        }

    except Exception as e:
        error_msg = f"Long-term memory write error: {str(e)}"
        logger.error(error_msg)
        return {
            "mem0_write_success": False,
            "mem0_write_result": None,
            "mem0_error": error_msg
        }
