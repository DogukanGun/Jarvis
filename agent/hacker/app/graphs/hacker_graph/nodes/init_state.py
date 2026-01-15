from typing import Dict, Any
from app.config import config
from app.graphs.hacker_graph.state import HackerGraphState


def init_state_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Initialize the graph state with default values.

    Sets up control variables like step_count, max_steps, and empty histories.
    """
    return {
        "step_count": 0,
        "max_steps": config.MAX_STEPS,
        "tool_history": [],
        "errors": [],
        "compiler_retry_count": 0,
        "last_tool_result": None,
        "validation_errors": [],
    }
