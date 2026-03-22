"""John the Ripper password cracker wrapper."""

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

_ACTIONS = ["crack", "show", "status"]


class JohnTool(BaseTool):
    """Wrapper around John the Ripper for password hash cracking.

    Supports wordlist attacks, rule-based mangling, brute-force, and
    a wide variety of hash formats (md5crypt, sha512crypt, NTLM, etc.).
    """

    def __init__(self) -> None:
        self._executor = SubprocessExecutor()

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="john",
            display_name="John the Ripper",
            category=ToolCategory.password,
            description=(
                "Password cracker supporting many hash types. Cracks "
                "password hashes using wordlists, rules, and brute force."
            ),
            capabilities=[
                "password_crack",
                "hash_identify",
                "wordlist_attack",
                "brute_force",
            ],
            auth_level=AuthLevel.medium,
            parameters=[
                ToolParameter(
                    name="hash_file",
                    type="string",
                    required=True,
                    description="Path to the file containing password hashes.",
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    required=False,
                    default="crack",
                    choices=_ACTIONS,
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="wordlist",
                    type="string",
                    required=False,
                    default="/usr/share/wordlists/rockyou.txt",
                    description="Path to the wordlist for dictionary attacks.",
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    required=False,
                    description="Hash format hint (e.g. raw-md5, nt, sha512crypt).",
                ),
                ToolParameter(
                    name="rules",
                    type="string",
                    required=False,
                    description="Mangling rules section name (e.g. Jumbo, Best64).",
                ),
            ],
            binary_path="/usr/sbin/john",
            estimated_duration="minutes",
        )

    # ------------------------------------------------------------------ #
    #  Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        hash_file: str = params["hash_file"]
        action: str = params.get("action", "crack")
        wordlist: str = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        fmt: str | None = params.get("format")
        rules: str | None = params.get("rules")

        if action == "crack":
            cmd = ["john", f"--wordlist={wordlist}"]
            if fmt:
                cmd.append(f"--format={fmt}")
            if rules:
                cmd.append(f"--rules={rules}")
            cmd.append(hash_file)
            result = await self._executor.execute(cmd, timeout=600)

        elif action == "show":
            cmd = ["john", "--show", hash_file]
            if fmt:
                cmd.append(f"--format={fmt}")
            result = await self._executor.execute(cmd, timeout=30)

        elif action == "status":
            cmd = ["john", "--status"]
            result = await self._executor.execute(cmd, timeout=15)

        else:
            return ToolResult(
                tool_name="john",
                success=False,
                error=f"Unknown action '{action}'. Valid actions: {_ACTIONS}",
            )

        result.tool_name = "john"
        result.structured_output = self.parse_output(result.raw_output)
        return result

    # ------------------------------------------------------------------ #
    #  Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Extract cracked credentials and session statistics from john output."""
        parsed: Dict[str, Any] = {}

        # --- Cracked passwords from --show -------------------------------- #
        # john --show outputs lines like:  user:password
        cracked: List[Dict[str, str]] = []
        for line in raw.splitlines():
            # Skip summary / blank lines
            stripped = line.strip()
            if not stripped or stripped.startswith("(") or "password hash" in stripped.lower():
                continue
            # Lines with at least one colon are credential pairs
            if ":" in stripped:
                parts = stripped.split(":", 1)
                cracked.append({
                    "user": parts[0],
                    "password": parts[1],
                })

        if cracked:
            parsed["cracked"] = cracked

        # --- Summary line: "N password hashes cracked, M left" ------------ #
        summary_match = re.search(
            r"(\d+)\s+password\s+hash(?:es)?\s+cracked.*?(\d+)\s+left",
            raw,
            re.IGNORECASE,
        )
        if summary_match:
            parsed["cracked_count"] = int(summary_match.group(1))
            parsed["remaining_count"] = int(summary_match.group(2))
        else:
            cracked_only = re.search(
                r"(\d+)\s+password\s+hash(?:es)?\s+cracked",
                raw,
                re.IGNORECASE,
            )
            if cracked_only:
                parsed["cracked_count"] = int(cracked_only.group(1))

        # --- Session status ----------------------------------------------- #
        guesses_match = re.search(r"(\d+)g\s", raw)
        if guesses_match:
            parsed["guesses"] = int(guesses_match.group(1))

        speed_match = re.search(r"(\d+(?:\.\d+)?)\s*[kKmMgG]?p/s", raw)
        if speed_match:
            parsed["speed"] = speed_match.group(0)

        return parsed


# Auto-register
ToolRegistry.register(JohnTool())
