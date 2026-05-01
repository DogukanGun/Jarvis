"""LangChain 1.x agent runner for the solana-strategy agent."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.agent.llm_factory import create_chat_model
from app.agent.tools import build_agent_tools

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 300

SYSTEM_PROMPT = """\
You are a disciplined trading strategy agent for the Solana ecosystem.

Your job is to analyse a user request, fetch any market data you need, run the \
appropriate technical indicators, decide whether a trade is warranted, and either \
emit a TradeIntent (via make_trade_intent) for the user to confirm, or report \
"no trade" with the reasoning.

Hard rules:
- You NEVER sign or broadcast transactions yourself. Execution is handled by the \
  trader service after the user confirms an intent.
- For any "should I buy/sell?" question, you MUST run indicator_signal on real \
  candle data (use fetch_ohlcv first if you don't already have closes).
- Bias toward conservatism: hold beats a low-confidence intent. Only emit an \
  intent when confidence ≥ 0.4.
- Be precise about position sizing — do not invent capital; use values the user \
  provides. If the user didn't specify size, ask via the report rather than \
  guessing.
- Always end the session by calling compile_report with a summary, the tools \
  you used, and any intents you emitted.
"""


def _extract_from_messages(
    messages: List[BaseMessage],
) -> tuple[str, List[str], List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    tools_used: List[str] = []
    findings: List[Dict[str, Any]] = []
    intents: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {}
    final_answer: str = ""

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        tools_used.append(name)
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
                    if isinstance(report.get("intents"), list):
                        intents = report["intents"]
                except (json.JSONDecodeError, TypeError):
                    report = {"summary": output_str, "status": "complete"}
                continue

            if tool_name == "make_trade_intent":
                # Try to lift the structured intent from the JSON dump in the body.
                try:
                    last_brace = output_str.rfind("{")
                    body = output_str[last_brace:]
                    parsed = json.loads(body)
                    if isinstance(parsed, dict) and "intent" in parsed:
                        intents.append(parsed["intent"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            findings.append({
                "type": "strategy",
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

    if not report:
        report = {
            "summary": final_answer,
            "tools_used": tools_used,
            "intents": intents,
            "total_findings": len(findings),
        }
    else:
        report.setdefault("intents", intents)
        report.setdefault("tools_used", tools_used)

    return final_answer, tools_used, findings, report, intents


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
        "intents": [],
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
        graph = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)

        try:
            result = await asyncio.wait_for(
                graph.ainvoke({"messages": [HumanMessage(content=effective_message)]}),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            base_result["error"] = f"Agent timed out after {AGENT_TIMEOUT_SECONDS}s"
            base_result["response"] = "The strategy run timed out."
            return base_result

        messages = result.get("messages", [])
        final_answer, tools_used, findings, report, intents = _extract_from_messages(messages)

        return {
            **base_result,
            "response": final_answer or report.get("summary", "Strategy run complete."),
            "tools_used": tools_used,
            "findings": findings,
            "intents": intents,
            "report": report,
        }

    except Exception as exc:
        logger.exception("Strategy agent run failed: %s", exc)
        return {
            **base_result,
            "error": str(exc),
            "response": f"Strategy run failed: {exc}",
        }
