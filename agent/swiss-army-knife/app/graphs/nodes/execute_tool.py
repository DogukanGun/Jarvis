"""Node that executes the current tool in the selected_tools list."""

import logging
import time
from typing import Any, Dict, List

from app.graphs.state import SwissArmyKnifeState
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


async def execute_tool(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Execute the tool at ``current_tool_index`` and record the result."""

    current_tool_index: int = state.get("current_tool_index", 0)
    selected_tools: List[Dict[str, Any]] = state.get("selected_tools", [])
    tool_results: List[Dict[str, Any]] = list(state.get("tool_results", []))
    tools_used: List[str] = list(state.get("tools_used", []))

    if current_tool_index >= len(selected_tools):
        logger.warning("current_tool_index (%d) out of range, nothing to execute.", current_tool_index)
        return {
            "tool_results": tool_results,
            "tools_used": tools_used,
            "current_tool_index": current_tool_index,
        }

    tool_spec = selected_tools[current_tool_index]
    tool_name = tool_spec["tool"]
    params = tool_spec.get("params", {})

    tool = ToolRegistry.get(tool_name)
    if tool is None:
        logger.error("Tool '%s' not found in registry during execution.", tool_name)
        result = ToolResult(
            tool_name=tool_name,
            success=False,
            error=f"Tool '{tool_name}' not found in registry.",
        )
        tool_results.append(result.model_dump())
        tools_used.append(tool_name)
        return {
            "tool_results": tool_results,
            "tools_used": tools_used,
            "current_tool_index": current_tool_index + 1,
        }

    logger.info("Executing tool '%s' (step %d/%d).", tool_name, current_tool_index + 1, len(selected_tools))

    try:
        start = time.monotonic()
        result = await tool.execute(params)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        # Patch duration if the tool did not set it
        if result.duration_ms == 0:
            result = result.model_copy(update={"duration_ms": elapsed_ms})
    except Exception as exc:
        logger.exception("Tool '%s' raised an exception.", tool_name)
        result = ToolResult(
            tool_name=tool_name,
            success=False,
            error=str(exc),
        )

    tool_results.append(result.model_dump())
    tools_used.append(tool_name)

    return {
        "tool_results": tool_results,
        "tools_used": tools_used,
        "current_tool_index": current_tool_index + 1,
    }
