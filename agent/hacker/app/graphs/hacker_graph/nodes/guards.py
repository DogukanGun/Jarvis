import logging
from typing import Literal

from app.graphs.hacker_graph.state import HackerGraphState

logger = logging.getLogger(__name__)


def guards_router(state: HackerGraphState) -> Literal["continue", "stop"]:
    """
    Guards check to determine if the loop should continue or stop.

    Checks:
    - step_count < max_steps (prevent infinite loops)
    - Optionally: detect repeated commands (not implemented yet)

    Returns:
        "continue" to loop back to planner
        "stop" to end the graph
    """
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 10)
    errors = state.get("errors", [])

    logger.info(f"Guards check: step {step_count}/{max_steps}")

    # Check step limit
    if step_count >= max_steps:
        logger.warning(f"Max steps ({max_steps}) reached, stopping")
        return "stop"

    # Check for too many errors
    if len(errors) >= 5:
        logger.warning(f"Too many errors ({len(errors)}), stopping")
        return "stop"

    # Check last tool result for critical failures
    last_result = state.get("last_tool_result")
    if last_result:
        # Stop if validation failed (no point continuing)
        if last_result.get("cmd") == "VALIDATION_FAILED":
            logger.warning("Validation failed, stopping")
            return "stop"

    logger.info("Guards passed, continuing")
    return "continue"
