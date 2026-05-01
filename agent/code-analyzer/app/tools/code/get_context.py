"""GetContextTool — 360° view of a symbol: callers, callees, location."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class GetContextTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_symbol_context",
            display_name="Get Symbol Context",
            category=ToolCategory.code,
            description=(
                "Get a full view of a function, class, or method: "
                "where it is defined, who calls it, what it calls, and what it imports. "
                "Requires index_repo to be called first."
            ),
            capabilities=["symbol context", "call graph", "find callers", "find callees"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(name="repo_id", type="string", required=True,
                    description="Repo ID returned by index_repo"),
                ToolParameter(name="symbol", type="string", required=True,
                    description="Name of the function, class, or method"),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import get_cached_graph

        repo_id: str = params["repo_id"]
        symbol: str = params["symbol"]

        graph = get_cached_graph(repo_id)
        if graph is None:
            return ToolResult(tool_name="get_symbol_context", success=False,
                error=f"Repo '{repo_id}' is not indexed. Call index_repo first.")

        result = graph.get_context(symbol)
        if "error" in result:
            return ToolResult(tool_name="get_symbol_context", success=False, error=result["error"])

        return ToolResult(
            tool_name="get_symbol_context",
            success=True,
            raw_output=json.dumps(result, indent=2)[:4000],
            structured_output=result,
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
