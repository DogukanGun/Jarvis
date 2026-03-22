"""RootTheBox CTF scoring engine and game platform wrapper."""

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
from app.tools.output_parser import JsonOutputParser
from app.tools.registry import ToolRegistry
from app.services.session_manager import session_manager

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


class RootTheBoxTool(BaseTool):
    """CTF scoring engine and game platform via RootTheBox.

    Supports starting the game server, checking its status,
    and creating new CTF competitions with custom configurations.
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="rootthebox",
            display_name="RootTheBox CTF",
            category=ToolCategory.ctf,
            description=(
                "CTF scoring engine and game platform. Create and manage "
                "capture-the-flag competitions."
            ),
            capabilities=[
                "ctf_setup",
                "ctf_manage",
                "scoreboard",
            ],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=["start", "status", "create_game"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="port",
                    type="integer",
                    required=False,
                    default=8888,
                    description="Port number for the web interface.",
                ),
                ToolParameter(
                    name="config_file",
                    type="string",
                    required=False,
                    description="Path to a game configuration file.",
                ),
            ],
            binary_path="/usr/local/bin/rootthebox",
            is_long_running=True,
            estimated_duration="hours",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        port: int = params.get("port", 8888)
        config_file: str | None = params.get("config_file")

        if action == "start":
            return await self._start(port)
        elif action == "status":
            return await self._status(port)
        elif action == "create_game":
            return await self._create_game(port, config_file)
        else:
            return ToolResult(
                tool_name="rootthebox",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: start, status, create_game.",
            )

    async def _start(self, port: int) -> ToolResult:
        """Start RootTheBox as a long-running background process."""
        cmd: List[str] = [
            "/usr/local/bin/rootthebox",
            "--setup",
            "--port", str(port),
        ]

        try:
            job_id = await session_manager.start_session(
                tool_name="rootthebox",
                cmd=cmd,
            )
            return ToolResult(
                tool_name="rootthebox",
                success=True,
                raw_output=f"RootTheBox CTF server started on port {port}",
                structured_output={
                    "job_id": job_id,
                    "port": port,
                    "web_url": f"http://localhost:{port}",
                    "status": "running",
                },
            )
        except Exception as exc:
            return ToolResult(
                tool_name="rootthebox",
                success=False,
                error=f"Failed to start RootTheBox: {exc}",
            )

    async def _status(self, port: int) -> ToolResult:
        """Query RootTheBox health endpoint to check status."""
        # First check managed sessions
        sessions = session_manager.list_sessions()
        rtb_sessions = [s for s in sessions if s["tool_name"] == "rootthebox"]

        # Then try the health endpoint
        api_status: Dict[str, Any] | None = None
        if httpx is not None:
            try:
                url = f"http://localhost:{port}/api/v1/scoreboard"
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url)
                    if 200 <= response.status_code < 300:
                        api_status = JsonOutputParser.parse(response.text)
            except Exception:
                pass

        is_running = bool(rtb_sessions) or api_status is not None

        return ToolResult(
            tool_name="rootthebox",
            success=True,
            raw_output="RootTheBox is running" if is_running else "RootTheBox is not running",
            structured_output={
                "running": is_running,
                "managed_sessions": rtb_sessions,
                "api_status": api_status,
                "port": port,
            },
        )

    async def _create_game(self, port: int, config_file: str | None) -> ToolResult:
        """Create a new CTF game from a configuration file."""
        cmd: List[str] = [
            "/usr/local/bin/rootthebox",
            "--setup",
            "--port", str(port),
        ]

        if config_file:
            cmd += ["--config", config_file]

        result = await self._executor.execute(cmd, timeout=120)
        result.tool_name = "rootthebox"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)
            result.structured_output["port"] = port
            if config_file:
                result.structured_output["config_file"] = config_file

        return result

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Parse RootTheBox output for setup and game status information."""
        parsed: Dict[str, Any] = {}

        # Attempt JSON parsing first (API responses)
        json_data = JsonOutputParser.parse(raw)
        if json_data is not None:
            parsed["api_response"] = json_data
            return parsed

        # Extract game setup status
        if "setup complete" in raw.lower() or "game created" in raw.lower():
            parsed["setup_complete"] = True
        else:
            parsed["setup_complete"] = False

        # Extract team information
        team_re = re.compile(r"Team:\s+(\S+)", re.IGNORECASE)
        teams = team_re.findall(raw)
        if teams:
            parsed["teams"] = teams

        # Extract flag/challenge information
        flag_re = re.compile(r"Flag:\s+(.+)", re.IGNORECASE)
        flags = [m.strip() for m in flag_re.findall(raw)]
        if flags:
            parsed["flags"] = flags

        # Extract scoreboard data
        score_re = re.compile(
            r"(\S+)\s+(\d+)\s+(?:points|pts)", re.IGNORECASE
        )
        scores: List[Dict[str, Any]] = []
        for m in score_re.finditer(raw):
            scores.append({
                "team": m.group(1),
                "score": int(m.group(2)),
            })
        if scores:
            parsed["scoreboard"] = scores

        # Extract errors or warnings
        error_re = re.compile(r"\[ERROR\]\s+(.+)", re.IGNORECASE)
        errors = [m.group(1).strip() for m in error_re.finditer(raw)]
        if errors:
            parsed["errors"] = errors

        return parsed


# Auto-register
ToolRegistry.register(RootTheBoxTool())
