"""Cron scheduling tool wrapper."""

from langchain_core.tools import tool

from .base import call_tool_sync


@tool
def cron_tool(
    action: str,
    id: str | None = None,
    name: str | None = None,
    schedule: str | None = None,
    command: str | None = None,
    enabled: bool | None = None,
) -> str:
    """Manage scheduled tasks (cron jobs).

    Args:
        action: Cron action - "status", "list", "add", "update", "remove", "run"
        id: Job ID (for update/remove/run actions)
        name: Job name (for add action)
        schedule: Cron schedule expression, e.g. "*/5 * * * *" for every 5 minutes
        command: Shell command to execute
        enabled: Whether the job is enabled

    Returns:
        Result of the cron action as JSON string.

    Schedule format (standard cron):
        minute hour day-of-month month day-of-week

    Examples:
        - "* * * * *"     -> Every minute
        - "*/5 * * * *"   -> Every 5 minutes
        - "0 * * * *"     -> Every hour at minute 0
        - "0 9 * * *"     -> Daily at 9:00 AM
        - "0 9 * * 1"     -> Every Monday at 9:00 AM

    Usage examples:
        - cron_tool(action="list") -> List all jobs
        - cron_tool(action="add", name="backup", schedule="0 2 * * *", command="./backup.sh")
        - cron_tool(action="run", id="job_1") -> Run job immediately
        - cron_tool(action="remove", id="job_1") -> Delete job
    """
    args = {"action": action}
    if id:
        args["id"] = id
    if name:
        args["name"] = name
    if schedule:
        args["schedule"] = schedule
    if command:
        args["command"] = command
    if enabled is not None:
        args["enabled"] = enabled

    result = call_tool_sync("cron", args)
    return str(result)
