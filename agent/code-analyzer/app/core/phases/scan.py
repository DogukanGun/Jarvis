"""Phase 1: scan a repo directory and return all parseable source files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, List, Set

from app.core.languages.registry import supported_extensions

logger = logging.getLogger(__name__)

_IGNORE_DIRS: Set[str] = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".nuxt", "vendor", "third_party",
    ".gitnexus", ".cache", "coverage", ".pytest_cache", ".mypy_cache",
    "target", "out", "bin", "obj",
}

_IGNORE_EXTENSIONS: Set[str] = {
    ".min.js", ".bundle.js", ".map", ".lock", ".sum",
}

MAX_FILE_SIZE_BYTES = 1_000_000  # skip files > 1 MB


def scan_files(repo_path: str) -> List[Path]:
    """Return all source files under repo_path that have a supported language."""
    root = Path(repo_path).resolve()
    supported = set(supported_extensions())
    files: List[Path] = []

    for path in _walk(root):
        if path.suffix.lower() in supported:
            files.append(path)

    logger.info("Scan found %d source files in %s", len(files), root)
    return files


def _walk(root: Path) -> Iterator[Path]:
    try:
        entries = list(root.iterdir())
    except PermissionError:
        return

    for entry in entries:
        if entry.name.startswith(".") and entry.name not in {".gitignore"}:
            continue
        if entry.is_dir():
            if entry.name in _IGNORE_DIRS:
                continue
            yield from _walk(entry)
        elif entry.is_file():
            if entry.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            if any(entry.name.endswith(ext) for ext in _IGNORE_EXTENSIONS):
                continue
            yield entry
