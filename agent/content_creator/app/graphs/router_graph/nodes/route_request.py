"""
Route Request Node.

Determines the target topic based on task type.
"""
import logging
from typing import Dict, Any, Literal

from app.schemas.messages import RenderRequest, TaskType
from app.config import config
from app.graphs.router_graph.state import RouterGraphState

logger = logging.getLogger(__name__)


def route_request_node(state: RouterGraphState) -> Dict[str, Any]:
    """
    Determine the routing target for the request.

    Args:
        state: Current graph state with validated request

    Returns:
        State update with target_topic and routing_decision
    """
    if not state.get("is_valid"):
        logger.info("Request invalid, routing to reject")
        return {
            "target_topic": None,
            "routing_decision": "reject",
        }

    request_dict = state.get("request", {})

    try:
        # Reconstruct request object to get target topic
        request = RenderRequest(**request_dict)
        target_topic = request.get_target_topic()

        logger.info(
            f"Routing job {request.job_id} ({request.task.value}) to {target_topic}"
        )

        return {
            "target_topic": target_topic,
            "routing_decision": "route",
        }

    except Exception as e:
        logger.error(f"Routing error: {e}")
        return {
            "target_topic": None,
            "routing_decision": "reject",
            "error": str(e),
        }


def route_decision(state: RouterGraphState) -> Literal["publish", "error"]:
    """
    Conditional edge function to decide next node.

    Returns:
        "publish" if routing to worker topic
        "error" if publishing error result
    """
    decision = state.get("routing_decision", "reject")

    if decision == "route" and state.get("target_topic"):
        return "publish"
    else:
        return "error"
