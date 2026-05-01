"""VisualizeGraphTool — open an interactive D3.js force-directed graph in Jarvis."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from app.config import config


class VisualizeGraphTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="visualize_graph",
            display_name="Visualize Knowledge Graph",
            category=ToolCategory.code,
            description=(
                "Open an interactive visual map of the codebase knowledge graph. "
                "Shows nodes (files, functions, classes, routes) and edges (calls, imports, inherits) "
                "as a force-directed graph with zoom, pan, hover tooltips, and click-to-highlight. "
                "Requires index_repo to be called first."
            ),
            capabilities=["visualize graph", "show code map", "graph explorer"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="repo_id",
                    type="string",
                    required=True,
                    description="Repo ID returned by index_repo",
                ),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import get_cached_graph

        repo_id: str = params["repo_id"]

        graph = get_cached_graph(repo_id)
        if graph is None:
            return ToolResult(
                tool_name="visualize_graph",
                success=False,
                error=f"Repo '{repo_id}' is not indexed. Call index_repo first.",
            )

        url = f"http://localhost:{config.PORT}/api/repos/{repo_id}/visualize"
        return ToolResult(
            tool_name="visualize_graph",
            success=True,
            raw_output=(
                f"Knowledge graph visualization ready for '{repo_id}'.\n"
                f"Visualization URL: {url}\n"
                f"Graph contains {graph.node_count} nodes and {graph.edge_count} edges."
            ),
            structured_output={"viz_url": url, "repo_id": repo_id},
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
