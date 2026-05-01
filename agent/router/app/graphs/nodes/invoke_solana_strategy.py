"""Invoke the Solana Strategy agent.

Strategy emits TradeIntents but never signs/broadcasts. If `confirmed=True`
is on the inbound state and an intent comes back, this node forwards it to
the trader for execution. Otherwise the intents are returned to the user
for confirmation.
"""

import logging
from typing import Any, Dict

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_solana_strategy(state: RouterGraphState) -> Dict[str, Any]:
    from app.clients.solana_strategy_client import SolanaStrategyClient
    from app.clients.solana_trader_client import SolanaTraderClient

    message = state.get("message", "")
    user_id = state.get("user_id", "default")
    tool_args = state.get("tool_args", {})
    confirmed = bool(tool_args.get("confirmed", False))

    strategy = SolanaStrategyClient()
    try:
        result = strategy.execute(message=message, user_id=user_id, confirmed=confirmed)
    finally:
        strategy.close()

    if result.get("error"):
        logger.error("Strategy invocation failed: %s", result["error"])
        tool_results = dict(state.get("tool_results", {}))
        tool_results["solana_strategy"] = {"error": result["error"]}
        tools_used = list(state.get("tools_used", []))
        tools_used.append("solana-strategy")
        return {"tool_results": tool_results, "tools_used": tools_used}

    intents = result.get("intents", []) or []
    execution_results: list[Dict[str, Any]] = []

    if confirmed and intents:
        trader = SolanaTraderClient()
        try:
            for intent in intents:
                exec_res = trader.execute_intent({
                    "action": intent.get("action"),
                    "params": intent.get("params", {}),
                    "sourceAgent": "solana-strategy",
                })
                execution_results.append(exec_res)
        finally:
            trader.close()

    tools_used = list(state.get("tools_used", []))
    tools_used.append("solana-strategy")

    tool_results = dict(state.get("tool_results", {}))
    tool_results["solana_strategy"] = {
        "response": result.get("response", ""),
        "tools_used": result.get("tools_used", []),
        "findings": result.get("findings", []),
        "report": result.get("report", {}),
        "intents": intents,
        "execution_results": execution_results,
    }

    return {
        "tool_results": tool_results,
        "tools_used": tools_used,
        "response": result.get("response", ""),
        "findings": result.get("findings", []),
        "report": result.get("report", {}),
    }
