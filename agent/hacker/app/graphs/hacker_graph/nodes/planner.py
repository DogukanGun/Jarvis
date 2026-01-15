import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.ollama_client import get_planner_client
from app.graphs.hacker_graph.state import HackerGraphState

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a CLI planning assistant. You help users by running shell commands.

RULES:
1. If no command has been run yet: describe what command to run
   Example: "Run find . -name '*.py' to find Python files"

2. If a command result is shown: provide the ACTUAL DATA from the output
   - DO NOT say "task completed" or "success"
   - DO include the actual files, numbers, or content from the output
   Example: "The Python files are: ./main.py, ./app/config.py, ./app/utils.py"
   Example: "Found 12 Python files in the project"

IMPORTANT: Always include the real data from command outputs in your answer."""


def _build_input_text(state: HackerGraphState) -> str:
    """Build the input text for the Planner."""
    parts = []

    # Add user request
    conversation = state.get("conversation", [])
    for msg in conversation:
        if msg.get("role") == "user":
            parts.append(f"User request: {msg.get('content', '')}")

    # Add last tool result if available
    last_result = state.get("last_tool_result")
    if last_result:
        parts.append("\n--- Command Result ---")
        parts.append(f"Command: {last_result['cmd']}")
        parts.append(f"Exit Code: {last_result['exit_code']}")
        if last_result.get("stdout"):
            parts.append(f"Output:\n{last_result['stdout']}")
        if last_result.get("stderr"):
            parts.append(f"Errors:\n{last_result['stderr']}")
        parts.append("---")
        parts.append("\nNow provide the answer using the ACTUAL DATA from the output above.")

    return "\n".join(parts)


def planner_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Planner Agent - Context-aware, NO tool calling.

    Uses llama2-uncensored which doesn't support tools.
    Outputs free text that the Compiler will parse.
    """
    logger.info("Planner node executing...")

    try:
        # Build messages
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=_build_input_text(state))
        ]

        # Call LLM (no tools)
        llm = get_planner_client()
        response = llm.invoke(messages)

        decision_text = response.content.strip()
        logger.info(f"Planner decision: {decision_text[:150]}...")

        return {
            "decision_text": decision_text,
            "compiler_retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Planner node error: {str(e)}")
        errors = state.get("errors", [])
        errors.append(f"Planner error: {str(e)}")
        return {
            "decision_text": f"Error: {str(e)}",
            "errors": errors,
        }
