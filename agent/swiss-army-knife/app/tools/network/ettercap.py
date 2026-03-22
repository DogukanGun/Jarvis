"""Ettercap man-in-the-middle attack tool wrapper."""

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


class EttercapTool(BaseTool):
    """Man-in-the-middle attack tool. ARP poisoning, traffic sniffing, and
    protocol dissection powered by Ettercap."""

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ettercap",
            display_name="Ettercap",
            category=ToolCategory.network,
            description=(
                "Man-in-the-middle attack tool. ARP poisoning, traffic sniffing, "
                "and protocol dissection."
            ),
            capabilities=[
                "mitm",
                "arp_poison",
                "traffic_sniff",
                "protocol_dissect",
            ],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="interface",
                    type="string",
                    required=True,
                    description="Network interface to use (e.g. eth0).",
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=["sniff", "mitm", "scan"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="target1",
                    type="string",
                    required=False,
                    description="First target IP for MITM / sniffing.",
                ),
                ToolParameter(
                    name="target2",
                    type="string",
                    required=False,
                    description="Second target IP (typically the gateway).",
                ),
                ToolParameter(
                    name="filter_file",
                    type="string",
                    required=False,
                    description="Path to an etterfilter compiled filter file.",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=60,
                    description="Maximum execution time in seconds.",
                ),
            ],
            binary_path="/usr/bin/ettercap",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        interface: str = params["interface"]
        target1: str | None = params.get("target1")
        target2: str | None = params.get("target2")
        filter_file: str | None = params.get("filter_file")
        timeout: int = params.get("timeout", 60)

        cmd = self._build_command(action, interface, target1, target2, filter_file)
        if cmd is None:
            return ToolResult(
                tool_name="ettercap",
                success=False,
                error=f"Unsupported action '{action}' or missing required parameters.",
            )

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "ettercap"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    # ------------------------------------------------------------------ #
    # Command builders
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_command(
        action: str,
        interface: str,
        target1: str | None,
        target2: str | None,
        filter_file: str | None,
    ) -> List[str] | None:
        # Always text-mode (-T), quiet (-q), non-interactive
        base: List[str] = ["/usr/bin/ettercap", "-T", "-q", "-i", interface]

        if action == "scan":
            # Quick host discovery: run ettercap in text mode, it will display
            # discovered hosts and exit.
            return base

        if action == "sniff":
            cmd = list(base)
            t1 = f"/{target1}//" if target1 else "//"
            t2 = f"/{target2}//" if target2 else "//"
            cmd += ["-M", "arp:remote", t1, t2]
            if filter_file:
                cmd += ["-F", filter_file]
            return cmd

        if action == "mitm":
            cmd = list(base)
            t1 = f"/{target1}//" if target1 else "//"
            t2 = f"/{target2}//" if target2 else "//"
            cmd += ["-M", "arp:remote,oneway", t1, t2]
            if filter_file:
                cmd += ["-F", filter_file]
            return cmd

        return None

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract host list and captured credentials from ettercap output."""
        hosts: List[Dict[str, str]] = []
        credentials: List[Dict[str, str]] = []

        # Host lines: e.g. "192.168.1.5   00:11:22:33:44:55"
        ip_mac_re = re.compile(
            r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F:]{17})"
        )
        # Credential lines: e.g. "HTTP : 192.168.1.5 -> USER: admin  PASS: secret"
        cred_re = re.compile(
            r"(\S+)\s*:\s*(\d{1,3}(?:\.\d{1,3}){3})\s*->\s*USER:\s*(\S+)\s+PASS:\s*(\S*)"
        )

        for line in raw.splitlines():
            m_host = ip_mac_re.search(line)
            if m_host:
                hosts.append({"ip": m_host.group(1), "mac": m_host.group(2)})

            m_cred = cred_re.search(line)
            if m_cred:
                credentials.append(
                    {
                        "protocol": m_cred.group(1),
                        "host": m_cred.group(2),
                        "user": m_cred.group(3),
                        "password": m_cred.group(4),
                    }
                )

        return {
            "host_count": len(hosts),
            "hosts": hosts,
            "credentials": credentials,
        }


ToolRegistry.register(EttercapTool())
