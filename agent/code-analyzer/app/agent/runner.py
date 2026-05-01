"""LangChain 1.x agent runner for the code-analyzer agent."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage

from app.agent.llm_factory import create_chat_model
from app.agent.tools import build_agent_tools

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 600

SYSTEM_PROMPT = """\
You are an expert code analysis agent with access to a suite of tools that build \
and query knowledge graphs from source code repositories.

Your responsibilities:
1. Analyse the user's request and decide which code analysis tools to use, in what order, \
   and with what parameters.
2. ALWAYS call index_repo first for any repo/codebase that has not yet been indexed. \
   Pass the repo_id returned by index_repo to subsequent tool calls.
3. Execute tools one at a time. After each result, reason about what you found and \
   decide whether to run more tools or conclude.
4. When you have a complete picture, call compile_report with a thorough summary.
5. Return a clear, well-structured final answer to the user.

Code analysis guidelines:
- If the user provides a GitHub URL, pass it directly to index_repo as repo_source.
- If the user asks about a local path, pass the absolute path as repo_source.
- For "what calls X?" or "who depends on X?" questions, use get_impact with direction="upstream".
- For "what does X call?" questions, use get_impact with direction="downstream".
- For "explain function X" or "show me X", use get_symbol_context.
- For "list API endpoints/routes", use get_routes.
- For general search ("find all auth code", "where is X implemented?"), use query_code.
- Never invent tool names — only use the tools available to you.
"""


def _extract_from_messages(
    messages: List[BaseMessage],
) -> tuple[str, List[str], List[Dict[str, Any]], Dict[str, Any]]:
    tools_used: List[str] = []
    findings: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {}
    final_answer: str = ""

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name: str = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if tool_name:
                        tools_used.append(tool_name)
            else:
                if isinstance(msg.content, str):
                    final_answer = msg.content
                elif isinstance(msg.content, list):
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

            findings.append({
                "type": "code_analysis",
                "tool": tool_name,
                "details": {"raw_output": output_str[:2000]},
            })

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

    if not report and findings:
        report = {
            "summary": final_answer,
            "tools_used": tools_used,
            "total_findings": len(findings),
            "findings": findings,
        }
    elif report:
        report.setdefault("findings", findings)
        report.setdefault("tools_used", tools_used)

    return final_answer, tools_used, findings, report


async def run_agent(
    user_id: str,
    message: str,
    target_tools: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    confirmed: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
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

    effective_message = message
    if target_tools:
        effective_message += f"\n\n[Constraint: only use these tools: {', '.join(target_tools)}]"
    if parameters:
        effective_message += f"\n\n[Additional context:\n{json.dumps(parameters, indent=2)}\n]"

    try:
        tools = build_agent_tools()

        if target_tools:
            workflow_names = {"compile_report"}
            tools = [t for t in tools if t.name in target_tools or t.name in workflow_names]

        llm = create_chat_model()

        graph = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        try:
            result = await asyncio.wait_for(
                graph.ainvoke({"messages": [HumanMessage(content=effective_message)]}),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            base_result["error"] = f"Agent timed out after {AGENT_TIMEOUT_SECONDS}s"
            base_result["response"] = "The analysis timed out. Try a simpler query or a smaller repo."
            return base_result

        messages = result.get("messages", [])
        final_answer, tools_used, findings, report = _extract_from_messages(messages)

        return {
            **base_result,
            "response": final_answer or report.get("summary", "Analysis complete."),
            "tools_used": tools_used,
            "findings": findings,
            "report": report,
        }

    except Exception as exc:
        logger.exception("Agent run failed: %s", exc)
        return {
            **base_result,
            "error": str(exc),
            "response": f"Code analysis failed: {exc}",
        }
