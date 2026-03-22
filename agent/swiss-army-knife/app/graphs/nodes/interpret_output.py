"""Node that interprets raw tool output using the LLM."""

import json
import logging
from typing import Any, Dict

from app.clients.llm_client import create_llm_client
from app.graphs.state import SwissArmyKnifeState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a security analyst interpreting tool output. Extract structured \
findings: hosts, services, vulnerabilities, credentials, or other relevant \
data. Classify severity as critical/high/medium/low/info.

Respond with a JSON object exactly matching this schema:

{
  "findings": [
    {
      "type": "host|service|vulnerability|credential|info",
      "severity": "critical|high|medium|low|info",
      "description": "Human-readable summary of the finding",
      "details": {}
    }
  ]
}

If there are no actionable findings, return {"findings": []}.
"""


async def interpret_output(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Interpret the latest tool result and extract structured findings."""

    tool_results = state.get("tool_results", [])
    if not tool_results:
        logger.warning("interpret_output called with no tool results")
        return {"findings": state.get("findings", [])}

    latest_result = tool_results[-1]

    # Get context from the corresponding plan step (previous index since
    # current_tool_index was already advanced after execution).
    selected_tools = state.get("selected_tools", [])
    executed_index = state.get("current_tool_index", 1) - 1
    step_context = (
        selected_tools[executed_index]
        if 0 <= executed_index < len(selected_tools)
        else {}
    )

    user_prompt = (
        f"Tool: {step_context.get('tool', 'unknown')}\n"
        f"Action: {step_context.get('action', 'unknown')}\n"
        f"Purpose: {step_context.get('purpose', 'N/A')}\n\n"
        f"Raw output:\n{latest_result.get('raw_output', '')}\n\n"
        f"Exit code: {latest_result.get('exit_code', 'N/A')}\n"
        f"Error: {latest_result.get('error', 'none')}\n\n"
        "Interpret this output and extract findings as JSON."
    )

    try:
        llm = create_llm_client()
        raw_response = await llm.generate(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
            json_mode=True,
        )
        parsed = json.loads(raw_response)
        new_findings = parsed.get("findings", [])
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("LLM interpretation failed: %s", exc)
        new_findings = [
            {
                "type": "info",
                "severity": "info",
                "description": "Automated interpretation failed; raw output preserved.",
                "details": {
                    "raw_output_preview": str(latest_result.get("raw_output", ""))[:500],
                    "error": str(exc),
                },
            }
        ]

    existing_findings = list(state.get("findings", []))
    existing_findings.extend(new_findings)

    return {"findings": existing_findings}
