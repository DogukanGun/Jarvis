"""BtleJack Bluetooth Low Energy (BLE) attack tool wrapper."""

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

_ACTIONS = ["scan", "sniff", "jam", "hijack"]


class BtlejackTool(BaseTool):
    """Wrapper around BtleJack for BLE sniffing, jamming, and hijacking.

    Leverages one or more Micro:Bit devices to interact with Bluetooth
    Low Energy connections at the link layer.
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="btlejack",
            display_name="BtleJack",
            category=ToolCategory.wifi,
            description=(
                "Bluetooth Low Energy (BLE) Swiss Army Knife. Sniff, jam, "
                "and hijack BLE connections."
            ),
            capabilities=["ble_sniff", "ble_jam", "ble_hijack", "ble_scan"],
            auth_level=AuthLevel.medium,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=_ACTIONS,
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="access_address",
                    type="string",
                    required=False,
                    description=(
                        "BLE access address (hex) for sniff/jam/hijack "
                        "(e.g. 0x12345678)."
                    ),
                ),
                ToolParameter(
                    name="channel",
                    type="integer",
                    required=False,
                    description="BLE advertising channel (37, 38, or 39).",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=30,
                    description="Maximum seconds to run before stopping.",
                ),
            ],
            binary_path="/usr/local/bin/btlejack",
            estimated_duration="seconds",
        )

    # ------------------------------------------------------------------ #
    #  Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        access_address: str | None = params.get("access_address")
        channel: int | None = params.get("channel")
        timeout: int = params.get("timeout", 30)

        if action == "scan":
            cmd = ["btlejack", "-s"]
            if channel is not None:
                cmd.extend(["-c", str(channel)])

        elif action == "sniff":
            if not access_address:
                return ToolResult(
                    tool_name="btlejack",
                    success=False,
                    error="Parameter 'access_address' is required for sniff action.",
                )
            cmd = ["btlejack", "-f", access_address]

        elif action == "jam":
            if not access_address:
                return ToolResult(
                    tool_name="btlejack",
                    success=False,
                    error="Parameter 'access_address' is required for jam action.",
                )
            cmd = ["btlejack", "-j", "-f", access_address]

        elif action == "hijack":
            if not access_address:
                return ToolResult(
                    tool_name="btlejack",
                    success=False,
                    error="Parameter 'access_address' is required for hijack action.",
                )
            cmd = ["btlejack", "-t", "-f", access_address]

        else:
            return ToolResult(
                tool_name="btlejack",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: {_ACTIONS}",
            )

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "btlejack"
        result.structured_output = self.parse_output(result.raw_output)
        return result

    # ------------------------------------------------------------------ #
    #  Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract BLE connections and device information from btlejack output."""
        parsed: Dict[str, Any] = {}

        # --- Discovered connections (scan mode) --------------------------- #
        connections: List[Dict[str, str]] = []
        # btlejack -s outputs lines like:
        #   Access Address: 0x12345678 | CRC Init: 0xABCDEF | Channel Map: 0x...
        conn_pattern = re.compile(
            r"Access\s+Address:\s*(0x[0-9A-Fa-f]+)", re.IGNORECASE
        )
        for line in raw.splitlines():
            m = conn_pattern.search(line)
            if m:
                entry: Dict[str, str] = {"access_address": m.group(1)}
                crc_match = re.search(
                    r"CRC\s*Init:\s*(0x[0-9A-Fa-f]+)", line, re.IGNORECASE
                )
                if crc_match:
                    entry["crc_init"] = crc_match.group(1)
                chan_match = re.search(
                    r"Channel\s*Map:\s*(0x[0-9A-Fa-f]+)", line, re.IGNORECASE
                )
                if chan_match:
                    entry["channel_map"] = chan_match.group(1)
                connections.append(entry)

        if connections:
            parsed["connections"] = connections

        # --- Hijack / jam status ------------------------------------------ #
        if re.search(r"hijack(?:ed|ing)\s+success", raw, re.IGNORECASE):
            parsed["hijack_success"] = True
        if re.search(r"jamming", raw, re.IGNORECASE):
            parsed["jamming_active"] = True

        # --- Sniffed packets count ---------------------------------------- #
        pkt_match = re.search(r"(\d+)\s+packets?\s+captured", raw, re.IGNORECASE)
        if pkt_match:
            parsed["packets_captured"] = int(pkt_match.group(1))

        return parsed


# Auto-register
ToolRegistry.register(BtlejackTool())
