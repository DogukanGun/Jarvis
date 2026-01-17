from typing import List

from langchain_core.tools import tool
from pydantic import field_validator, Field, BaseModel

from app.graphs.hacker_graph.tools.helper import _require_binary, _run_cmd

class NetcatPortScanInput(BaseModel):
    target: str = Field(..., description="Private/loopback host or IP (e.g. 192.168.1.10, 10.0.0.5, 127.0.0.1).")
    ports: List[int] = Field(..., description="Ports to probe (e.g. [22, 80, 443]). Max 100 ports.")
    timeout_seconds: int = Field(2, ge=1, le=10, description="Per-port timeout in seconds.")
    tcp: bool = Field(True, description="Use TCP connect probing.")

    @field_validator("ports")
    @classmethod
    def _validate_ports(cls, v: List[int]) -> List[int]:
        if len(v) > 100:
            raise ValueError("Too many ports. Max 100.")
        for p in v:
            if p < 1 or p > 65535:
                raise ValueError(f"Invalid port: {p}")
        return v

@tool("port_scan_netcat", args_schema=NetcatPortScanInput)
def port_scan_netcat(target: str, ports: List[int], timeout_seconds: int = 2, tcp: bool = True) -> str:
    """
    Probe a list of TCP ports using netcat (nc). Restricted to private/loopback targets.
    """
    _require_binary("nc")

    results = []
    for p in ports:
        # -z: scan mode (no I/O), -v: verbose, -w: timeout
        # Note: netcat flags vary across OS; this works for common nc (OpenBSD).
        cmd = ["nc", "-vz", "-w", str(timeout_seconds), target, str(p)]
        out = _run_cmd(cmd, timeout_s=max(5, timeout_seconds + 3))
        results.append(f"== Port {p} ==\n{out}")

    return "\n\n".join(results)
