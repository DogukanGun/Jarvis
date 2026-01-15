"""
Record Decision Node

Logs user decision for learning and analytics.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from ..state import ApprovalState
from app.storage import get_episode_repository, UserDecision

logger = logging.getLogger(__name__)


def record_decision(state: ApprovalState) -> Dict[str, Any]:
    """
    Record user's approval decision.

    Stores the decision for:
    - Analytics
    - Learning user preferences
    - Audit trail

    Args:
        state: Current graph state

    Returns:
        State updates with decision_id, decision_recorded
    """
    proposal = state.get("proposal", {})
    proposal_id = state.get("proposal_id") or proposal.get("id")
    user_id = state.get("user_id") or proposal.get("user_id")
    approval_status = state.get("approval_status", "rejected")
    edited_value = state.get("edited_value")
    user_response = state.get("user_response", {})

    if not proposal_id or not user_id:
        logger.warning("Missing proposal_id or user_id for decision recording")
        return {
            "decision_id": None,
            "decision_recorded": False
        }

    try:
        # Map approval status to decision
        if approval_status in ["approved", "edited"]:
            decision = "approve" if approval_status == "approved" else "edit"
        elif approval_status == "timeout":
            decision = "reject"  # Timeout counts as reject
        else:
            decision = "reject"

        # Create decision record
        user_decision = UserDecision(
            proposal_id=proposal_id,
            user_id=user_id,
            decision=decision,
            original_value=proposal.get("proposed_value", ""),
            final_value=edited_value if decision == "edit" else None,
            reason=user_response.get("reason"),
            created_at=datetime.utcnow()
        )

        # Store decision
        repo = get_episode_repository()
        decision_id = repo.insert_decision(user_decision)

        # Update proposal status
        repo.update_proposal_status(
            proposal_id=proposal_id,
            status=approval_status,
            user_response=edited_value
        )

        logger.info(f"Recorded decision {decision_id}: {decision} for proposal {proposal_id}")

        return {
            "decision_id": decision_id,
            "decision_recorded": True,
            "completed": True
        }

    except Exception as e:
        error_msg = f"Decision recording error: {str(e)}"
        logger.error(error_msg)
        return {
            "decision_id": None,
            "decision_recorded": False,
            "completed": True,  # Still mark as completed to end the graph
            "errors": state.get("errors", []) + [error_msg]
        }
