"""Invoke the Code Analyzer agent synchronously and return the result."""

import logging
from typing import Any, Dict

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_code_analyzer(state: RouterGraphState) -> Dict[str, Any]:
    from app.clients.code_analyzer_client import CodeAnalyzerClient

    message = state.get("message", "")
    tool_args = state.get("tool_args", {})
    user_id = state.get("user_id", "default")

    # Pass repo context extracted by classify_intent (if any) as parameters
    parameters: Dict[str, Any] = {}
    if tool_args.get("repo_url"):
        parameters["repo_url"] = tool_args["repo_url"]
    if tool_args.get("repo_path"):
        parameters["repo_path"] = tool_args["repo_path"]

    # Embed repo context directly into the message so the agent can extract it
    full_message = message
    if parameters:
        import json
        full_message += f"\n\n[Context: {json.dumps(parameters)}]"

    client = CodeAnalyzerClient()
    try:
        result = client.execute(message=full_message, user_id=user_id)
        client.close()

        if result.get("error"):
            raise RuntimeError(result["error"])

        tools_used = list(state.get("tools_used", []))
        tools_used.append("code-analyzer")
        tool_results = dict(state.get("tool_results", {}))
        tool_results["code_analyzer"] = {
            "response": result.get("response", ""),
            "tools_used": result.get("tools_used", []),
            "findings": result.get("findings", []),
            "report": result.get("report", {}),
        }
        return {
            "tool_results": tool_results,
            "tools_used": tools_used,
            "response": result.get("response", ""),
            "findings": result.get("findings", []),
            "report": result.get("report", {}),
        }

    except Exception as e:
        logger.error("Code analyzer invocation failed: %s", e)
        client.close()
        tools_used = list(state.get("tools_used", []))
        tools_used.append("code-analyzer")
        tool_results = dict(state.get("tool_results", {}))
        tool_results["code_analyzer"] = {"error": str(e)}
        return {"tool_results": tool_results, "tools_used": tools_used}
