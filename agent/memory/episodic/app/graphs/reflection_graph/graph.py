"""
Reflection Graph Definition

Wires together the periodic pattern extraction workflow.
"""

from langgraph.graph import StateGraph, END
import logging

from .state import ReflectionState
from .nodes import (
    load_recent_episodes,
    extract_patterns,
    resolve_conflicts,
    create_promotion_proposals,
)

logger = logging.getLogger(__name__)


def create_reflection_graph():
    """
    Create and configure the reflection_graph.

    Flow:
    1. load_recent_episodes - Get episodes from last N days
    2. extract_patterns - Find recurring patterns by fingerprint
    3. resolve_conflicts - Handle conflicts, user overrides win
    4. create_promotion_proposals - Create proposals for approval
    5. END

    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(ReflectionState)

    # Add nodes
    graph.add_node("load_recent_episodes", load_recent_episodes)
    graph.add_node("extract_patterns", extract_patterns)
    graph.add_node("resolve_conflicts", resolve_conflicts)
    graph.add_node("create_promotion_proposals", create_promotion_proposals)

    # Entry point
    graph.set_entry_point("load_recent_episodes")

    # Linear flow
    graph.add_edge("load_recent_episodes", "extract_patterns")
    graph.add_edge("extract_patterns", "resolve_conflicts")
    graph.add_edge("resolve_conflicts", "create_promotion_proposals")
    graph.add_edge("create_promotion_proposals", END)

    return graph.compile()


# Create default instance
reflection_graph = create_reflection_graph()


def run_reflection(user_id: str, lookback_days: int = None) -> ReflectionState:
    """
    Run the reflection graph for a user.

    Args:
        user_id: User to analyze
        lookback_days: Number of days to look back (default from config)

    Returns:
        Final state after reflection
    """
    from app.config import config

    initial_state: ReflectionState = {
        "user_id": user_id,
        "lookback_days": lookback_days or config.REFLECTION_LOOKBACK_DAYS,
        "errors": []
    }

    try:
        result = reflection_graph.invoke(initial_state)
        logger.info(f"Reflection completed for user {user_id}: {result.get('proposals_count', 0)} proposals")
        return result
    except Exception as e:
        logger.error(f"Reflection error: {str(e)}")
        initial_state["errors"] = [str(e)]
        initial_state["completed"] = True
        return initial_state
