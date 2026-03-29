"""Executor classes for running subprocesses and Python callables."""

import asyncio
import time
from typing import Callable, Dict, List, Optional

from app.tools.base import ToolResult


class SubprocessExecutor:
    """Executes shell commands as async subprocesses with timeout and output capture."""

    async def execute(
        self,
        cmd: List[str],
        timeout: int = 60,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        """Run a command via asyncio subprocess with enforced timeout.

        Args:
            cmd: Command and arguments as a list of strings.
            timeout: Maximum seconds to wait before killing the process.
            cwd: Working directory for the subprocess.
            env: Environment variables for the subprocess.

        Returns:
            ToolResult with stdout+stderr as raw_output, exit code, and timing.
        """
        start = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration_ms = int((time.monotonic() - start) * 1000)
                return ToolResult(
                    exit_code=-1,
                    raw_output="",
                    success=False,
                    error=f"Command timed out after {timeout}s",
                    duration_ms=duration_ms,
                )

            duration_ms = int((time.monotonic() - start) * 1000)
            raw_output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).rstrip()
            exit_code = process.returncode

            return ToolResult(
                exit_code=exit_code,
                raw_output=raw_output,
                success=(exit_code == 0),
                error=None if exit_code == 0 else f"Process exited with code {exit_code}",
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                exit_code=-1,
                raw_output="",
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )


class PythonExecutor:
    """Executes Python callables in a thread pool with error handling."""

    async def execute(
        self,
        func: Callable,
        *args,
        timeout: int = 180,
        **kwargs,
    ) -> ToolResult:
        """Run a synchronous callable on a background thread.

        Args:
            func: The callable to execute.
            *args: Positional arguments forwarded to *func*.
            timeout: Maximum seconds to wait before returning a timeout error.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            ToolResult with the stringified return value as raw_output.
        """
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=timeout,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                exit_code=0,
                raw_output=str(result),
                success=True,
                error=None,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                exit_code=-1,
                raw_output="",
                success=False,
                error=f"Tool timed out after {timeout}s",
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(
                exit_code=1,
                raw_output="",
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )
