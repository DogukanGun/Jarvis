"""GetImpactTool — blast radius analysis for a symbol."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class GetImpactTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_impact",
            display_name="Get Impact Analysis",
            category=ToolCategory.code,
            description=(
                "Find everything that would be affected if you changed a symbol. "
                "'upstream' shows who calls this symbol (blast radius). "
                "'downstream' shows what this symbol calls (dependencies). "
                "Requires index_repo to be called first."
            ),
            capabilities=["blast radius", "dependency analysis", "find callers", "impact"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(name="repo_id", type="string", required=True,
                    description="Repo ID returned by index_repo"),
                ToolParameter(name="symbol", type="string", required=True,
                    description="Function, class, or method name to analyse"),
                ToolParameter(name="direction", type="string", required=False, default="upstream",
                    choices=["upstream", "downstream"],
                    description="upstream=who calls this; downstream=what this calls"),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        from app.core.analyzer import get_cached_graph

        repo_id: str = params["repo_id"]
        symbol: str = params["symbol"]
        direction: str = params.get("direction") or "upstream"

        graph = get_cached_graph(repo_id)
        if graph is None:
            return ToolResult(tool_name="get_impact", success=False,
                error=f"Repo '{repo_id}' is not indexed. Call index_repo first.")

        result = graph.get_impact(symbol, direction=direction)
        if "error" in result:
            return ToolResult(tool_name="get_impact", success=False, error=result["error"])

        return ToolResult(
            tool_name="get_impact",
            success=True,
            raw_output=json.dumps(result, indent=2)[:4000],
            structured_output=result,
        )

    def parse_output(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}
