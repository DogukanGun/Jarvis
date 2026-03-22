"""ntopng network traffic monitoring and analysis tool wrapper."""

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


class NtopngTool(BaseTool):
    """Network traffic monitoring and analysis via ntopng.

    Supports starting the ntopng daemon for real-time flow visualisation,
    querying process status, and accessing the REST API for host, flow,
    and protocol statistics.
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ntopng",
            display_name="ntopng",
            category=ToolCategory.monitoring,
            description=(
                "Network traffic monitoring and analysis. Real-time flow "
                "visualization and historical data."
            ),
            capabilities=[
                "traffic_monitor",
                "flow_analysis",
                "protocol_stats",
                "host_discovery",
            ],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=["start", "status", "query"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="interface",
                    type="string",
                    required=False,
                    default="eth0",
                    description="Network interface to monitor.",
                ),
                ToolParameter(
                    name="port",
                    type="integer",
                    required=False,
                    default=3000,
                    description="Web UI port for ntopng.",
                ),
                ToolParameter(
                    name="query_endpoint",
                    type="string",
                    required=False,
                    description="REST API endpoint to query (e.g. get/interface/data.lua).",
                ),
            ],
            binary_path="/usr/bin/ntopng",
            is_long_running=True,
            estimated_duration="hours",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        interface: str = params.get("interface", "eth0")
        port: int = params.get("port", 3000)
        query_endpoint: str | None = params.get("query_endpoint")

        if action == "start":
            return await self._start(interface, port)
        elif action == "status":
            return await self._status()
        elif action == "query":
            return await self._query(port, query_endpoint)
        else:
            return ToolResult(
                tool_name="ntopng",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: start, status, query.",
            )

    async def _start(self, interface: str, port: int) -> ToolResult:
        """Start ntopng as a long-running background daemon."""
        cmd: List[str] = [
            "/usr/bin/ntopng",
            "-i", interface,
            "-w", str(port),
        ]

        try:
            job_id = await session_manager.start_session(
                tool_name="ntopng",
                cmd=cmd,
            )
            return ToolResult(
                tool_name="ntopng",
                success=True,
                raw_output=f"ntopng started on interface {interface}, web UI on port {port}",
                structured_output={
                    "job_id": job_id,
                    "interface": interface,
                    "port": port,
                    "web_url": f"http://localhost:{port}",
                    "status": "running",
                },
            )
        except Exception as exc:
            return ToolResult(
                tool_name="ntopng",
                success=False,
                error=f"Failed to start ntopng: {exc}",
            )

    async def _status(self) -> ToolResult:
        """Check if ntopng is currently running."""
        # Check via pgrep for running ntopng processes
        result = await self._executor.execute(
            ["pgrep", "-a", "ntopng"], timeout=10,
        )

        sessions = session_manager.list_sessions()
        ntopng_sessions = [s for s in sessions if s["tool_name"] == "ntopng"]

        is_running = result.success or bool(ntopng_sessions)

        return ToolResult(
            tool_name="ntopng",
            success=True,
            raw_output=result.raw_output if result.raw_output else "ntopng is not running",
            structured_output={
                "running": is_running,
                "process_info": result.raw_output if result.success else None,
                "managed_sessions": ntopng_sessions,
            },
        )

    async def _query(self, port: int, query_endpoint: str | None) -> ToolResult:
        """Query ntopng REST API endpoint."""
        if not query_endpoint:
            return ToolResult(
                tool_name="ntopng",
                success=False,
                error="Parameter 'query_endpoint' is required for query action.",
            )

        if httpx is None:
            return ToolResult(
                tool_name="ntopng",
                success=False,
                error="httpx library is not installed; cannot query ntopng API.",
            )

        url = f"http://localhost:{port}/lua/rest/v2/{query_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                raw_body = response.text
                status_code = response.status_code

            structured = JsonOutputParser.parse(raw_body)

            return ToolResult(
                tool_name="ntopng",
                success=(200 <= status_code < 300),
                raw_output=raw_body,
                structured_output={
                    "status_code": status_code,
                    "endpoint": query_endpoint,
                    "data": structured,
                },
                error=None if 200 <= status_code < 300 else f"HTTP {status_code}",
            )
        except Exception as exc:
            return ToolResult(
                tool_name="ntopng",
                success=False,
                error=f"Failed to query ntopng API: {exc}",
            )

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Parse ntopng text output or API JSON responses."""
        parsed: Dict[str, Any] = {}

        # Attempt JSON parsing first (API responses)
        json_data = JsonOutputParser.parse(raw)
        if json_data is not None:
            parsed["api_response"] = json_data
            return parsed

        # Extract host information from text output
        host_re = re.compile(
            r"(\d{1,3}(?:\.\d{1,3}){3})\s+"   # IP address
            r"(\S+)\s+"                         # hostname or MAC
            r"(\d+)\s+"                         # traffic bytes
        )
        hosts: List[Dict[str, str]] = []
        for m in host_re.finditer(raw):
            hosts.append({
                "ip": m.group(1),
                "name": m.group(2),
                "bytes": m.group(3),
            })
        if hosts:
            parsed["hosts"] = hosts

        # Extract protocol statistics
        proto_re = re.compile(r"(\w+)\s+(\d+(?:\.\d+)?)\s*%")
        protocols: List[Dict[str, str]] = []
        for m in proto_re.finditer(raw):
            protocols.append({
                "protocol": m.group(1),
                "percentage": m.group(2),
            })
        if protocols:
            parsed["protocols"] = protocols

        return parsed


# Auto-register
ToolRegistry.register(NtopngTool())
