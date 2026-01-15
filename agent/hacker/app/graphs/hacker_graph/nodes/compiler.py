import logging
from typing import Dict, Any, Literal

from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from app.clients.ollama_client import get_compiler_client
from app.graphs.hacker_graph.state import HackerGraphState
from app.config import config

logger = logging.getLogger(__name__)


@tool
def run_cli(cmd: str) -> str:
    """
    Execute a CLI command to gather information or perform an action.

    Args:
        cmd: The exact CLI command to execute (e.g., "ls -la", "find . -name '*.py'")

    Returns:
        Confirmation that the command will be executed.
    """
    return f"Command scheduled: {cmd}"


@tool
def finish(answer: str) -> str:
    """
    Complete the task and return the final answer to the user.

    Args:
        answer: The complete answer to the user's question based on command outputs.

    Returns:
        Confirmation that the task is finished.
    """
    return f"Task finished: {answer}"


COMPILER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a command compiler. You read the planner's decision and execute the appropriate action.

You have TWO tools:
1. run_cli(cmd) - Execute a CLI command
2. finish(answer) - Complete the task with a final answer

RULES:
- If the planner wants to run a command, call run_cli with the exact command
- If the planner is providing a final answer (not asking to run a command), call finish with that answer
- Extract the exact command or answer from the planner's text

Allowed CLI commands: {allowlist}

IMPORTANT: You MUST call exactly one tool. Either run_cli OR finish."""),
    ("human", "Planner decision: {input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def compiler_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Compiler Agent - Context-blind, with tool calling.

    Parses Planner's free text and calls either:
    - run_cli(cmd) -> execute a command
    - finish(answer) -> complete the task
    """
    logger.info("Compiler node executing...")

    decision_text = state.get("decision_text", "")
    validation_errors = state.get("validation_errors", [])
    retry_count = state.get("compiler_retry_count", 0)

    if not decision_text:
        logger.error("No decision text provided to compiler")
        return {
            "tool_request": None,
            "compiler_error": "No decision text",
            "compiler_action": "error",
        }

    # Add validation errors if retrying
    if validation_errors:
        decision_text = f"{decision_text}\n\nPrevious errors (fix these): {', '.join(validation_errors)}"

    try:
        llm = get_compiler_client()
        tools = [run_cli, finish]
        prompt = COMPILER_PROMPT.partial(allowlist=", ".join(config.COMMAND_ALLOWLIST))

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=1,
            return_intermediate_steps=True,
        )

        result = executor.invoke({"input": decision_text})

        # Check which tool was called
        intermediate_steps = result.get("intermediate_steps", [])
        for step in intermediate_steps:
            if len(step) >= 1:
                action = step[0]
                if hasattr(action, "tool"):
                    tool_name = action.tool
                    tool_input = action.tool_input

                    if tool_name == "finish":
                        answer = tool_input.get("answer", "") if isinstance(tool_input, dict) else str(tool_input)
                        logger.info(f"Compiler called finish: {answer[:100]}...")
                        return {
                            "compiler_action": "finish",
                            "final_answer": answer,
                            "tool_request": None,
                            "compiler_retry_count": retry_count + 1,
                        }

                    elif tool_name == "run_cli":
                        cmd = tool_input.get("cmd", "") if isinstance(tool_input, dict) else str(tool_input)
                        logger.info(f"Compiler called run_cli: {cmd}")
                        return {
                            "compiler_action": "run_cli",
                            "tool_request": {
                                "action": "CALL_TOOL",
                                "tool": "run_cli",
                                "args": {"cmd": cmd}
                            },
                            "compiler_retry_count": retry_count + 1,
                        }

        # No tool called - try to extract from output
        output = result.get("output", "")
        logger.warning(f"No tool called, output: {output[:100]}")

        # Fallback: assume it's a finish if no command keywords
        if any(kw in decision_text.lower() for kw in ["run ", "execute ", "command"]):
            # Try to extract command
            import re
            match = re.search(r'(?:run|execute)\s+(.+?)(?:\s+to|\s*$)', decision_text, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                return {
                    "compiler_action": "run_cli",
                    "tool_request": {"action": "CALL_TOOL", "tool": "run_cli", "args": {"cmd": cmd}},
                    "compiler_retry_count": retry_count + 1,
                }

        # Default to finish with the decision text as answer
        return {
            "compiler_action": "finish",
            "final_answer": decision_text,
            "tool_request": None,
            "compiler_retry_count": retry_count + 1,
        }

    except Exception as e:
        logger.error(f"Compiler error: {str(e)}")
        return {
            "compiler_action": "error",
            "compiler_error": str(e),
            "tool_request": None,
            "compiler_retry_count": retry_count + 1,
        }


def compiler_router(state: HackerGraphState) -> Literal["finish", "run_cli", "error"]:
    """Router to determine next step after compiler."""
    action = state.get("compiler_action", "error")
    return action
