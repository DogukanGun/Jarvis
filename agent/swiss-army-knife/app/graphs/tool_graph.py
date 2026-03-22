"""Main LangGraph wiring for the Swiss Army Knife agent."""

import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from app.graphs.state import SwissArmyKnifeState
from app.graphs.nodes import (
    plan_approach,
    select_tools,
    request_confirmation,
    execute_tool,
    interpret_output,
    check_continue,
    compile_report,
)
from app.graphs.nodes.check_continue import continue_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _confirmation_router(state: SwissArmyKnifeState) -> str:
    """Route after select_tools: skip confirmation when it is not required."""
    if state.get("requires_confirmation", False):
        return "needs_confirmation"
    return "skip_confirmation"


def create_tool_graph():
    """Build and compile the Swiss Army Knife LangGraph."""

    graph = StateGraph(SwissArmyKnifeState)

    # -- Register nodes ------------------------------------------------
    graph.add_node("plan_approach", plan_approach)
    graph.add_node("select_tools", select_tools)
    graph.add_node("request_confirmation", request_confirmation)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("interpret_output", interpret_output)
    graph.add_node("check_continue", check_continue)
    graph.add_node("compile_report", compile_report)

    # -- Wire edges ----------------------------------------------------
    # 1. Entry point
    graph.set_entry_point("plan_approach")

    # 2. plan_approach -> select_tools
    graph.add_edge("plan_approach", "select_tools")

    # 3. select_tools -> conditional: confirmation or straight to execution
    graph.add_conditional_edges(
        "select_tools",
        _confirmation_router,
        {
            "needs_confirmation": "request_confirmation",
            "skip_confirmation": "execute_tool",
        },
    )

    # 4. request_confirmation -> execute_tool
    graph.add_edge("request_confirmation", "execute_tool")

    # 5. execute_tool -> interpret_output
    graph.add_edge("execute_tool", "interpret_output")

    # 6. interpret_output -> check_continue
    graph.add_edge("interpret_output", "check_continue")

    # 7. check_continue -> conditional via continue_router
    graph.add_conditional_edges(
        "check_continue",
        continue_router,
        {
            "next_tool": "execute_tool",
            "replan": "plan_approach",
            "done": "compile_report",
        },
    )

    # 8. compile_report -> END
    graph.add_edge("compile_report", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

async def run_tool_graph(
    user_id: str,
    message: str,
    target_tools: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build initial state, invoke the compiled graph, and return final state.

    Args:
        user_id: Identifier for the requesting user/session.
        message: The natural-language task description.
        target_tools: Optional list of specific tool names to constrain the plan.
        parameters: Optional extra parameters forwarded into the state.

    Returns:
        The final graph state dictionary containing the report, findings, etc.
    """

    initial_state: Dict[str, Any] = {
        "user_id": user_id,
        "message": message,
        "plan": {},
        "selected_tools": [],
        "requires_confirmation": False,
        "confirmation_prompt": "",
        "confirmed": False,
        "current_tool_index": 0,
        "tool_results": [],
        "tools_used": [],
        "findings": [],
        "needs_more_tools": False,
        "report": {},
        "response": "",
        "error": None,
        "job_id": None,
    }

    if target_tools:
        initial_state["message"] += f"\n\n[Constrained tools: {', '.join(target_tools)}]"

    if parameters:
        initial_state.update(parameters)

    try:
        compiled_graph = create_tool_graph()
        final_state = await compiled_graph.ainvoke(initial_state)
        return final_state
    except Exception as exc:
        logger.exception("Tool graph execution failed: %s", exc)
        return {
            **initial_state,
            "error": str(exc),
            "response": f"Execution failed: {exc}",
        }
