"""Aircrack-ng WiFi security auditing suite wrapper."""

from __future__ import annotations

import csv
import io
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

_ACTIONS = ["monitor_start", "monitor_stop", "scan", "deauth", "crack"]


class AircrackTool(BaseTool):
    """Wrapper around the Aircrack-ng WiFi auditing suite.

    Supports monitor-mode toggling (airmon-ng), passive scanning
    (airodump-ng), client deauthentication (aireplay-ng), and
    WPA/WEP key cracking (aircrack-ng).
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="aircrack-ng",
            display_name="Aircrack-ng WiFi Suite",
            category=ToolCategory.wifi,
            description=(
                "WiFi security auditing suite. Includes monitor mode "
                "(airmon-ng), packet capture (airodump-ng), deauthentication "
                "(aireplay-ng), and WPA/WEP key cracking (aircrack-ng)."
            ),
            capabilities=[
                "wifi_monitor",
                "wifi_capture",
                "wifi_deauth",
                "wifi_crack",
                "packet_injection",
            ],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="interface",
                    type="string",
                    required=True,
                    description="Wireless interface name (e.g. wlan0, wlan0mon).",
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=_ACTIONS,
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="bssid",
                    type="string",
                    required=False,
                    description="Target access-point BSSID (required for deauth).",
                ),
                ToolParameter(
                    name="channel",
                    type="integer",
                    required=False,
                    description="WiFi channel number.",
                ),
                ToolParameter(
                    name="capture_file",
                    type="string",
                    required=False,
                    description="Path to a capture file (required for crack).",
                ),
                ToolParameter(
                    name="wordlist",
                    type="string",
                    required=False,
                    default="/usr/share/wordlists/rockyou.txt",
                    description="Path to the wordlist used for cracking.",
                ),
            ],
            binary_path="/usr/sbin/aircrack-ng",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    #  Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        interface: str = params["interface"]
        action: str = params["action"]
        bssid: str | None = params.get("bssid")
        channel: int | None = params.get("channel")
        capture_file: str | None = params.get("capture_file")
        wordlist: str = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")

        if action == "monitor_start":
            cmd = ["airmon-ng", "start", interface]
            result = await self._executor.execute(cmd, timeout=15)

        elif action == "monitor_stop":
            cmd = ["airmon-ng", "stop", interface]
            result = await self._executor.execute(cmd, timeout=15)

        elif action == "scan":
            scan_prefix = "/tmp/scan"
            cmd = [
                "airodump-ng",
                "--write-interval", "1",
                "--output-format", "csv",
                "-w", scan_prefix,
                interface,
            ]
            if channel is not None:
                cmd.extend(["-c", str(channel)])
            result = await self._executor.execute(cmd, timeout=30)
            # Attempt to read the CSV produced by airodump-ng
            try:
                with open(f"{scan_prefix}-01.csv", "r", errors="replace") as fh:
                    csv_content = fh.read()
                result.raw_output = csv_content
            except FileNotFoundError:
                result.warnings.append(
                    "CSV scan file not found; raw stdout retained."
                )

        elif action == "deauth":
            if not bssid:
                return ToolResult(
                    tool_name="aircrack-ng",
                    success=False,
                    error="Parameter 'bssid' is required for deauth action.",
                )
            cmd = ["aireplay-ng", "--deauth", "10", "-a", bssid, interface]
            result = await self._executor.execute(cmd, timeout=30)

        elif action == "crack":
            if not capture_file:
                return ToolResult(
                    tool_name="aircrack-ng",
                    success=False,
                    error="Parameter 'capture_file' is required for crack action.",
                )
            cmd = ["aircrack-ng", "-w", wordlist, capture_file]
            result = await self._executor.execute(cmd, timeout=600)

        else:
            return ToolResult(
                tool_name="aircrack-ng",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: {_ACTIONS}",
            )

        result.tool_name = "aircrack-ng"
        result.structured_output = self.parse_output(result.raw_output)
        return result

    # ------------------------------------------------------------------ #
    #  Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Parse airodump-ng CSV or aircrack-ng key output."""
        parsed: Dict[str, Any] = {}

        # --- airodump CSV parsing ----------------------------------------- #
        networks: List[Dict[str, str]] = []
        try:
            reader = csv.reader(io.StringIO(raw))
            headers: List[str] | None = None
            for row in reader:
                stripped = [c.strip() for c in row]
                if not stripped or not stripped[0]:
                    headers = None
                    continue
                if "BSSID" in stripped[0]:
                    headers = stripped
                    continue
                if headers and len(stripped) >= len(headers):
                    entry = dict(zip(headers, stripped))
                    if entry.get("BSSID"):
                        networks.append(entry)
        except Exception:
            pass

        if networks:
            parsed["networks"] = networks

        # --- KEY FOUND extraction ----------------------------------------- #
        key_match = re.search(r"KEY FOUND!\s*\[\s*(.+?)\s*\]", raw)
        if key_match:
            parsed["key_found"] = key_match.group(1)

        return parsed


# Auto-register
ToolRegistry.register(AircrackTool())
