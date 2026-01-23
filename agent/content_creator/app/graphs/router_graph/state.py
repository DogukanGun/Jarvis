"""
State definition for Router Graph.

Tracks request validation and routing.
"""
from typing import TypedDict, Optional, List, Dict, Any


class RouterGraphState(TypedDict, total=False):
    """
    State for the Router Graph.

    Flow: validate_request -> route_request -> publish_routed
    """
    # ===== INPUT =====
    raw_message: Dict[str, Any]  # Raw Kafka message

    # ===== VALIDATE_REQUEST OUTPUT =====
    is_valid: bool
    validation_errors: List[str]
    request: Optional[Dict[str, Any]]  # Parsed and validated request

    # ===== ROUTE_REQUEST OUTPUT =====
    target_topic: Optional[str]  # Topic to route the request to
    routing_decision: str  # "route" or "reject"

    # ===== PUBLISH OUTPUT =====
    publish_success: bool
    result_published: bool  # Whether error result was published

    # ===== ERROR HANDLING =====
    job_id: Optional[str]  # Extracted job_id for error responses
    error: Optional[str]  # Any error message
