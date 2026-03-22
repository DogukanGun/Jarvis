"""Lynis security auditing tool wrapper for Unix-based systems."""

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


class LynisTool(BaseTool):
    """Security auditing and hardening assessment via Lynis.

    Performs comprehensive system audits, extracts warnings and
    suggestions, and reports the overall hardening index for
    Unix-based hosts.
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="lynis",
            display_name="Lynis",
            category=ToolCategory.monitoring,
            description=(
                "Security auditing tool for Unix-based systems. Performs "
                "system hardening checks and compliance tests."
            ),
            capabilities=[
                "security_audit",
                "hardening_check",
                "compliance_test",
                "vulnerability_scan",
            ],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=False,
                    default="audit",
                    choices=["audit", "show_details", "show_warnings"],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="profile",
                    type="string",
                    required=False,
                    description="Path to a custom Lynis profile file.",
                ),
                ToolParameter(
                    name="tests_category",
                    type="string",
                    required=False,
                    description="Run only tests from this category (e.g. malware, authentication).",
                ),
                ToolParameter(
                    name="quick",
                    type="boolean",
                    required=False,
                    default=False,
                    description="Enable quick mode (skip prompts and delays).",
                ),
            ],
            binary_path="/opt/lynis/lynis",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params.get("action", "audit")
        profile: str | None = params.get("profile")
        tests_category: str | None = params.get("tests_category")
        quick: bool = params.get("quick", False)

        if action == "audit":
            return await self._audit(profile, tests_category, quick)
        elif action == "show_details":
            return await self._show_details()
        elif action == "show_warnings":
            return await self._show_warnings()
        else:
            return ToolResult(
                tool_name="lynis",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: audit, show_details, show_warnings.",
            )

    async def _audit(
        self,
        profile: str | None,
        tests_category: str | None,
        quick: bool,
    ) -> ToolResult:
        """Run a full Lynis system audit."""
        cmd: List[str] = ["/opt/lynis/lynis", "audit", "system", "--no-colors"]

        if quick:
            cmd.append("--quick")

        if profile:
            cmd += ["--profile", profile]

        if tests_category:
            cmd += ["--tests-from-group", tests_category]

        result = await self._executor.execute(cmd, timeout=600)
        result.tool_name = "lynis"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    async def _show_details(self) -> ToolResult:
        """Show detailed test results from the last audit."""
        cmd: List[str] = ["/opt/lynis/lynis", "show", "details"]
        result = await self._executor.execute(cmd, timeout=30)
        result.tool_name = "lynis"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    async def _show_warnings(self) -> ToolResult:
        """Show warnings from the last audit."""
        cmd: List[str] = ["/opt/lynis/lynis", "show", "warnings"]
        result = await self._executor.execute(cmd, timeout=30)
        result.tool_name = "lynis"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Parse Lynis audit output for warnings, suggestions, and hardening index."""
        parsed: Dict[str, Any] = {}

        # Extract hardening index
        hardening_re = re.compile(
            r"Hardening\s+index\s*:\s*(\d+)", re.IGNORECASE
        )
        hardening_match = hardening_re.search(raw)
        if hardening_match:
            parsed["hardening_index"] = int(hardening_match.group(1))

        # Extract warnings
        warnings: List[Dict[str, str]] = []
        warning_re = re.compile(
            r"Warning:\s+(.+?)(?:\s+\[([A-Z]+-\d+)\])?\s*$", re.MULTILINE
        )
        for m in warning_re.finditer(raw):
            entry: Dict[str, str] = {"message": m.group(1).strip()}
            if m.group(2):
                entry["test_id"] = m.group(2)
            warnings.append(entry)
        if warnings:
            parsed["warnings"] = warnings
            parsed["warning_count"] = len(warnings)

        # Extract suggestions
        suggestions: List[Dict[str, str]] = []
        suggestion_re = re.compile(
            r"Suggestion:\s+(.+?)(?:\s+\[([A-Z]+-\d+)\])?\s*$", re.MULTILINE
        )
        for m in suggestion_re.finditer(raw):
            entry = {"message": m.group(1).strip()}
            if m.group(2):
                entry["test_id"] = m.group(2)
            suggestions.append(entry)
        if suggestions:
            parsed["suggestions"] = suggestions
            parsed["suggestion_count"] = len(suggestions)

        # Extract test counts
        tests_re = re.compile(r"Tests\s+performed\s*:\s*(\d+)", re.IGNORECASE)
        tests_match = tests_re.search(raw)
        if tests_match:
            parsed["tests_performed"] = int(tests_match.group(1))

        # Extract compliance status
        compliance_re = re.compile(
            r"Compliance\s+status\s*:\s*(.+)", re.IGNORECASE
        )
        compliance_match = compliance_re.search(raw)
        if compliance_match:
            parsed["compliance_status"] = compliance_match.group(1).strip()

        # Extract plugin results
        plugins_re = re.compile(r"Plugins\s+enabled\s*:\s*(\d+)", re.IGNORECASE)
        plugins_match = plugins_re.search(raw)
        if plugins_match:
            parsed["plugins_enabled"] = int(plugins_match.group(1))

        return parsed


# Auto-register
ToolRegistry.register(LynisTool())
