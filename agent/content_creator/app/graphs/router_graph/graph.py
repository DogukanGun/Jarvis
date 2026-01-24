"""
Router Graph.

Routes incoming render requests to appropriate worker topics.

Flow:
    START -> validate_request -> route_request --(route)--> publish_routed -> END
                                       |
                                    (reject)
                                       v
                                 publish_error -> END
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.router_graph.state import RouterGraphState
from app.graphs.router_graph.nodes import (
    validate_request_node,
    route_request_node,
    route_decision,
    publish_routed_node,
    publish_error_node,
)

logger = logging.getLogger(__name__)


def create_router_graph() -> StateGraph:
    """
    Create and compile the Router Graph.

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Router graph...")

    # Create graph with state schema
    graph = StateGraph(RouterGraphState)

    # Add nodes
    graph.add_node("validate_request", validate_request_node)
    graph.add_node("route_request", route_request_node)
    graph.add_node("publish_routed", publish_routed_node)
    graph.add_node("publish_error", publish_error_node)

    # Set entry point
    graph.set_entry_point("validate_request")

    # Add edges
    graph.add_edge("validate_request", "route_request")

    # Conditional routing based on validation
    graph.add_conditional_edges(
        "route_request",
        route_decision,
        {
            "publish": "publish_routed",
            "error": "publish_error",
        }
    )

    # Both publish nodes go to END
    graph.add_edge("publish_routed", END)
    graph.add_edge("publish_error", END)

    # Compile and return
    compiled = graph.compile()
    logger.info("Router graph compiled successfully")

    return compiled


def run_router_graph(raw_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Router Graph with the given message.

    Args:
        raw_message: Raw Kafka message dict

    Returns:
        Final graph state
    """
    logger.info(f"Processing message: {raw_message.get('job_id', 'unknown')}")

    # Create graph
    graph = create_router_graph()

    # Build initial state
    initial_state: RouterGraphState = {
        "raw_message": raw_message,
    }

    # Run graph
    try:
        result = graph.invoke(initial_state)
        logger.info(f"Router graph completed for job {result.get('job_id', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"Router graph failed: {str(e)}")
        raise
