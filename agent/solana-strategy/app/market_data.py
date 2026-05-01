"""Unified close-price fetcher.

Defaults to GeckoTerminal (free, no API key, Solana-native). Falls back to
Birdeye when `BIRDEYE_API_KEY` is set, in case the user wants their richer
data. Both produce a list of close prices in chronological order.
"""

from __future__ import annotations

import logging
import time
from typing import List

import httpx

from app.config import config

logger = logging.getLogger(__name__)

INTERVAL_TO_BIRDEYE = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1H": "1H",
    "4H": "4H",
    "1D": "1D",
}

INTERVAL_TO_BIRDEYE_SECS = {
    "1m": 60, "5m": 300, "15m": 900, "1H": 3600, "4H": 14_400, "1D": 86_400,
}

# GeckoTerminal expects (timeframe, aggregate). e.g. ("minute", 15) for 15m.
INTERVAL_TO_GT = {
    "1m":  ("minute", 1),
    "5m":  ("minute", 5),
    "15m": ("minute", 15),
    "1H":  ("hour", 1),
    "4H":  ("hour", 4),
    "1D":  ("day", 1),
}

GT_BASE = "https://api.geckoterminal.com/api/v2"


async def fetch_closes(mint: str, interval: str, lookback: int) -> List[float]:
    """Try Birdeye if configured, else GeckoTerminal. Returns chronological closes."""
    if interval not in INTERVAL_TO_BIRDEYE:
        raise ValueError(f"interval must be one of {list(INTERVAL_TO_BIRDEYE)}")

    if config.BIRDEYE_API_KEY:
        try:
            return await _fetch_birdeye(mint, interval, lookback)
        except Exception as e:  # noqa: BLE001
            logger.warning("Birdeye fetch failed (%s); falling back to GeckoTerminal", e)

    return await _fetch_geckoterminal(mint, interval, lookback)


async def _fetch_birdeye(mint: str, interval: str, lookback: int) -> List[float]:
    secs = INTERVAL_TO_BIRDEYE_SECS[interval]
    time_to = int(time.time())
    time_from = time_to - secs * lookback
    url = f"{config.BIRDEYE_BASE_URL}/defi/history_price"
    headers = {"X-API-KEY": config.BIRDEYE_API_KEY, "x-chain": "solana"}
    params = {
        "address": mint,
        "address_type": "token",
        "type": INTERVAL_TO_BIRDEYE[interval],
        "time_from": time_from,
        "time_to": time_to,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
    items = (data.get("data") or {}).get("items") or []
    return [float(it["value"]) for it in items if "value" in it]


async def _fetch_geckoterminal(mint: str, interval: str, lookback: int) -> List[float]:
    """Two-step: resolve mint -> top pool, then fetch OHLCV on that pool."""
    timeframe, aggregate = INTERVAL_TO_GT[interval]

    async with httpx.AsyncClient(
        timeout=20,
        headers={"accept": "application/json;version=20230302"},
    ) as client:
        pools_url = f"{GT_BASE}/networks/solana/tokens/{mint}/pools"
        r = await client.get(pools_url)
        if r.status_code != 200:
            raise RuntimeError(f"GeckoTerminal pools lookup failed: {r.status_code} {r.text[:120]}")
        body = r.json()
        pools = body.get("data") or []
        if not pools:
            raise RuntimeError(f"No DEX pools found for mint {mint}")

        # Pick the highest-reserve pool (first item is usually #1 by reserve).
        pool_address = pools[0].get("attributes", {}).get("address") or pools[0].get("id", "").split("_")[-1]
        if not pool_address:
            raise RuntimeError("Pool record missing address")

        ohlcv_url = (
            f"{GT_BASE}/networks/solana/pools/{pool_address}/ohlcv/{timeframe}"
        )
        params = {"aggregate": aggregate, "limit": min(lookback, 1000)}
        r2 = await client.get(ohlcv_url, params=params)
        if r2.status_code != 200:
            raise RuntimeError(f"GeckoTerminal OHLCV failed: {r2.status_code} {r2.text[:120]}")
        ohlcv = r2.json()

    # Schema: { data: { attributes: { ohlcv_list: [[ts, o, h, l, c, vol], ...] } } }
    rows = (
        ohlcv.get("data", {})
        .get("attributes", {})
        .get("ohlcv_list", [])
    ) or []
    if not rows:
        return []
    # GeckoTerminal returns newest-first; flip to chronological.
    rows.reverse()
    closes = [float(row[4]) for row in rows if len(row) >= 5]
    return closes


def source_name() -> str:
    return "birdeye" if config.BIRDEYE_API_KEY else "geckoterminal"
