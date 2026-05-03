"""Spot price for a Pump.fun bonding-curve token.

Reads the public pump.fun frontend API which exposes the curve's virtual
reserves. Spot price (SOL per UI token) is derived from:

    price = (virtual_sol_reserves / 1e9) / (virtual_token_reserves / 10**decimals)

Pump.fun tokens use 6 decimals.

This is the same calculation chainstacklabs/pumpfun-bonkfun-bot does in
src/platforms/pumpfun/curve_manager.py — we use the public REST endpoint
to avoid pulling in anchorpy/solders just to decode the bonding-curve
account.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

PUMP_API = "https://frontend-api-v3.pump.fun/coins"
PUMPFUN_DECIMALS = 6
LAMPORTS_PER_SOL = 1_000_000_000


class PriceUnavailable(Exception):
    """Raised when the price source can't return a fresh quote."""


async def get_spot_price(mint: str) -> float:
    """Returns SOL per UI token. Raises PriceUnavailable if no price."""
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{PUMP_API}/{mint}")
            if r.status_code == 404:
                raise PriceUnavailable(f"pump.fun has no record for {mint}")
            r.raise_for_status()
            data = r.json()

            # If the bonding curve has graduated to PumpSwap AMM, the curve
            # reserves don't move anymore — we'd need a different price source.
            if data.get("complete"):
                raise PriceUnavailable(f"{mint[:6]}… has graduated; bonding curve frozen")

            vsol = int(data.get("virtual_sol_reserves") or 0)
            vtok = int(data.get("virtual_token_reserves") or 0)
            if vsol <= 0 or vtok <= 0:
                raise PriceUnavailable(f"{mint[:6]}… returned zero reserves")

            sol = vsol / LAMPORTS_PER_SOL
            tokens = vtok / (10 ** PUMPFUN_DECIMALS)
            return sol / tokens
        except (httpx.HTTPError, PriceUnavailable) as e:
            last_err = e
            if attempt == 0:
                await asyncio.sleep(0.5)
    assert last_err is not None
    raise PriceUnavailable(f"price fetch failed: {last_err}")
