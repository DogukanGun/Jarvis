import platform

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.graphs.hacker_graph.tools.helper import _require_binary, _run_cmd


class PingInput(BaseModel):
    target: str = Field(..., description="Private/loopback host or IP.")
    count: int = Field(3, ge=1, le=10, description="Number of echo requests.")
    timeout_seconds: int = Field(2, ge=1, le=10, description="Timeout per ping.")


@tool("ip_resolution_ping", args_schema=PingInput)
def ip_resolution_ping(target: str, count: int = 3, timeout_seconds: int = 2) -> str:
    """
    Ping a host to check reachability / resolve IP. Restricted to private/loopback targets.
    """
    _require_binary("ping")

    sys = platform.system().lower()
    if "windows" in sys:
        # Windows: -n count, -w timeout_ms
        cmd = ["ping", "-n", str(count), "-w", str(timeout_seconds * 1000), target]
    elif "darwin" in sys:
        # macOS: -c count, -W timeout_ms (on mac, -W is in ms)
        cmd = ["ping", "-c", str(count), "-W", str(timeout_seconds * 1000), target]
    else:
        # Linux: -c count, -W timeout_seconds
        cmd = ["ping", "-c", str(count), "-W", str(timeout_seconds), target]

    return _run_cmd(cmd, timeout_s=max(10, count * (timeout_seconds + 1)))

