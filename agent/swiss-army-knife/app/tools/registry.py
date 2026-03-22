from __future__ import annotations

from typing import Dict, List, Optional

from app.tools.base import AuthLevel, BaseTool, ToolCategory, ToolMetadata


class ToolRegistry:
    """Singleton registry that holds all tool instances.

    Interaction happens exclusively through class methods so there is never a
    need to instantiate this class.
    """

    _tools: Dict[str, BaseTool] = {}

    # ---- mutation -------------------------------------------------------- #

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """Register a tool using its ``metadata().name`` as the key."""
        cls._tools[tool.metadata().name] = tool

    # ---- lookup ---------------------------------------------------------- #

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """Return the tool registered under *name*, or ``None``."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[ToolMetadata]:
        """Return metadata for every registered tool."""
        return [tool.metadata() for tool in cls._tools.values()]

    @classmethod
    def find_by_capability(cls, capability: str) -> List[BaseTool]:
        """Return all tools whose capabilities list contains *capability*."""
        cap_lower = capability.lower()
        return [
            tool
            for tool in cls._tools.values()
            if any(cap_lower in c.lower() for c in tool.metadata().capabilities)
        ]

    @classmethod
    def find_by_category(cls, category: ToolCategory) -> List[BaseTool]:
        """Return all tools that belong to *category*."""
        return [
            tool
            for tool in cls._tools.values()
            if tool.metadata().category == category
        ]

    @classmethod
    def available_tools(cls) -> List[ToolMetadata]:
        """Return metadata only for tools whose binary is available."""
        return [
            tool.metadata()
            for tool in cls._tools.values()
            if tool.check_available()
        ]

    # ---- LLM helpers ----------------------------------------------------- #

    @classmethod
    def get_llm_tool_descriptions(cls) -> str:
        """Format every available tool into a prompt-ready catalog string."""
        available = [
            tool for tool in cls._tools.values() if tool.check_available()
        ]
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
                    choices_str = (
                        f", choices={p.choices}" if p.choices else ""
                    )
                    default_str = (
                        f", default={p.default!r}"
                        if p.default is not None
                        else ""
                    )
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
        """Return the highest ``AuthLevel`` among the named tools.

        Tools that are not found in the registry are silently ignored.  If none
        of the names resolve to a registered tool, ``AuthLevel.low`` is
        returned as a safe default.
        """
        max_level = AuthLevel.low
        for name in tool_names:
            tool = cls._tools.get(name)
            if tool is not None:
                level = tool.metadata().auth_level
                if level > max_level:
                    max_level = level
        return max_level
