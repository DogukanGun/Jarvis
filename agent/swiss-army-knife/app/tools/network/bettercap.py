"""Bettercap network reconnaissance and MITM tool wrapper."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)
from app.tools.executor import SubprocessExecutor
from app.tools.registry import ToolRegistry


class BettercapTool(BaseTool):
    """Network reconnaissance, MITM attacks, ARP/DNS spoofing, and packet sniffing
    powered by Bettercap."""

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="bettercap",
            display_name="Bettercap",
            category=ToolCategory.network,
            description=(
                "Network reconnaissance, MITM attacks, ARP spoofing, DNS spoofing, "
                "packet sniffing, WiFi and BLE recon."
            ),
            capabilities=[
                "network_recon",
                "arp_spoof",
                "dns_spoof",
                "mitm",
                "packet_sniff",
                "net_probe",
            ],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="interface",
                    type="string",
                    required=False,
                    description="Network interface to use (e.g. eth0, wlan0).",
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=["recon", "arp_spoof", "dns_spoof", "sniff", "custom"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="target",
                    type="string",
                    required=False,
                    description="Target IP or CIDR for ARP/DNS spoofing.",
                ),
                ToolParameter(
                    name="gateway",
                    type="string",
                    required=False,
                    description="Gateway IP address for spoofing attacks.",
                ),
                ToolParameter(
                    name="caplet",
                    type="string",
                    required=False,
                    description="Path to a bettercap caplet file to execute.",
                ),
                ToolParameter(
                    name="eval_command",
                    type="string",
                    required=False,
                    description="Raw bettercap eval string (used with action='custom').",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=60,
                    description="Maximum execution time in seconds.",
                ),
            ],
            binary_path="/usr/local/bin/bettercap",
            is_long_running=True,
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        interface: str | None = params.get("interface")
        target: str | None = params.get("target")
        gateway: str | None = params.get("gateway")
        timeout: int = params.get("timeout", 60)
        eval_command: str | None = params.get("eval_command")

        eval_str = self._build_eval(action, target, gateway, timeout, eval_command)
        if eval_str is None:
            return ToolResult(
                tool_name="bettercap",
                success=False,
                error=f"Unsupported action '{action}' or missing required parameters.",
            )

        cmd: List[str] = ["/usr/local/bin/bettercap"]
        if interface:
            cmd += ["-iface", interface]
        cmd += ["-eval", eval_str]

        result = await self._executor.execute(cmd, timeout=timeout + 10)
        result.tool_name = "bettercap"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    # ------------------------------------------------------------------ #
    # Build eval strings per action
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_eval(
        action: str,
        target: str | None,
        gateway: str | None,
        timeout: int,
        eval_command: str | None,
    ) -> str | None:
        if action == "recon":
            return "net.probe on; net.recon on; sleep 10; net.show; quit"

        if action == "arp_spoof":
            if not target:
                return None
            parts = [f"set arp.spoof.targets {target}"]
            if gateway:
                parts.append(f"set arp.spoof.gateway {gateway}")
            parts += ["arp.spoof on", f"sleep {timeout}", "quit"]
            return "; ".join(parts)

        if action == "dns_spoof":
            if not target:
                return None
            parts = []
            if target:
                parts.append(f"set arp.spoof.targets {target}")
            if gateway:
                parts.append(f"set arp.spoof.gateway {gateway}")
            parts += [
                "arp.spoof on",
                "set dns.spoof.all true",
                "dns.spoof on",
                f"sleep {timeout}",
                "quit",
            ]
            return "; ".join(parts)

        if action == "sniff":
            return f"net.sniff on; sleep {timeout}; quit"

        if action == "custom":
            return eval_command if eval_command else None

        return None

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract discovered hosts (IP, MAC, hostname/vendor) from net.show output."""
        hosts: List[Dict[str, str]] = []
        # Bettercap net.show typically outputs tabular rows with IP, MAC, Name columns
        # Example line:  192.168.1.1  aa:bb:cc:dd:ee:ff  gateway
        ip_mac_re = re.compile(
            r"(\d{1,3}(?:\.\d{1,3}){3})\s+"          # IP address
            r"([0-9a-fA-F:]{17})\s*"                  # MAC address
            r"(.*)",                                    # hostname / vendor
        )
        for line in raw.splitlines():
            m = ip_mac_re.search(line)
            if m:
                hosts.append(
                    {
                        "ip": m.group(1),
                        "mac": m.group(2),
                        "hostname": m.group(3).strip(),
                    }
                )

        return {
            "host_count": len(hosts),
            "hosts": hosts,
        }


ToolRegistry.register(BettercapTool())
