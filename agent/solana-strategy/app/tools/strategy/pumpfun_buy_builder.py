"""Build an unsigned Pump.fun buy/sell transaction via PumpPortal's trade-local API.

PumpPortal exposes `POST /api/trade-local` which constructs the bonding-curve
buy or sell instruction server-side and returns the serialized unsigned
transaction. We then forward that bytes blob to the trader's
`/api/auto/sign-and-send` endpoint, which routes signing through the
Electron loopback (under the active session policy).

This avoids vendoring the full chainstacklabs/pumpfun-bonkfun-bot codebase
while preserving the same trust boundary: strategy never signs.

Reference shape adapted from chainstacklabs/pumpfun-bonkfun-bot — Apache-2.0;
see THIRD_PARTY_NOTICES.md for attribution.
"""

from __future__ import annotations

import base64
from typing import Any, Dict

import httpx

PUMPPORTAL_TRADE_URL = "https://pumpportal.fun/api/trade-local"


async def build_buy_tx(
    mint: str,
    sol_amount: float,
    wallet_pubkey: str,
    slippage_pct: float = 10.0,
    priority_fee_sol: float = 0.0005,
) -> str:
    """Returns the unsigned serialized Pump.fun buy tx (base64)."""
    payload: Dict[str, Any] = {
        "publicKey": wallet_pubkey,
        "action": "buy",
        "mint": mint,
        "amount": sol_amount,
        "denominatedInSol": "true",
        "slippage": slippage_pct,
        "priorityFee": priority_fee_sol,
        "pool": "pump",
    }
    return await _post_local(payload)


async def build_sell_tx(
    mint: str,
    token_amount: float,
    wallet_pubkey: str,
    slippage_pct: float = 10.0,
    priority_fee_sol: float = 0.0005,
) -> str:
    """Returns the unsigned serialized Pump.fun sell tx (base64). `token_amount` is in UI units."""
    payload: Dict[str, Any] = {
        "publicKey": wallet_pubkey,
        "action": "sell",
        "mint": mint,
        "amount": token_amount,
        "denominatedInSol": "false",
        "slippage": slippage_pct,
        "priorityFee": priority_fee_sol,
        "pool": "pump",
    }
    return await _post_local(payload)


async def _post_local(payload: Dict[str, Any]) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(PUMPPORTAL_TRADE_URL, json=payload)
    if r.status_code >= 400:
        raise RuntimeError(f"PumpPortal trade-local {r.status_code}: {r.text}")
    # Response body is the raw bytes of the unsigned tx; convert to base64.
    return base64.b64encode(r.content).decode("ascii")
