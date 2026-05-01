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
    def get_llm_tool_descriptions(cls) -> str:
        available = [t for t in cls._tools.values() if t.check_available()]
        if not available:
            return "No tools are currently available."
        lines: list[str] = []
        for tool in available:
            meta = tool.metadata()
            params_desc = ""
            if meta.parameters:
                param_parts: list[str] = []
                for p in meta.parameters:
                    req = "required" if p.required else "optional"
                    choices_str = f", choices={p.choices}" if p.choices else ""
                    default_str = f", default={p.default!r}" if p.default is not None else ""
                    param_parts.append(
                        f"    - {p.name} ({p.type}, {req}{default_str}{choices_str}): {p.description}"
                    )
                params_desc = "\n".join(param_parts)
            block = (
                f"[{meta.name}]\n"
                f"  Category    : {meta.category.value}\n"
                f"  Description : {meta.description}\n"
                f"  Auth Level  : {meta.auth_level.value}\n"
                f"  Capabilities: {', '.join(meta.capabilities)}\n"
            )
            if params_desc:
                block += f"  Parameters:\n{params_desc}\n"
            lines.append(block)
        return "\n".join(lines)

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
