"""Node that validates the plan and resolves tool references."""

import logging
from typing import Any, Dict, List

from app.graphs.state import SwissArmyKnifeState
from app.tools.base import AuthLevel
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


async def select_tools(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Validate each planned step and build the resolved tool list."""

    steps: List[Dict[str, Any]] = state.get("plan", {}).get("steps", [])

    selected_tools: List[Dict[str, Any]] = []
    requires_confirmation = False
    confirmation_lines: List[str] = []

    for step in steps:
        tool_name = step.get("tool", "")
        tool = ToolRegistry.get(tool_name)

        # -- tool existence check --
        if tool is None:
            logger.warning("Tool '%s' from plan not found in registry, skipping.", tool_name)
            continue

        # -- availability check --
        if not tool.check_available():
            logger.warning("Tool '%s' is not available on this system, skipping.", tool_name)
            continue

        meta = tool.metadata()

        # -- required-params check --
        provided_params = step.get("params", {})
        required_params = [p.name for p in meta.parameters if p.required]
        missing = [p for p in required_params if p not in provided_params]
        if missing:
            logger.warning(
                "Tool '%s' is missing required params %s, skipping.",
                tool_name,
                missing,
            )
            continue

        # -- build resolved entry --
        selected_tools.append(
            {
                "tool": meta.name,
                "action": step.get("action", ""),
                "params": provided_params,
                "purpose": step.get("purpose", ""),
                "auth_level": meta.auth_level.value,
                "category": meta.category.value,
            }
        )

        # -- confirmation check --
        if meta.auth_level >= AuthLevel.high:
            requires_confirmation = True
            confirmation_lines.append(
                f"- {meta.display_name} ({meta.name}) "
                f"[auth_level={meta.auth_level.value}]: {step.get('purpose', 'N/A')}"
            )

    confirmation_prompt = ""
    if requires_confirmation:
        header = (
            "The following tools require elevated authorization and will be executed:\n"
        )
        confirmation_prompt = header + "\n".join(confirmation_lines)

    return {
        "selected_tools": selected_tools,
        "requires_confirmation": requires_confirmation,
        "confirmation_prompt": confirmation_prompt,
        "current_tool_index": 0,
        "tool_results": [],
        "tools_used": [],
        "findings": [],
    }
