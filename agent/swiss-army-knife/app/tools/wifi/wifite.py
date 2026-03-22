"""Wifite2 automated WiFi auditing tool wrapper."""

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


class WifiteTool(BaseTool):
    """Wrapper around Wifite2 for automated WiFi network auditing.

    Scans for nearby networks and attempts to crack them using a
    combination of WPA handshake capture, PMKID attacks, and WPS
    exploitation.
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="wifite2",
            display_name="Wifite2",
            category=ToolCategory.wifi,
            description=(
                "Automated WiFi auditing tool. Scans for networks and "
                "attempts to crack them using multiple methods."
            ),
            capabilities=[
                "wifi_scan",
                "wifi_auto_crack",
                "wps_attack",
                "pmkid_capture",
            ],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="interface",
                    type="string",
                    required=True,
                    description="Wireless interface name (e.g. wlan0).",
                ),
                ToolParameter(
                    name="target_bssid",
                    type="string",
                    required=False,
                    description="Limit attack to a specific BSSID.",
                ),
                ToolParameter(
                    name="kill_conflicting",
                    type="boolean",
                    required=False,
                    default=True,
                    description="Kill conflicting processes before starting.",
                ),
                ToolParameter(
                    name="wps_only",
                    type="boolean",
                    required=False,
                    description="Only target WPS-enabled networks.",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=300,
                    description="Maximum seconds to run before stopping.",
                ),
            ],
            binary_path="/usr/local/bin/wifite",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    #  Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        interface: str = params["interface"]
        target_bssid: str | None = params.get("target_bssid")
        kill_conflicting: bool = params.get("kill_conflicting", True)
        wps_only: bool = params.get("wps_only", False)
        timeout: int = params.get("timeout", 300)

        cmd: List[str] = ["wifite", "-i", interface]

        if target_bssid:
            cmd.extend(["--bssid", target_bssid])

        if kill_conflicting:
            cmd.append("--kill")

        if wps_only:
            cmd.append("--wps")

        # Disable reaver by default for safety
        cmd.append("--no-reaver")

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "wifite2"
        result.structured_output = self.parse_output(result.raw_output)
        return result

    # ------------------------------------------------------------------ #
    #  Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract discovered networks and cracked keys from wifite output."""
        parsed: Dict[str, Any] = {}

        # --- Discovered networks ------------------------------------------ #
        # Wifite lists networks with columns: NUM  ESSID  BSSID  CH  ENCR  POWER  WPS  CLIENT
        networks: List[Dict[str, str]] = []
        network_pattern = re.compile(
            r"^\s*\d+\s+"            # NUM
            r"(.+?)\s{2,}"           # ESSID
            r"([0-9A-Fa-f:]{17})\s+" # BSSID
            r"(\d+)\s+"              # CH
            r"(\S+)\s+"              # ENCR
            r"(-?\d+\s*db)",         # POWER
            re.IGNORECASE,
        )
        for line in raw.splitlines():
            m = network_pattern.search(line)
            if m:
                networks.append({
                    "essid": m.group(1).strip(),
                    "bssid": m.group(2),
                    "channel": m.group(3),
                    "encryption": m.group(4),
                    "power": m.group(5),
                })
        if networks:
            parsed["networks"] = networks

        # --- Cracked keys ------------------------------------------------- #
        cracked: List[Dict[str, str]] = []
        key_pattern = re.compile(
            r"cracked\s+(.+?)\s+\(([0-9A-Fa-f:]{17})\)\s+Key:\s+(.+)",
            re.IGNORECASE,
        )
        for line in raw.splitlines():
            m = key_pattern.search(line)
            if m:
                cracked.append({
                    "essid": m.group(1).strip(),
                    "bssid": m.group(2),
                    "key": m.group(3).strip(),
                })
        if cracked:
            parsed["cracked"] = cracked

        # --- PMKID captures ----------------------------------------------- #
        pmkid_captures = re.findall(
            r"captured PMKID.*?([0-9A-Fa-f:]{17})", raw, re.IGNORECASE
        )
        if pmkid_captures:
            parsed["pmkid_captures"] = pmkid_captures

        return parsed


# Auto-register
ToolRegistry.register(WifiteTool())
