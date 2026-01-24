import re
import shutil
import subprocess
from typing import Sequence


def _run_cmd(cmd: Sequence[str], timeout_s: int = 30) -> str:
    """
    Run command safely (no shell), return combined output.
    """
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        out = out.strip()
        # Keep outputs reasonably sized
        if len(out) > 8000:
            out = out[:8000] + "\n...[truncated]..."
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"(command timed out after {timeout_s}s)"

def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise FileNotFoundError(
            f"Required binary '{name}' not found on PATH. Install it first."
        )

def _looks_like_domain(s: str) -> bool:
    # Very light domain check; avoids treating "10.0.0.1" as a domain.
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", s):
        return False
    if ":" in s:  # likely IPv6 literal
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", s))
