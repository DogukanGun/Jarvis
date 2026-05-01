"""Watch a target wallet for recent Jupiter swaps to copy.

Approach (clean-room rewrite of imcrazysteven/Solana-Copy-Trading-Bot — MIT):
1. Poll `getSignaturesForAddress` to get the most recent N tx signatures for the wallet.
2. For each unseen sig, fetch the parsed transaction.
3. Look for Jupiter aggregator program-id involvement; pull the SOL → SPL leg
   from token balances pre/post (the wallet's SPL balance increases for the
   bought mint, SOL decreases for the spent amount).

This is a polling implementation — fine for hackathon speed. Production code
would use Helius webhooks / Geyser stream for sub-second latency.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = logging.getLogger(__name__)

# Jupiter v6 swap program. (v4 was JUP4Fb..., v6 is JUP6Lk...).
JUPITER_PROGRAM_IDS = {
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",  # v6
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",  # v4 (older)
}
WSOL = "So11111111111111111111111111111111111111112"


def _rpc_url() -> str:
    return os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")


async def _rpc(method: str, params: List[Any]) -> Dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(_rpc_url(), json=payload)
        r.raise_for_status()
        return r.json()


async def recent_jupiter_swaps(target: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of detected Jupiter swaps for `target`, newest first.

    Each swap dict has: signature, slot, output_mint, in_amount_sol,
    out_amount_raw (raw token units), out_decimals.
    """
    sigs_resp = await _rpc("getSignaturesForAddress", [target, {"limit": limit}])
    sigs = sigs_resp.get("result", []) or []

    out: List[Dict[str, Any]] = []
    for entry in sigs:
        sig = entry.get("signature")
        if not sig or entry.get("err"):
            continue
        try:
            tx = await _rpc(
                "getTransaction",
                [sig, {"maxSupportedTransactionVersion": 0, "encoding": "jsonParsed"}],
            )
            result = tx.get("result")
            if not result:
                continue
            parsed = _extract_jupiter_swap(target, result)
            if parsed:
                parsed["signature"] = sig
                parsed["slot"] = result.get("slot")
                out.append(parsed)
        except Exception as e:  # noqa: BLE001
            logger.debug("copy_trade getTransaction failed for %s: %s", sig, e)
            continue
    return out


def _extract_jupiter_swap(target: str, tx: Dict[str, Any]) -> Dict[str, Any] | None:
    """Pull (output_mint, in_sol, out_amount) from a parsed tx if it touches Jupiter."""
    msg = tx.get("transaction", {}).get("message", {}) or {}
    instructions = msg.get("instructions", []) or []
    inner = (tx.get("meta", {}).get("innerInstructions", []) or [])
    program_ids: List[str] = []
    for ix in instructions:
        pid = ix.get("programId")
        if pid:
            program_ids.append(pid)
    for group in inner:
        for ix in group.get("instructions", []) or []:
            pid = ix.get("programId")
            if pid:
                program_ids.append(pid)
    if not any(pid in JUPITER_PROGRAM_IDS for pid in program_ids):
        return None

    meta = tx.get("meta") or {}
    pre_token = meta.get("preTokenBalances") or []
    post_token = meta.get("postTokenBalances") or []
    pre_sol = (meta.get("preBalances") or [None])
    post_sol = (meta.get("postBalances") or [None])

    # Find the target's SPL balance delta — the largest positive change is the buy.
    # Account keys are at message.accountKeys.
    keys = msg.get("accountKeys", []) or []
    target_idx = None
    for i, k in enumerate(keys):
        kp = k.get("pubkey") if isinstance(k, dict) else k
        if kp == target:
            target_idx = i
            break

    in_amount_sol = 0.0
    if target_idx is not None and target_idx < len(pre_sol) and target_idx < len(post_sol):
        delta_lamports = int(pre_sol[target_idx]) - int(post_sol[target_idx])
        if delta_lamports > 0:
            in_amount_sol = delta_lamports / 1_000_000_000

    output_mint = None
    out_amount_raw = 0
    out_decimals = 0
    best_delta = 0.0
    for post in post_token:
        if post.get("owner") != target:
            continue
        mint = post.get("mint")
        if not mint or mint == WSOL:
            continue
        post_amt = float(post.get("uiTokenAmount", {}).get("uiAmount") or 0)
        pre_amt = 0.0
        for pre in pre_token:
            if pre.get("owner") == target and pre.get("mint") == mint:
                pre_amt = float(pre.get("uiTokenAmount", {}).get("uiAmount") or 0)
                break
        delta = post_amt - pre_amt
        if delta > best_delta:
            best_delta = delta
            output_mint = mint
            out_amount_raw = int(post.get("uiTokenAmount", {}).get("amount") or 0)
            out_decimals = int(post.get("uiTokenAmount", {}).get("decimals") or 0)

    if not output_mint or in_amount_sol <= 0:
        return None
    return {
        "output_mint": output_mint,
        "in_amount_sol": in_amount_sol,
        "out_amount_raw": out_amount_raw,
        "out_decimals": out_decimals,
    }


class CopyTradeWatcherTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="watch_wallet",
            display_name="Watch wallet for copy-trade",
            category=ToolCategory.market,
            description=(
                "Pull recent Jupiter swaps from a target wallet so the copy-trade "
                "strategy can replicate them. Returns up to `limit` swaps newest-first."
            ),
            capabilities=["copy-trade-detection"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(name="target", type="string", description="Target wallet address"),
                ToolParameter(
                    name="limit",
                    type="integer",
                    required=False,
                    default=10,
                    description="How many recent signatures to scan",
                ),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        target = str(params.get("target", "")).strip()
        if not target:
            return ToolResult(success=False, error="target required")
        limit = int(params.get("limit", 10))
        try:
            swaps = await recent_jupiter_swaps(target, limit=limit)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=f"copy-trade fetch failed: {e}")
        return ToolResult(
            success=True,
            raw_output=f"Found {len(swaps)} Jupiter swap(s) on {target[:6]}…",
            structured_output={"swaps": swaps},
        )
