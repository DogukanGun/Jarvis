"""QueryCodeTool — text search over an indexed codebase knowledge graph."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class QueryCodeTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="query_code",
            display_name="Query Codebase",
            category=ToolCategory.code,
            description=(
                "Search the indexed codebase for functions, classes, or files matching a keyword or concept. "
                "Returns matching symbols with their file locations. "
                "Requires index_repo to be called first."
            ),
            capabilities=["search code", "find functions", "find classes", "keyword search"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(name="repo_id", type="string", required=True,
                    description="Repo ID returned by index_repo"),
                ToolParameter(name="query", type="string", required=True,
                    description="Keyword or concept to search for"),
                ToolParameter(name="limit", type="integer", required=False, default=10,
                    description="Max results to return"),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import get_cached_graph

        repo_id: str = params["repo_id"]
        query: str = params["query"]
        limit: int = int(params.get("limit") or 10)

        graph = get_cached_graph(repo_id)
        if graph is None:
            return ToolResult(tool_name="query_code", success=False,
                error=f"Repo '{repo_id}' is not indexed. Call index_repo first.")

        results = graph.search(query, limit=limit)
        output = json.dumps(results, indent=2)
        return ToolResult(
            tool_name="query_code",
            success=True,
            raw_output=output[:4000],
            structured_output={"results": results, "count": len(results)},
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
