"""GetRoutesTool — list all HTTP API routes in the indexed codebase."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class GetRoutesTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_routes",
            display_name="Get API Routes",
            category=ToolCategory.code,
            description=(
                "List all HTTP API endpoints (routes) defined in the codebase: "
                "method, path, and handler function. "
                "Supports Flask, FastAPI, Express, Gin, and similar frameworks. "
                "Requires index_repo to be called first."
            ),
            capabilities=["list api routes", "find endpoints", "route map"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(name="repo_id", type="string", required=True,
                    description="Repo ID returned by index_repo"),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import get_cached_graph

        repo_id: str = params["repo_id"]

        graph = get_cached_graph(repo_id)
        if graph is None:
            return ToolResult(tool_name="get_routes", success=False,
                error=f"Repo '{repo_id}' is not indexed. Call index_repo first.")

        routes = graph.get_routes()
        output = json.dumps(routes, indent=2)
        return ToolResult(
            tool_name="get_routes",
            success=True,
            raw_output=output[:4000],
            structured_output={"routes": routes, "count": len(routes)},
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
