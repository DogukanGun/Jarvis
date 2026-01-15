"""
Await User Approval Node

Sends Kafka request and waits for user response with timeout.
"""

from typing import Dict, Any
import logging

from ..state import ApprovalState
from app.clients.kafka_client import get_kafka_client

logger = logging.getLogger(__name__)


def await_user_approval(state: ApprovalState) -> Dict[str, Any]:
    """
    Send approval request via Kafka and wait for response.

    Timeout: 5 minutes (configurable via KAFKA_APPROVAL_TIMEOUT_SECONDS)

    Args:
        state: Current graph state

    Returns:
        State updates with approval status and response
    """
    from app.config import config

    proposal = state.get("proposal", {})
    proposal_id = state.get("proposal_id") or proposal.get("id")
    user_id = state.get("user_id") or proposal.get("user_id")

    if not proposal or not proposal_id:
        logger.error("Missing proposal for approval")
        return {
            "approval_status": "rejected",
            "user_response": None,
            "errors": state.get("errors", []) + ["Missing proposal"]
        }

    try:
        kafka_client = get_kafka_client()

        # Send approval request
        message_id = kafka_client.send_approval_request(
            proposal=proposal,
            timeout_seconds=config.KAFKA_APPROVAL_TIMEOUT_SECONDS
        )

        logger.info(f"Sent approval request {message_id} for proposal {proposal_id}")

        # Wait for response
        response = kafka_client.wait_for_response(
            message_id=message_id,
            timeout_seconds=config.KAFKA_APPROVAL_TIMEOUT_SECONDS
        )

        if response is None:
            # Timeout - auto-reject
            logger.warning(f"Approval timeout for proposal {proposal_id}")
            return {
                "kafka_message_id": message_id,
                "user_response": None,
                "approval_status": "timeout",
                "edited_value": None
            }

        # Process response
        decision = response.get("decision", "rejected")
        edited_value = response.get("edited_value")

        # Map decision to status
        if decision == "approved":
            status = "approved"
        elif decision == "edited":
            status = "edited"
        else:
            status = "rejected"

        logger.info(f"Received approval decision for {proposal_id}: {status}")

        return {
            "kafka_message_id": message_id,
            "user_response": response,
            "approval_status": status,
            "edited_value": edited_value
        }

    except Exception as e:
        error_msg = f"Approval request error: {str(e)}"
        logger.error(error_msg)
        return {
            "kafka_message_id": None,
            "user_response": None,
            "approval_status": "rejected",
            "edited_value": None,
            "errors": state.get("errors", []) + [error_msg]
        }
