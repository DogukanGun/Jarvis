"""Node that uses the LLM to create an execution plan."""

import json
import logging
from typing import Any, Dict

from app.clients.llm_client import create_llm_client
from app.graphs.state import SwissArmyKnifeState
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert security and network tool orchestrator. Your job is to \
analyse a user request and produce a step-by-step execution plan using the \
available tools listed below.

Guidelines:
- Choose the most appropriate tools from the catalog for the task.
- Order steps logically: reconnaissance and information gathering before \
  active scanning, active scanning before exploitation, etc.
- Only include tools that appear in the catalog -- never invent tool names.
- Consider the capabilities each tool provides and match them to the task.
- Be concise in your rationale.

Respond with a JSON object exactly matching this schema (no extra keys):

{
  "rationale": "Brief explanation of why these tools in this order",
  "steps": [
    {
      "tool": "tool-name",
      "action": "specific action or subcommand",
      "params": {"key": "value"},
      "purpose": "what this step achieves"
    }
  ]
}
"""


async def plan_approach(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Build an LLM-generated execution plan for the user's request."""

    tool_catalog = ToolRegistry.get_llm_tool_descriptions()

    user_prompt = (
        f"User request:\n{state['message']}\n\n"
        f"Available tools:\n{tool_catalog}\n\n"
        "Produce the execution plan as JSON."
    )

    try:
        llm = create_llm_client()
        raw_response = await llm.generate(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
            json_mode=True,
        )
        plan = json.loads(raw_response)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("LLM planning failed: %s", exc)
        plan = {
            "rationale": "Automatic planning failed; falling back to a single-step plan.",
            "steps": [],
            "error": str(exc),
        }

    return {"plan": plan}
