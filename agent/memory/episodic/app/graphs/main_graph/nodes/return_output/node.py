"""
Return Output Node for MainGraph
Node 8: return_output

Maps internal LLM output to stable response payload.
"""

from typing import Dict, Any
from app.shared.types import MainGraphState


def return_output(state: MainGraphState) -> Dict[str, Any]:
    """
    Map llm_output to response_payload.

    Args:
        state: Current graph state (must contain llm_output)

    Returns:
        State updates with response_payload
    """
    llm_output = state.get("llm_output")
    task_type = state.get("task_type", "unknown")
    app = state.get("app")

    # Extract answer from llm_output
    if isinstance(llm_output, str):
        answer = llm_output
    elif isinstance(llm_output, dict):
        # If dict, try to extract answer key
        answer = llm_output.get("answer", llm_output.get("response", str(llm_output)))
    else:
        # Fallback: stringify safely
        try:
            answer = str(llm_output) if llm_output is not None else "No response"
        except Exception:
            answer = "Error formatting response"

    # Build response payload
    response_payload = {
        "answer": answer,
        "metadata": {
            "task_type": task_type,
            "app": app
        }
    }

    return {
        "response_payload": response_payload
    }
