"""
User Approval Graph State Definition

State schema for the approval workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal


class ApprovalState(TypedDict, total=False):
    """
    State for user_approval_graph.

    Tracks the approval process from request to decision.
    """

    # =========================================================================
    # Input (promotion proposal)
    # =========================================================================
    proposal: Dict[str, Any]
    proposal_id: str
    episode_id: str
    user_id: str

    # =========================================================================
    # await_user_approval
    # =========================================================================
    kafka_message_id: Optional[str]
    user_response: Optional[Dict[str, Any]]
    approval_status: Literal["pending", "approved", "rejected", "edited", "timeout"]
    edited_value: Optional[str]

    # =========================================================================
    # apply_mem0_patch
    # =========================================================================
    mem0_write_success: bool
    mem0_write_result: Optional[Dict[str, Any]]
    mem0_error: Optional[str]

    # =========================================================================
    # record_decision
    # =========================================================================
    decision_id: Optional[str]
    decision_recorded: bool

    # =========================================================================
    # Status
    # =========================================================================
    completed: bool
    errors: List[str]
