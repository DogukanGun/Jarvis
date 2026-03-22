"""Node that handles the confirmation gate for HIGH/CRITICAL tools."""

import logging
from typing import Any, Dict, List

from app.graphs.state import SwissArmyKnifeState

logger = logging.getLogger(__name__)


async def request_confirmation(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Build a detailed confirmation prompt and return it in state.

    This node is only reached when ``requires_confirmation`` is ``True``.
    The graph will effectively pause here -- the server endpoint / job_store
    is responsible for waiting on the user's approval before resuming
    execution.
    """

    selected_tools: List[Dict[str, Any]] = state.get("selected_tools", [])

    lines: List[str] = [
        "=== Confirmation Required ===",
        "",
        "The execution plan includes tools that require explicit approval.",
        "Please review the details below and confirm to proceed.",
        "",
    ]

    for idx, tool_spec in enumerate(selected_tools, start=1):
        auth = tool_spec.get("auth_level", "unknown")
        lines.append(f"Step {idx}: {tool_spec['tool']}")
        lines.append(f"  Auth Level : {auth}")
        lines.append(f"  Action     : {tool_spec.get('action', 'N/A')}")
        lines.append(f"  Purpose    : {tool_spec.get('purpose', 'N/A')}")

        params = tool_spec.get("params", {})
        if params:
            lines.append("  Parameters :")
            for key, value in params.items():
                lines.append(f"    {key}: {value}")

        # Highlight risk for high/critical tools
        if auth in ("high", "critical"):
            lines.append(f"  ** Risk     : This tool has {auth.upper()} authorization level. **")

        lines.append("")

    lines.append("Reply with 'confirm' to proceed or 'cancel' to abort.")

    prompt_text = "\n".join(lines)
    logger.info("Confirmation requested for %d tool(s).", len(selected_tools))

    return {"confirmation_prompt": prompt_text}
