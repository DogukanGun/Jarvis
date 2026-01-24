import logging
import subprocess
from typing import Dict, Any

from app.graphs.hacker_graph.state import HackerGraphState, ToolResult

logger = logging.getLogger(__name__)

# Maximum output size to prevent memory issues
MAX_OUTPUT_SIZE = 10000


def executor_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Executes CLI command from ToolRequest.
    Captures stdout, stderr, exit_code.
    Context-blind - only sees the command, not conversation.
    """
    logger.info("Executor node executing...")

    tool_request = state.get("tool_request")
    tool_history = state.get("tool_history", [])
    step_count = state.get("step_count", 0)
    errors = state.get("errors", [])

    # Check for validation failure (max retries exceeded)
    if not state.get("is_valid", False):
        validation_errors = state.get("validation_errors", [])
        error_msg = f"Execution skipped due to validation errors: {validation_errors}"
        logger.error(error_msg)

        result: ToolResult = {
            "cmd": "VALIDATION_FAILED",
            "exit_code": 1,
            "stdout": "",
            "stderr": error_msg,
        }

        return {
            "last_tool_result": result,
            "tool_history": tool_history + [result],
            "step_count": step_count + 1,
            "errors": errors + [error_msg],
        }

    # Extract command
    if not tool_request:
        error_msg = "No tool request to execute"
        logger.error(error_msg)

        result: ToolResult = {
            "cmd": "NO_COMMAND",
            "exit_code": 1,
            "stdout": "",
            "stderr": error_msg,
        }

        return {
            "last_tool_result": result,
            "tool_history": tool_history + [result],
            "step_count": step_count + 1,
            "errors": errors + [error_msg],
        }

    cmd = tool_request.get("args", {}).get("cmd", "")
    if not cmd:
        error_msg = "Empty command in tool request"
        logger.error(error_msg)

        result: ToolResult = {
            "cmd": "",
            "exit_code": 1,
            "stdout": "",
            "stderr": error_msg,
        }

        return {
            "last_tool_result": result,
            "tool_history": tool_history + [result],
            "step_count": step_count + 1,
            "errors": errors + [error_msg],
        }

    logger.info(f"Executing command: {cmd}")

    try:
        # Execute command
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )

        stdout = process.stdout
        stderr = process.stderr

        # Truncate output if too large
        if len(stdout) > MAX_OUTPUT_SIZE:
            stdout = stdout[:MAX_OUTPUT_SIZE] + f"\n... [truncated, {len(process.stdout)} total chars]"
        if len(stderr) > MAX_OUTPUT_SIZE:
            stderr = stderr[:MAX_OUTPUT_SIZE] + f"\n... [truncated, {len(process.stderr)} total chars]"

        result: ToolResult = {
            "cmd": cmd,
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

        logger.info(f"Command completed with exit code: {process.returncode}")

    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after 60 seconds: {cmd}"
        logger.error(error_msg)

        result: ToolResult = {
            "cmd": cmd,
            "exit_code": 124,  # Standard timeout exit code
            "stdout": "",
            "stderr": error_msg,
        }
        errors.append(error_msg)

    except Exception as e:
        error_msg = f"Command execution failed: {str(e)}"
        logger.error(error_msg)

        result: ToolResult = {
            "cmd": cmd,
            "exit_code": 1,
            "stdout": "",
            "stderr": error_msg,
        }
        errors.append(error_msg)

    return {
        "last_tool_result": result,
        "tool_history": tool_history + [result],
        "step_count": step_count + 1,
        "errors": errors,
    }
