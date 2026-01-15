"""
User Approval Graph Definition

Wires together the approval workflow nodes.
"""

from langgraph.graph import StateGraph, END
import logging

from .state import ApprovalState
from .nodes import (
    await_user_approval,
    apply_mem0_patch,
    record_decision,
)

logger = logging.getLogger(__name__)


def create_user_approval_graph():
    """
    Create and configure the user_approval_graph.

    Flow:
    1. await_user_approval - Send Kafka, wait for response
    2. If approved/edited -> apply_mem0_patch -> record_decision
    3. If rejected/timeout -> record_decision
    4. END

    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(ApprovalState)

    # Add nodes
    graph.add_node("await_user_approval", await_user_approval)
    graph.add_node("apply_mem0_patch", apply_mem0_patch)
    graph.add_node("record_decision", record_decision)

    # Entry point
    graph.set_entry_point("await_user_approval")

    # Conditional routing based on approval status
    def approval_router(state: ApprovalState) -> str:
        status = state.get("approval_status", "rejected")
        if status in ["approved", "edited"]:
            return "approved"
        else:
            return "rejected"

    graph.add_conditional_edges(
        "await_user_approval",
        approval_router,
        {
            "approved": "apply_mem0_patch",
            "rejected": "record_decision"
        }
    )

    # apply_mem0_patch -> record_decision
    graph.add_edge("apply_mem0_patch", "record_decision")

    # record_decision -> END
    graph.add_edge("record_decision", END)

    return graph.compile()


# Create default instance
user_approval_graph = create_user_approval_graph()


def run_approval_flow(proposal: dict) -> ApprovalState:
    """
    Run the approval flow for a promotion proposal.

    Args:
        proposal: Promotion proposal dict

    Returns:
        Final state after approval flow
    """
    initial_state: ApprovalState = {
        "proposal": proposal,
        "proposal_id": proposal.get("id"),
        "episode_id": proposal.get("episode_id"),
        "user_id": proposal.get("user_id"),
        "errors": []
    }

    try:
        result = user_approval_graph.invoke(initial_state)
        logger.info(f"Approval flow completed for proposal {proposal.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Approval flow error: {str(e)}")
        initial_state["errors"] = [str(e)]
        initial_state["completed"] = True
        return initial_state


def run_approval(
    proposal_id: str,
    decision: str,
    edited_value: str = None,
    reason: str = None
) -> ApprovalState:
    """
    Process an approval decision for a proposal.

    This is called when a Kafka response is received.

    Args:
        proposal_id: The proposal ID
        decision: User decision (approved, rejected, edited, timeout)
        edited_value: Optional edited value (if decision is 'edited')
        reason: Optional reason for decision

    Returns:
        Final state after processing
    """
    from app.storage import get_episode_repository

    try:
        # Get the proposal from storage
        repo = get_episode_repository()
        proposal = repo.get_proposal(proposal_id)

        if not proposal:
            return {
                "proposal_id": proposal_id,
                "completed": True,
                "applied": False,
                "errors": [f"Proposal not found: {proposal_id}"]
            }

        # Build initial state with pre-filled decision
        initial_state: ApprovalState = {
            "proposal": proposal.model_dump(),
            "proposal_id": proposal_id,
            "episode_id": proposal.episode_id,
            "user_id": proposal.user_id,
            "approval_status": decision,
            "edited_value": edited_value,
            "rejection_reason": reason,
            "errors": []
        }

        # Skip await_user_approval since we already have the decision
        # Go directly to apply_mem0_patch or record_decision based on status
        if decision in ["approved", "edited"]:
            from .nodes import apply_mem0_patch, record_decision

            # Apply mem0 patch
            state_after_patch = apply_mem0_patch(initial_state)
            initial_state.update(state_after_patch)

            # Record decision
            state_after_record = record_decision(initial_state)
            initial_state.update(state_after_record)
        else:
            from .nodes import record_decision

            # Just record decision
            state_after_record = record_decision(initial_state)
            initial_state.update(state_after_record)

        initial_state["completed"] = True
        logger.info(f"Processed approval decision for {proposal_id}: {decision}")
        return initial_state

    except Exception as e:
        logger.error(f"Error processing approval: {str(e)}")
        return {
            "proposal_id": proposal_id,
            "completed": True,
            "applied": False,
            "errors": [str(e)]
        }
