"""IndexRepoTool — clone and analyze a GitHub repo or local path."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from app.config import config
from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


def _derive_repo_id(source: str) -> str:
    parts = source.rstrip("/").split("/")
    if source.startswith("http") and len(parts) >= 2:
        return f"{parts[-2]}__{parts[-1].removesuffix('.git')}"
    name = Path(source).name
    suffix = hashlib.md5(source.encode()).hexdigest()[:6]
    return f"{name}__{suffix}"


async def _clone(url: str, target: Path) -> None:
    if target.exists():
        proc = await asyncio.create_subprocess_exec(
            "git", "fetch", "--depth=1", cwd=str(target),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth=1", url, str(target),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {stderr.decode()}")


class IndexRepoTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="index_repo",
            display_name="Index Repository",
            category=ToolCategory.code,
            description=(
                "Clone and analyze a GitHub repository or local path to build a knowledge graph "
                "of its code structure (functions, classes, call graph, imports). "
                "Call this FIRST before using any other code analysis tool. "
                "Returns a repo_id to pass to the other tools."
            ),
            capabilities=["clone repo", "build knowledge graph", "analyze code structure"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="repo_source",
                    type="string",
                    required=True,
                    description="GitHub URL (https://github.com/owner/repo) or absolute local path",
                ),
                ToolParameter(
                    name="repo_id",
                    type="string",
                    required=False,
                    description="Stable ID for this repo (auto-derived from URL/path if omitted)",
                ),
            ],
            is_long_running=True,
            estimated_duration="10-120 seconds depending on repo size",
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import analyze_repo, get_cached_graph

        source: str = params["repo_source"]
        repo_id: str = params.get("repo_id") or _derive_repo_id(source)

        # Fast path: already in cache
        if get_cached_graph(repo_id) is not None:
            return ToolResult(
                tool_name="index_repo",
                success=True,
                raw_output=f"Repo '{repo_id}' is already indexed. Use this repo_id with the other tools.",
                structured_output={"repo_id": repo_id, "status": "ready"},
            )

        # Resolve local path (clone if GitHub URL)
        if source.startswith("http"):
            cache_dir = Path(config.REPO_CACHE_DIR)
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / repo_id
            try:
                await _clone(source, target)
            except RuntimeError as e:
                return ToolResult(tool_name="index_repo", success=False, error=str(e))
            repo_path = str(target)
        else:
            if not Path(source).exists():
                return ToolResult(
                    tool_name="index_repo", success=False,
                    error=f"Local path does not exist: {source}",
                )
            repo_path = source

        # Build knowledge graph
        try:
            graph = await analyze_repo(repo_path, repo_id)
        except Exception as e:
            logger.exception("Analysis failed for %s", repo_path)
            return ToolResult(tool_name="index_repo", success=False, error=str(e))

        return ToolResult(
            tool_name="index_repo",
            success=True,
            raw_output=(
                f"Repo '{repo_id}' indexed successfully.\n"
                f"Knowledge graph: {graph.node_count} nodes, {graph.edge_count} edges.\n"
                f"Now use repo_id='{repo_id}' with query_code, get_symbol_context, get_impact, or get_routes."
            ),
            structured_output={
                "repo_id": repo_id,
                "repo_path": repo_path,
                "nodes": graph.node_count,
                "edges": graph.edge_count,
            },
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
