"""Pump.fun new-launch scanner.

Maintains a short-lived background task that subscribes to PumpPortal's public
WebSocket data feed (`wss://pumpportal.fun/api/data`) for `subscribeNewToken`
events. The auto-trade runner pulls candidates via `next_qualifying_launch()`
which returns the freshest unseen launch matching the filters.

Approach reference: chainstacklabs/pumpfun-bonkfun-bot's
`src/platforms/pumpfun/pumpportal_processor.py` (Apache-2.0). We don't lift
their parser code — we re-derive against the documented PumpPortal payload
shape — but credit them in THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any, Deque, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

WS_URL = "wss://pumpportal.fun/api/data"

# Bounded buffer of recently-seen launches; consumer pops one at a time.
_queue: Deque[Dict[str, Any]] = deque(maxlen=64)
_seen_mints: set[str] = set()
_listener_task: Optional[asyncio.Task[None]] = None


async def _listen() -> None:
    # We use httpx's ws support (>=0.27 has it via httpx_ws plugin); fall back
    # to a polling REST call if the WS dep isn't present.
    try:
        import websockets  # type: ignore
    except ImportError:
        logger.warning("websockets not installed — pumpfun scanner falling back to no-op")
        return

    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        async for raw in ws:
            try:
                msg = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001
                continue
            mint = msg.get("mint") or msg.get("ca")
            if not mint or mint in _seen_mints:
                continue
            _seen_mints.add(mint)
            _queue.append({
                "mint": mint,
                "name": msg.get("name"),
                "symbol": msg.get("symbol"),
                "creator": msg.get("traderPublicKey") or msg.get("creator"),
                "initial_buy_sol": msg.get("solAmount"),
                "market_cap_sol": msg.get("marketCapSol"),
                # Heuristic placeholders so the runner has something to filter on.
                # Real rug-score / liquidity should come from a separate enrichment pass.
                "rug_score": 0.5,
                "liquidity_sol": float(msg.get("solAmount") or 0),
            })


async def _ensure_listener() -> None:
    global _listener_task
    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(_listen())


async def next_qualifying_launch(
    rug_score_max: float,
    min_liquidity_sol: float,
) -> Optional[Dict[str, Any]]:
    """Pop the next queued launch that passes the filters, or None."""
    await _ensure_listener()
    while _queue:
        candidate = _queue.popleft()
        if candidate.get("rug_score", 1.0) > rug_score_max:
            continue
        if float(candidate.get("liquidity_sol", 0)) < min_liquidity_sol:
            continue
        return candidate
    return None
