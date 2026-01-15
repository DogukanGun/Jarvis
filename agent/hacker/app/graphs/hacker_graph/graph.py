import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.hacker_graph.state import HackerGraphState
from app.graphs.hacker_graph.nodes import (
    init_state_node,
    planner_node,
    compiler_node,
    compiler_router,
    validator_node,
    validator_router,
    executor_node,
    guards_router,
)

logger = logging.getLogger(__name__)


def create_hacker_graph() -> StateGraph:
    """
    Create and compile the Hacker Agent LangGraph.

    Flow:
        START → init_state → planner → compiler ──┬──(finish)──→ END
                                ↑                  │
                                │             (run_cli)
                                │                  ↓
                           guards ← executor ← validator
                                │                  ↑
                                └──(invalid)───────┘

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Hacker Agent graph...")

    # Create graph with state schema
    graph = StateGraph(HackerGraphState)

    # Add nodes
    graph.add_node("init_state", init_state_node)
    graph.add_node("planner", planner_node)
    graph.add_node("compiler", compiler_node)
    graph.add_node("validator", validator_node)
    graph.add_node("executor", executor_node)

    # Set entry point
    graph.set_entry_point("init_state")

    # Add edges
    # init_state → planner
    graph.add_edge("init_state", "planner")

    # planner → compiler (always goes to compiler now)
    graph.add_edge("planner", "compiler")

    # compiler → (finish → END) or (run_cli → validator) or (error → END)
    graph.add_conditional_edges(
        "compiler",
        compiler_router,
        {
            "finish": END,
            "run_cli": "validator",
            "error": END,
        }
    )

    # validator → (valid → executor) or (invalid → compiler for retry)
    graph.add_conditional_edges(
        "validator",
        validator_router,
        {
            "valid": "executor",
            "invalid": "compiler",
        }
    )

    # executor → guards
    graph.add_conditional_edges(
        "executor",
        guards_router,
        {
            "continue": "planner",  # Loop back to planner
            "stop": END,
        }
    )

    # Compile and return
    compiled = graph.compile()
    logger.info("Hacker Agent graph compiled successfully")

    return compiled


def run_hacker_graph(
    user_input: str,
    user_id: str = "default",
    max_steps: int = 10,
) -> Dict[str, Any]:
    """
    Run the Hacker Agent graph with the given input.

    Args:
        user_input: The user's request/question.
        user_id: User identifier for tracking.
        max_steps: Maximum number of tool execution steps.

    Returns:
        Final graph state including the answer.
    """
    logger.info(f"Running Hacker Agent for user {user_id}")

    # Create graph
    graph = create_hacker_graph()

    # Build initial state
    initial_state: HackerGraphState = {
        "user_id": user_id,
        "conversation": [{"role": "user", "content": user_input}],
        "max_steps": max_steps,
    }

    # Run graph
    try:
        result = graph.invoke(initial_state)
        logger.info("Hacker Agent completed successfully")
        return result
    except Exception as e:
        logger.error(f"Hacker Agent failed: {str(e)}")
        raise
