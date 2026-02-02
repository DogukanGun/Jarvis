"""Shell execution tool wrapper."""

from langchain_core.tools import tool

from .base import call_tool_sync


@tool
def exec_tool(command: str, cwd: str | None = None, timeout: int = 30000) -> str:
    """Execute a shell command and return the output.

    Args:
        command: The shell command to execute.
        cwd: Working directory for the command. Optional.
        timeout: Timeout in milliseconds. Default: 30000 (30 seconds).

    Returns:
        Command output including stdout, stderr, and exit code.
    """
    args = {"command": command, "timeout": timeout}
    if cwd:
        args["cwd"] = cwd

    result = call_tool_sync("exec", args)

    # Format the result
    if isinstance(result, dict):
        output_parts = []
        if result.get("stdout"):
            output_parts.append(f"STDOUT:\n{result['stdout']}")
        if result.get("stderr"):
            output_parts.append(f"STDERR:\n{result['stderr']}")
        output_parts.append(f"Exit code: {result.get('exitCode', 'unknown')}")
        return "\n\n".join(output_parts)

    return str(result)
