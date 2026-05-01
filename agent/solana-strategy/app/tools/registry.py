from __future__ import annotations

from typing import Dict, List, Optional

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata


class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools[tool.metadata().name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[ToolMetadata]:
        return [tool.metadata() for tool in cls._tools.values()]

    @classmethod
    def find_by_category(cls, category: ToolCategory) -> List[BaseTool]:
        return [t for t in cls._tools.values() if t.metadata().category == category]

    @classmethod
    def available_tools(cls) -> List[ToolMetadata]:
        return [t.metadata() for t in cls._tools.values() if t.check_available()]

    @classmethod
    def get_max_auth_level(cls, tool_names: List[str]) -> AuthLevel:
        max_level = AuthLevel.low
        for name in tool_names:
            tool = cls._tools.get(name)
            if tool is not None:
                level = tool.metadata().auth_level
                if level > max_level:
                    max_level = level
        return max_level
