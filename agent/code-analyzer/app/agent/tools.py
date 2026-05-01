"""Wrap registry BaseTool instances as LangChain StructuredTools.

Also defines two workflow tools:
  - compile_report: called when the agent has finished all analysis
  - request_confirmation: stub kept for API compatibility (not used in code analysis)
"""

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
    "file_path": str,
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


def _make_code_tool(base_tool: BaseTool) -> StructuredTool:
    meta = base_tool.metadata()
    input_model = _build_input_model(meta.name, meta.parameters)

    async def _run(**kwargs: Any) -> str:
        kwargs.pop("_noop", None)

        if not base_tool.check_available():
            return f"[UNAVAILABLE] Tool '{meta.name}' is not available."

        try:
            result = await base_tool.execute(kwargs)
            if result.error and not result.raw_output:
                return f"[ERROR] {result.error}"
            output_parts = []
            if result.raw_output:
                output_parts.append(result.raw_output)
            if result.error:
                output_parts.append(f"stderr: {result.error}")
            if result.structured_output:
                output_parts.append(json.dumps(result.structured_output, indent=2))
            return ("\n".join(output_parts) or "[no output]")[:4000]
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception.", meta.name)
            return f"[EXCEPTION] {exc}"

    return StructuredTool.from_function(
        coroutine=_run,
        name=meta.name,
        description=meta.description,
        args_schema=input_model,
    )


class CompileReportInput(BaseModel):
    findings_summary: str = Field(
        description="A concise summary of all findings and code analysis results."
    )
    tools_used: List[str] = Field(description="Names of every tool called during this session.")
    severity_notes: Optional[str] = Field(default=None, description="Any critical items to highlight.")


def _make_report_tool() -> StructuredTool:
    async def _run(
        findings_summary: str,
        tools_used: List[str],
        severity_notes: Optional[str] = None,
    ) -> str:
        report = {
            "summary": findings_summary,
            "tools_used": tools_used,
            "severity_notes": severity_notes or "",
            "status": "complete",
        }
        return json.dumps(report)

    return StructuredTool.from_function(
        coroutine=_run,
        name="compile_report",
        description=(
            "Call this tool when you have finished all code analysis and are ready "
            "to compile the final report. Pass a comprehensive summary of everything found."
        ),
        args_schema=CompileReportInput,
    )


def build_agent_tools() -> List[StructuredTool]:
    tools: List[StructuredTool] = []
    for base_tool in ToolRegistry._tools.values():
        if not base_tool.check_available():
            continue
        try:
            tools.append(_make_code_tool(base_tool))
        except Exception as exc:
            logger.warning("Failed to wrap tool '%s': %s", base_tool.metadata().name, exc)

    tools.append(_make_report_tool())
    logger.info("Built %d agent tools (%d from registry + 1 workflow).", len(tools), len(tools) - 1)
    return tools
