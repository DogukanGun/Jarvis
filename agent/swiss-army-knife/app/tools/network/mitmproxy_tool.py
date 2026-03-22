"""Mitmproxy HTTP/HTTPS interception proxy tool wrapper."""

from __future__ import annotations

import re
import time
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


class MitmproxyTool(BaseTool):
    """HTTP/HTTPS interception proxy. Capture, inspect, modify, and replay
    web traffic using mitmproxy / mitmdump."""

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mitmproxy",
            display_name="Mitmproxy",
            category=ToolCategory.network,
            description=(
                "HTTP/HTTPS interception proxy. Capture, inspect, modify, "
                "and replay web traffic."
            ),
            capabilities=[
                "http_intercept",
                "https_intercept",
                "traffic_capture",
                "request_replay",
                "ssl_strip",
            ],
            auth_level=AuthLevel.medium,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=["dump", "start", "replay"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="listen_port",
                    type="integer",
                    required=False,
                    default=8080,
                    description="Port for the proxy to listen on.",
                ),
                ToolParameter(
                    name="listen_host",
                    type="string",
                    required=False,
                    default="0.0.0.0",
                    description="Host/IP for the proxy to bind to.",
                ),
                ToolParameter(
                    name="flow_file",
                    type="string",
                    required=False,
                    description="Path to a saved flow file (for replay).",
                ),
                ToolParameter(
                    name="filter_expression",
                    type="string",
                    required=False,
                    description="Mitmproxy filter expression (e.g. '~d example.com').",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=60,
                    description="Maximum execution time in seconds.",
                ),
            ],
            binary_path="/usr/local/bin/mitmdump",
            is_long_running=True,
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        listen_port: int = params.get("listen_port", 8080)
        listen_host: str = params.get("listen_host", "0.0.0.0")
        flow_file: str | None = params.get("flow_file")
        filter_expression: str | None = params.get("filter_expression")
        timeout: int = params.get("timeout", 60)

        if action == "dump":
            return await self._action_dump(
                listen_port, listen_host, filter_expression, timeout
            )

        if action == "replay":
            return await self._action_replay(flow_file, filter_expression, timeout)

        if action == "start":
            return await self._action_start(
                listen_port, listen_host, filter_expression
            )

        return ToolResult(
            tool_name="mitmproxy",
            success=False,
            error=f"Unsupported action '{action}'.",
        )

    # ---- action helpers ------------------------------------------------ #

    async def _action_dump(
        self,
        port: int,
        host: str,
        filter_expr: str | None,
        timeout: int,
    ) -> ToolResult:
        timestamp = int(time.time())
        flow_path = f"/tmp/flows_{timestamp}"
        cmd: List[str] = [
            "/usr/local/bin/mitmdump",
            "-p", str(port),
            "--listen-host", host,
            "--set", "flow_detail=2",
            "-w", flow_path,
        ]
        if filter_expr:
            cmd.append(filter_expr)

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "mitmproxy"

        if result.success or result.raw_output:
            parsed = self.parse_output(result.raw_output)
            parsed["flow_file"] = flow_path
            result.structured_output = parsed

        return result

    async def _action_replay(
        self,
        flow_file: str | None,
        filter_expr: str | None,
        timeout: int,
    ) -> ToolResult:
        if not flow_file:
            return ToolResult(
                tool_name="mitmproxy",
                success=False,
                error="Parameter 'flow_file' is required for the 'replay' action.",
            )

        cmd: List[str] = [
            "/usr/local/bin/mitmdump",
            "-S", flow_file,
        ]
        if filter_expr:
            cmd.append(filter_expr)

        result = await self._executor.execute(cmd, timeout=timeout)
        result.tool_name = "mitmproxy"

        if result.success or result.raw_output:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    async def _action_start(
        self,
        port: int,
        host: str,
        filter_expr: str | None,
    ) -> ToolResult:
        """Start mitmdump as a long-running background session via SessionManager."""
        try:
            from app.services.session_manager import session_manager
        except ImportError:
            return ToolResult(
                tool_name="mitmproxy",
                success=False,
                error="SessionManager is not available in this environment.",
            )

        timestamp = int(time.time())
        flow_path = f"/tmp/flows_{timestamp}"
        cmd: List[str] = [
            "/usr/local/bin/mitmdump",
            "-p", str(port),
            "--listen-host", host,
            "--set", "flow_detail=2",
            "-w", flow_path,
        ]
        if filter_expr:
            cmd.append(filter_expr)

        job_id = await session_manager.start_session("mitmproxy", cmd)
        return ToolResult(
            tool_name="mitmproxy",
            success=True,
            raw_output=f"Mitmproxy session started. job_id={job_id}, flow_file={flow_path}",
            structured_output={
                "job_id": job_id,
                "flow_file": flow_path,
                "listen_port": port,
                "listen_host": host,
            },
        )

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract request/response summaries from mitmdump output."""
        requests: List[Dict[str, str]] = []

        # mitmdump lines look like:
        #   >> GET https://example.com/path
        #       200 OK  text/html  12345b
        # or compact:
        #   GET https://example.com/path << 200 OK 1.23kb
        req_re = re.compile(
            r"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|CONNECT)\s+(https?://\S+)"
        )
        status_re = re.compile(r"<<?\s*(\d{3})\s+(\S+)")

        current_request: Dict[str, str] | None = None
        for line in raw.splitlines():
            m_req = req_re.search(line)
            if m_req:
                # Save any previous request without a matched response
                if current_request:
                    requests.append(current_request)
                current_request = {
                    "method": m_req.group(1),
                    "url": m_req.group(2),
                    "status_code": "",
                }
                # Check if status is on the same line
                m_status = status_re.search(line)
                if m_status:
                    current_request["status_code"] = m_status.group(1)
                    requests.append(current_request)
                    current_request = None
                continue

            if current_request:
                m_status = status_re.search(line)
                if m_status:
                    current_request["status_code"] = m_status.group(1)
                    requests.append(current_request)
                    current_request = None

        # Append trailing request if any
        if current_request:
            requests.append(current_request)

        return {
            "request_count": len(requests),
            "requests": requests,
        }


ToolRegistry.register(MitmproxyTool())
