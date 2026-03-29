"""Wrap registry BaseTool instances as LangChain StructuredTools.

Also defines two workflow tools that replace the former graph nodes:
  - compile_report: agent calls when it has finished all tool runs
  - request_confirmation: agent calls before HIGH/CRITICAL auth tools
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from app.tools.base import AuthLevel, BaseTool, ToolParameter
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema generation helpers
# ---------------------------------------------------------------------------

_PYTHON_TYPE_MAP: Dict[str, Any] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "file_path": str,
    "number": float,
}


def _build_input_model(tool_name: str, parameters: List[ToolParameter]) -> Type[BaseModel]:
    """Dynamically build a Pydantic model from a list of ToolParameter objects.

    This gives the LLM a proper JSON schema for each tool so it knows exactly
    which fields to fill in and which are required vs optional.
    """
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
        # Tool takes no parameters — provide a dummy field so Pydantic is happy
        fields["_noop"] = (
            Optional[str],
            Field(default=None, description="No parameters required."),
        )

    model_name = f"{tool_name.replace('-', '_').title()}Input"
    return create_model(model_name, **fields)


# ---------------------------------------------------------------------------
# Security tool wrapper
# ---------------------------------------------------------------------------


def _make_security_tool(base_tool: BaseTool, confirmed: bool = False) -> StructuredTool:
    """Return a LangChain StructuredTool backed by a registry BaseTool.

    Auth gating: if the tool requires HIGH or CRITICAL auth and confirmed is
    False, the tool returns a descriptive error string rather than executing.
    The agent can then call `request_confirmation` and let the caller confirm.
    """
    meta = base_tool.metadata()
    input_model = _build_input_model(meta.name, meta.parameters)

    async def _run(**kwargs: Any) -> str:
        # Strip the dummy noop field before passing to the tool
        kwargs.pop("_noop", None)

        if meta.auth_level >= AuthLevel.high and not confirmed:
            return (
                f"[AUTH_REQUIRED] Tool '{meta.name}' requires elevated authorization "
                f"(auth_level={meta.auth_level.value}). "
                "Call the `request_confirmation` tool to surface this to the user, "
                "then re-invoke once the caller confirms."
            )

        if not base_tool.check_available():
            return (
                f"[UNAVAILABLE] Tool '{meta.name}' binary is not available on this system."
            )

        # Emit tool_start so the monitor shows real-time progress
        try:
            from app.server import broadcast_event
            broadcast_event({"type": "tool_start", "tool": meta.name, "input": str(kwargs)[:500]})
        except Exception:
            pass

        try:
            result = await base_tool.execute(kwargs)
            if result.error and not result.raw_output:
                output = f"[ERROR] {result.error}"
            else:
                output_parts = []
                if result.raw_output:
                    output_parts.append(result.raw_output)
                if result.error:
                    output_parts.append(f"stderr: {result.error}")
                if result.structured_output:
                    output_parts.append(json.dumps(result.structured_output, indent=2))
                output = "\n".join(output_parts) or "[no output]"

            # Emit tool_end for monitor, cap output sent to LLM to avoid context overflow
            try:
                from app.server import broadcast_event
                broadcast_event({"type": "tool_end", "tool": meta.name, "output": output[:1000], "truncated": len(output) > 1000})
            except Exception:
                pass

            return output[:3000]
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception.", meta.name)
            try:
                from app.server import broadcast_event
                broadcast_event({"type": "tool_error", "tool": meta.name, "error": str(exc)[:300]})
            except Exception:
                pass
            return f"[EXCEPTION] {exc}"

    description = (
        f"{meta.description} "
        f"(category={meta.category.value}, auth_level={meta.auth_level.value})"
    )

    return StructuredTool.from_function(
        coroutine=_run,
        name=meta.name,
        description=description,
        args_schema=input_model,
    )


# ---------------------------------------------------------------------------
# Workflow tool: request_confirmation
# ---------------------------------------------------------------------------


class RequestConfirmationInput(BaseModel):
    tool_names: List[str] = Field(
        description="List of HIGH or CRITICAL auth-level tool names that need user approval."
    )
    purposes: List[str] = Field(
        description="Brief description of what each tool will do."
    )


def _make_confirmation_tool() -> StructuredTool:
    """Tool the agent calls before running any HIGH/CRITICAL auth-level operation.

    Returns a human-readable confirmation prompt. The actual confirmation flag
    flows in from the caller (server/kafka) — this tool is the agent's signal
    to surface the request rather than silently blocking.
    """

    async def _run(tool_names: List[str], purposes: List[str]) -> str:
        lines = [
            "CONFIRMATION REQUIRED — the following high-authorization tools are about to run:",
            "",
        ]
        for name, purpose in zip(tool_names, purposes):
            tool = ToolRegistry.get(name)
            auth = tool.metadata().auth_level.value if tool else "unknown"
            lines.append(f"  • {name} (auth_level={auth}): {purpose}")

        lines += [
            "",
            "The caller must set confirmed=True and re-submit the request to proceed.",
            "If you have already received confirmation, proceed with execution.",
        ]
        return "\n".join(lines)

    return StructuredTool.from_function(
        coroutine=_run,
        name="request_confirmation",
        description=(
            "Call this tool BEFORE using any HIGH or CRITICAL auth-level security tool. "
            "It surfaces a human-readable confirmation prompt to the operator. "
            "If the session is already confirmed, you may skip this and proceed."
        ),
        args_schema=RequestConfirmationInput,
    )


# ---------------------------------------------------------------------------
# Workflow tool: compile_report
# ---------------------------------------------------------------------------


class CompileReportInput(BaseModel):
    findings_summary: str = Field(
        description=(
            "A concise summary of all findings, tool outputs, hosts, services, "
            "vulnerabilities, and credentials discovered during this session."
        )
    )
    tools_used: List[str] = Field(
        description="Names of every tool that was called during this session."
    )
    severity_notes: Optional[str] = Field(
        default=None,
        description="Optional notes on critical or high severity items that need immediate attention.",
    )


def _make_report_tool() -> StructuredTool:
    """Tool the agent calls at the end of a session to compile a structured report.

    The agent passes a natural-language summary; this tool formats it into the
    structured dict shape the rest of the system expects.
    """

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
        # Return a JSON string so the agent can read/confirm it, then the
        # runner picks it up from intermediate_steps.
        return json.dumps(report)

    return StructuredTool.from_function(
        coroutine=_run,
        name="compile_report",
        description=(
            "Call this tool when you have finished all tool executions and are ready "
            "to produce the final security assessment report. Pass a comprehensive "
            "summary of everything found plus the list of tools used."
        ),
        args_schema=CompileReportInput,
    )


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def build_agent_tools(confirmed: bool = False) -> List[StructuredTool]:
    """Return the full list of LangChain tools for the agent.

    Includes all available registry tools (wrapped) plus the two workflow tools.

    Args:
        confirmed: Whether the current session has operator confirmation for
                   HIGH/CRITICAL auth-level tools.
    """
    tools: List[StructuredTool] = []

    for base_tool in ToolRegistry._tools.values():
        if not base_tool.check_available():
            logger.info("Skipping unavailable tool: %s", base_tool.metadata().name)
            continue
        try:
            lc_tool = _make_security_tool(base_tool, confirmed=confirmed)
            tools.append(lc_tool)
        except Exception as exc:
            logger.warning(
                "Failed to wrap tool '%s' as LangChain tool: %s",
                base_tool.metadata().name,
                exc,
            )

    tools.append(_make_confirmation_tool())
    tools.append(_make_report_tool())

    logger.info("Built %d agent tools (%d from registry + 2 workflow).", len(tools), len(tools) - 2)
    return tools
