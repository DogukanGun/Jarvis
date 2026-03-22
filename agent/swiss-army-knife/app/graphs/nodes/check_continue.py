"""Router and node for deciding whether to continue, replan, or finish."""

import logging
from typing import Any, Dict

from app.graphs.state import SwissArmyKnifeState

logger = logging.getLogger(__name__)


def continue_router(state: SwissArmyKnifeState) -> str:
    """Conditional edge router: decide the next step after interpretation.

    Returns:
        "next_tool"  -- more tools remain in the plan.
        "replan"     -- the LLM flagged that additional tools are needed.
        "done"       -- all tools have been executed; proceed to reporting.
    """
    current_index = state.get("current_tool_index", 0)
    selected_tools = state.get("selected_tools", [])

    if current_index < len(selected_tools):
        logger.info(
            "continue_router -> next_tool (index %d/%d)",
            current_index,
            len(selected_tools),
        )
        return "next_tool"

    if state.get("needs_more_tools", False):
        logger.info("continue_router -> replan")
        return "replan"

    logger.info("continue_router -> done")
    return "done"


async def check_continue(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Pass-through node placed before the conditional router.

    Currently keeps things simple by always returning
    ``needs_more_tools = False``.  In the future this node can call the
    LLM to decide whether the findings gathered so far are sufficient or
    whether replanning is warranted.
    """
    return {"needs_more_tools": False}
