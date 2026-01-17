import logging
from typing import Dict, Any, Literal

from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from app.clients.ollama_client import get_compiler_client
from app.graphs.hacker_graph.state import HackerGraphState
from app.graphs.hacker_graph.tools import network_discovery_nmap
from app.config import config

logger = logging.getLogger(__name__)


@tool
def run_cli(cmd: str) -> str:
    """
    Execute a general CLI command to gather information or perform an action.

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


# Collect all available tools
AVAILABLE_TOOLS = [run_cli, finish, network_discovery_nmap]

# Tools that execute directly (return results immediately)
DIRECT_EXECUTION_TOOLS = {"network_discovery_nmap", "port_scan_netcat"}


COMPILER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a command compiler. You read the planner's decision and execute the appropriate action.

AVAILABLE TOOLS:
1. run_cli(cmd) - Execute a general CLI command
2. finish(answer) - Complete the task with a final answer
3. network_discovery_nmap(target, ports, ping_only, timing) - Run nmap scan on private/loopback networks
4. port_scan_netcat(target: str, ports: List[int], timeout_seconds: int = 2, tcp: bool = True) - Run nc to scan ports
RULES:
- If planner wants to run a general command, use run_cli
- If planner wants network scanning/discovery, use network_discovery_nmap
- If planner provides a final answer, use finish
- Extract exact parameters from the planner's text

For network_discovery_nmap:
- target: IP or CIDR (e.g., "192.168.1.0/24", "10.0.0.1")
- ports: port range (default "1-1024")
- ping_only: true for host discovery only
- timing: T0-T5 (default T3)

IMPORTANT: Call exactly ONE tool per decision."""),
    ("human", "Planner decision: {input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def compiler_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Compiler Agent - Context-blind, with tool calling.

    Parses Planner's free text and calls the appropriate tool:
    - run_cli(cmd) -> goes to validator/executor
    - finish(answer) -> ends the task
    - network_discovery_nmap(...) -> executes directly, returns to planner
    """
    logger.info("Compiler node executing...")

    decision_text = state.get("decision_text", "")
    validation_errors = state.get("validation_errors", [])
    retry_count = state.get("compiler_retry_count", 0)
    tool_history = state.get("tool_history", [])
    step_count = state.get("step_count", 0)

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

        agent = create_tool_calling_agent(llm, AVAILABLE_TOOLS, COMPILER_PROMPT)
        executor = AgentExecutor(
            agent=agent,
            tools=AVAILABLE_TOOLS,
            verbose=False,
            max_iterations=1,
            return_intermediate_steps=True,
        )

        result = executor.invoke({"input": decision_text})

        # Check which tool was called
        intermediate_steps = result.get("intermediate_steps", [])
        for step in intermediate_steps:
            if len(step) >= 2:
                action = step[0]
                tool_result = step[1]

                if hasattr(action, "tool"):
                    tool_name = action.tool
                    tool_input = action.tool_input

                    # Handle finish tool
                    if tool_name == "finish":
                        answer = tool_input.get("answer", "") if isinstance(tool_input, dict) else str(tool_input)
                        logger.info(f"Compiler called finish: {answer[:100]}...")
                        return {
                            "compiler_action": "finish",
                            "final_answer": answer,
                            "tool_request": None,
                            "compiler_retry_count": retry_count + 1,
                        }

                    # Handle run_cli (goes to validator/executor)
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

                    # Handle direct execution tools (execute and return to planner)
                    elif tool_name in DIRECT_EXECUTION_TOOLS:
                        logger.info(f"Compiler called {tool_name} with args: {tool_input}")
                        logger.info(f"Tool result: {str(tool_result)[:200]}...")

                        # Store result like executor does
                        tool_result_entry = {
                            "cmd": f"{tool_name}({tool_input})",
                            "exit_code": 0 if "error" not in str(tool_result).lower() else 1,
                            "stdout": str(tool_result),
                            "stderr": "",
                        }

                        return {
                            "compiler_action": "direct_tool",
                            "last_tool_result": tool_result_entry,
                            "tool_history": tool_history + [tool_result_entry],
                            "step_count": step_count + 1,
                            "compiler_retry_count": retry_count + 1,
                        }

        # No tool called - fallback logic
        output = result.get("output", "")
        logger.warning(f"No tool called, output: {output[:100]}")

        # Fallback: try to extract command
        if any(kw in decision_text.lower() for kw in ["run ", "execute ", "command"]):
            import re
            match = re.search(r'(?:run|execute)\s+(.+?)(?:\s+to|\s*$)', decision_text, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                return {
                    "compiler_action": "run_cli",
                    "tool_request": {"action": "CALL_TOOL", "tool": "run_cli", "args": {"cmd": cmd}},
                    "compiler_retry_count": retry_count + 1,
                }

        # Default to finish
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


def compiler_router(state: HackerGraphState) -> Literal["finish", "run_cli", "direct_tool", "error"]:
    """Router to determine next step after compiler."""
    action = state.get("compiler_action", "error")
    return action
