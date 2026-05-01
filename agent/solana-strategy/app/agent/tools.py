"""Wrap registry BaseTool instances as LangChain StructuredTools."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from app.tools.base import BaseTool, ToolParameter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_PYTHON_TYPE_MAP: Dict[str, Any] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
}


def _build_input_model(tool_name: str, parameters: List[ToolParameter]) -> Type[BaseModel]:
    fields: Dict[str, Any] = {}
    for p in parameters:
        python_type = _PYTHON_TYPE_MAP.get(p.type, str)
        description_parts = [p.description]
        if p.choices:
            description_parts.append(f"Choices: {p.choices}")
        if p.default is not None:
            description_parts.append(f"Default: {p.default!r}")
        full_description = " | ".join(filter(None, description_parts))

        if p.required:
            fields[p.name] = (python_type, Field(description=full_description))
        else:
            default_val = p.default if p.default is not None else None
            fields[p.name] = (
                Optional[python_type],
                Field(default=default_val, description=full_description),
            )

    if not fields:
        fields["_noop"] = (Optional[str], Field(default=None, description="No parameters required."))

    model_name = f"{tool_name.replace('-', '_').title()}Input"
    return create_model(model_name, **fields)


def _make_strategy_tool(base_tool: BaseTool) -> StructuredTool:
    meta = base_tool.metadata()
    input_model = _build_input_model(meta.name, meta.parameters)

    async def _run(**kwargs: Any) -> str:
        kwargs.pop("_noop", None)
        try:
            result = await base_tool.execute(kwargs)
            if result.error and not result.raw_output:
                return f"[ERROR] {result.error}"
            parts = []
            if result.raw_output:
                parts.append(result.raw_output)
            if result.error:
                parts.append(f"warning: {result.error}")
            if result.structured_output:
                parts.append(json.dumps(result.structured_output, indent=2))
            return ("\n".join(parts) or "[no output]")[:4000]
        except Exception as exc:
            logger.exception("Tool '%s' raised", meta.name)
            return f"[EXCEPTION] {exc}"

    return StructuredTool.from_function(
        coroutine=_run,
        name=meta.name,
        description=meta.description,
        args_schema=input_model,
    )


class CompileReportInput(BaseModel):
    findings_summary: str = Field(description="Concise summary of analysis and rationale.")
    tools_used: List[str] = Field(description="Tools called during this session.")
    intents: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Trade intents emitted, if any."
    )


def _make_report_tool() -> StructuredTool:
    async def _run(
        findings_summary: str,
        tools_used: List[str],
        intents: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        return json.dumps({
            "summary": findings_summary,
            "tools_used": tools_used,
            "intents": intents or [],
            "status": "complete",
        })

    return StructuredTool.from_function(
        coroutine=_run,
        name="compile_report",
        description=(
            "Call when you have finished strategy analysis and decided on intents (or no-op). "
            "Pass a clear summary, the tools you used, and any TradeIntents to forward to execution."
        ),
        args_schema=CompileReportInput,
    )


def build_agent_tools() -> List[StructuredTool]:
    tools: List[StructuredTool] = []
    for base_tool in ToolRegistry._tools.values():
        try:
            tools.append(_make_strategy_tool(base_tool))
        except Exception as exc:
            logger.warning("Failed to wrap tool '%s': %s", base_tool.metadata().name, exc)

    tools.append(_make_report_tool())
    return tools
