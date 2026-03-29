"""LangChain 1.x agent runner — uses create_agent (LangGraph-backed).

The old AgentExecutor + create_tool_calling_agent API was removed in
LangChain 1.0.  This module replaces it with the new ``create_agent``
function which returns a compiled LangGraph.

The public entry-point ``run_agent()`` keeps the same signature and
return-dict shape so ``server.py`` and ``kafka/consumer.py`` need zero changes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage

from app.agent.callbacks import AgentProgressCallbackHandler
from app.agent.llm_factory import create_chat_model
from app.agent.tools import build_agent_tools

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 600  # 10 minutes — tools now bounded so agent can actually complete

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert security and network operations agent with access to a suite \
of professional penetration testing and monitoring tools.

Your responsibilities:
1. Analyse the operator's request and decide which tools to use, in what order, \
   and with what parameters.
2. Execute tools one at a time. After each result, reason about what you found \
   and decide whether to run more tools or conclude.
3. For any tool with auth_level=high or auth_level=critical, ALWAYS call \
   `request_confirmation` first — unless the session is already confirmed.
4. When you have finished all tool runs and have a complete picture, call \
   `compile_report` with a thorough summary of your findings.
5. Return a concise final answer to the operator after the report is compiled.

Network scanning rules:
- ALWAYS start with scapy(action="get_local_network") when the operator asks to \
  scan, discover hosts, or check the network WITHOUT specifying an explicit target. \
  Use the returned "primary_network" CIDR as the target for the subsequent ARP scan. \
  Do NOT guess ranges like 192.168.1.0/24 or 10.0.0.0/24 — the real network may differ.
- If the operator supplies a specific target (IP or CIDR), use it directly.

Security guidelines:
- Only use tools that are relevant to the stated task.
- Prefer low-auth tools (reconnaissance, scanning) before high-auth tools.
- Never invent tool names — only use the tools available to you.
- If a tool is unavailable or returns an error, note it and adapt your approach.
"""

# ---------------------------------------------------------------------------
# Result extraction helpers
# ---------------------------------------------------------------------------


def _extract_from_messages(
    messages: List[BaseMessage],
) -> tuple[str, List[str], List[Dict[str, Any]], Dict[str, Any]]:
    """Parse LangGraph message list into (final_answer, tools_used, findings, report).

    Message structure from create_agent:
      HumanMessage  → user input
      AIMessage(tool_calls=[...])  → agent decided to call tools
      ToolMessage   → tool result
      AIMessage(content=..., tool_calls=[])  → final answer
    """
    tools_used: List[str] = []
    findings: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {}
    final_answer: str = ""

    for msg in messages:
        if isinstance(msg, AIMessage):
            # Collect tool calls the agent made
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name: str = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if tool_name:
                        tools_used.append(tool_name)
            else:
                # No tool calls → this is the final answer
                if isinstance(msg.content, str):
                    final_answer = msg.content
                elif isinstance(msg.content, list):
                    # Content might be a list of blocks in newer models
                    final_answer = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in msg.content
                    )

        elif isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", "") or ""
            output_str = str(msg.content)

            if tool_name == "compile_report":
                try:
                    report = json.loads(output_str)
                except (json.JSONDecodeError, TypeError):
                    report = {"summary": output_str, "status": "complete"}
                continue

            if tool_name == "request_confirmation":
                continue  # workflow tool, not a security finding

            if output_str.startswith("[AUTH_REQUIRED]"):
                findings.append({
                    "type": "info",
                    "severity": "info",
                    "description": f"Tool '{tool_name}' blocked — confirmation required.",
                    "details": {"raw": output_str},
                })
            elif output_str.startswith("[UNAVAILABLE]"):
                findings.append({
                    "type": "info",
                    "severity": "info",
                    "description": f"Tool '{tool_name}' is not available on this system.",
                    "details": {"raw": output_str},
                })
            elif output_str.startswith("[ERROR]") or output_str.startswith("[EXCEPTION]"):
                findings.append({
                    "type": "info",
                    "severity": "low",
                    "description": f"Tool '{tool_name}' returned an error.",
                    "details": {"raw": output_str},
                })
            else:
                findings.append({
                    "type": "info",
                    "severity": "info",
                    "description": f"Output from '{tool_name}'",
                    "details": {"raw_output": output_str[:2000]},
                })

    # If no explicit final answer was found, use the last AIMessage content
    if not final_answer:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, str) and content:
                    final_answer = content
                    break
                elif isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in content
                    ).strip()
                    if text:
                        final_answer = text
                        break

    # If the agent compiled a report but it's missing some fields, fill them in
    if not report and findings:
        findings_by_severity: Dict[str, list] = defaultdict(list)
        for f in findings:
            findings_by_severity[f.get("severity", "info")].append(f)
        report = {
            "summary": final_answer,
            "tools_used": tools_used,
            "total_findings": len(findings),
            "findings_by_severity": dict(findings_by_severity),
            "findings": findings,
        }
    elif report:
        report.setdefault("findings", findings)
        report.setdefault("tools_used", tools_used)
        report.setdefault("total_findings", len(findings))

    return final_answer, tools_used, findings, report


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_agent(
    user_id: str,
    message: str,
    target_tools: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    confirmed: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the LangChain 1.x agent for the given task and return the final state dict.

    Returned dict keys (same as before):
        response, report, tools_used, findings, requires_confirmation,
        confirmation_prompt, error, job_id, user_id, message
    """
    # Signal that agent execution has actually started (visible in monitor)
    if job_id:
        try:
            from app.server import broadcast_event
            broadcast_event({"type": "agent_started", "job_id": job_id, "message": message[:200]})
        except Exception:
            pass

    base_result: Dict[str, Any] = {
        "user_id": user_id,
        "message": message,
        "job_id": job_id,
        "requires_confirmation": False,
        "confirmation_prompt": "",
        "confirmed": confirmed,
        "tools_used": [],
        "findings": [],
        "report": {},
        "response": "",
        "error": None,
    }

    # Build effective message
    effective_message = message
    if target_tools:
        effective_message += (
            f"\n\n[Operator constraint: only use these tools: {', '.join(target_tools)}]"
        )
    if parameters:
        param_str = json.dumps(parameters, indent=2)
        effective_message += f"\n\n[Additional context/parameters:\n{param_str}\n]"

    try:
        tools = build_agent_tools(confirmed=confirmed)

        # Filter to target_tools if specified (keep workflow tools always)
        if target_tools:
            workflow_names = {"compile_report", "request_confirmation"}
            tools = [
                t for t in tools
                if t.name in target_tools or t.name in workflow_names
            ]

        llm = create_chat_model()

        callbacks = [AgentProgressCallbackHandler(job_id=job_id or "")]

        # LangChain 1.x: create_agent returns a compiled LangGraph
        graph = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        try:
            result = await asyncio.wait_for(
                graph.ainvoke(
                    {"messages": [HumanMessage(content=effective_message)]},
                    config={"callbacks": callbacks},
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Agent timed out after {AGENT_TIMEOUT_SECONDS}s. "
                "The LLM did not respond in time. Check LLM connectivity and API keys."
            )

        messages: List[BaseMessage] = result.get("messages", [])
        final_answer, tools_used, findings, report = _extract_from_messages(messages)

        if not final_answer:
            final_answer = "Security analysis complete. See findings for details."

        # Check if any tool was blocked on confirmation
        auth_blocked = any(
            f["description"].startswith("Tool '") and "confirmation required" in f["description"]
            for f in findings
        )
        confirmation_prompt = ""
        if auth_blocked and not confirmed:
            blocked = [
                f["description"].split("'")[1]
                for f in findings
                if "confirmation required" in f.get("description", "")
            ]
            confirmation_prompt = (
                "The following tools require operator confirmation before execution:\n"
                + "\n".join(f"  • {t}" for t in blocked)
            )

        return {
            **base_result,
            "response": final_answer,
            "report": report,
            "tools_used": tools_used,
            "findings": findings,
            "requires_confirmation": auth_blocked and not confirmed,
            "confirmation_prompt": confirmation_prompt,
        }

    except Exception as exc:
        logger.exception("Agent execution failed: %s", exc)
        return {
            **base_result,
            "error": str(exc),
            "response": f"Execution failed: {exc}",
        }
