"""Direct invocation of the Solana Trader (read-only or pre-confirmed actions).

Used for things like portfolio queries, price lookups, and explicit single-shot
trade requests where the strategy layer isn't needed.
"""

import logging
from typing import Any, Dict

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_solana_trader(state: RouterGraphState) -> Dict[str, Any]:
    from app.clients.solana_trader_client import SolanaTraderClient

    tool_args = state.get("tool_args", {}) or {}
    op = str(tool_args.get("op", "balance"))

    client = SolanaTraderClient()
    out: Dict[str, Any]
    try:
        if op == "balance":
            out = client.balance()
        elif op == "swap":
            out = client.swap(tool_args.get("params", {}))
        elif op == "transfer":
            out = client.transfer(tool_args.get("params", {}))
        elif op == "price":
            out = client.price(str(tool_args.get("token", "")))
        elif op == "token_info":
            out = client.token_info(str(tool_args.get("mint", "")))
        else:
            out = {"error": f"unknown op: {op}"}
    finally:
        client.close()

    tool_results = dict(state.get("tool_results", {}))
    tool_results["solana_trader"] = out
    tools_used = list(state.get("tools_used", []))
    tools_used.append("solana-trader")

    response = ""
    if out.get("error"):
        response = f"Trader error: {out['error']}"
    elif op == "balance" and out.get("sol") is not None:
        response = f"Wallet {out.get('publicKey', '')} on {out.get('network', '?')}: {out['sol']} SOL"
    elif out.get("signature"):
        response = f"Executed {op}. tx: {out['signature']}"
    elif out.get("price") is not None:
        response = f"Price: {out['price']}"

    return {
        "tool_results": tool_results,
        "tools_used": tools_used,
        "response": response,
    }
