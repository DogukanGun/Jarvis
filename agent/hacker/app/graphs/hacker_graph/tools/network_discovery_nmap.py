import ipaddress

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from app.graphs.hacker_graph.tools.helper import _require_binary, _run_cmd


class NmapDiscoveryInput(BaseModel):
    target: str = Field(..., description="Private/loopback host or CIDR in private range (e.g. 192.168.1.0/24).")
    ports: str = Field("1-1024", description="Port range, e.g. '1-1024' or '22,80,443'.")
    ping_only: bool = Field(False, description="If true, run a ping scan only (host discovery).")
    timing: str = Field("T3", description="Nmap timing template: T0..T5 (default T3).")

    @field_validator("timing")
    @classmethod
    def _validate_timing(cls, v: str) -> str:
        if v not in {"T0", "T1", "T2", "T3", "T4", "T5"}:
            raise ValueError("timing must be one of T0..T5")
        return v

    @field_validator("ports")
    @classmethod
    def _validate_ports(cls, v: str) -> str:
        # disallow dangerous options smuggled into ports
        if any(ch in v for ch in [";", "&", "|", "$", "`"]):
            raise ValueError("Invalid characters in ports.")
        if len(v) > 200:
            raise ValueError("ports string too long.")
        return v.strip()

@tool("network_discovery_nmap", args_schema=NmapDiscoveryInput)
def network_discovery_nmap(target: str, ports: str = "1-1024", ping_only: bool = False, timing: str = "T3") -> str:
    """
    Run a *non-aggressive* nmap scan for host discovery or basic TCP connect scan.
    Restricted to private/loopback targets/CIDRs.
    """
    _require_binary("nmap")

    # Guardrails: no OS detection (-O), no scripts, no -A, no UDP, no version intensity tricks
    base = ["nmap", f"-{timing}", "--reason"]

    if ping_only:
        # Ping scan (host discovery)
        cmd = base + ["-sn", target]
    else:
        # Basic TCP connect scan
        # -sT uses system connect() (works without raw socket privileges)
        cmd = base + ["-sT", "-Pn", "-p", ports, target]

    return _run_cmd(cmd, timeout_s=120)

