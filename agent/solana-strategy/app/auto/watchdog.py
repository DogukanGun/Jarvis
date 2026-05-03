"""Dead-man's switch for the auto-trade runner.

A second long-running task that:
  1. Watches for a stale UI heartbeat (Auto-Trade tab unmounted / app closed).
  2. Probes the trader's /health to detect prolonged unreachability.
  3. Surfaces explicit panic requests from the manual button or app-quit hook.

When any condition fires, sets a `panic` flag on a shared callback so the
runner's exit loop sells everything ignoring TP/SL/hold-time.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

UI_HEARTBEAT_TIMEOUT_SEC = 60
TRADER_FAILURE_THRESHOLD = 5  # consecutive /health misses
TRADER_HEALTH_TIMEOUT_SEC = 5
TICK_SEC = 10


# Module-level mutable state — single watchdog at a time, mirroring the
# single-runner design.
_last_ui_heartbeat: float = 0.0
_panic_requested_reason: Optional[str] = None
_active_task: Optional[asyncio.Task[None]] = None
_stop_event: Optional[asyncio.Event] = None


def heartbeat() -> None:
    """Called by `POST /api/auto/heartbeat`."""
    global _last_ui_heartbeat
    _last_ui_heartbeat = time.time()


def request_panic(reason: str) -> None:
    """Called by `POST /api/auto/panic` and the Electron `before-quit` hook."""
    global _panic_requested_reason
    _panic_requested_reason = reason


def last_heartbeat_age_sec() -> float:
    if _last_ui_heartbeat <= 0:
        return float("inf")
    return time.time() - _last_ui_heartbeat


def is_running() -> bool:
    return _active_task is not None and not _active_task.done()


async def start(
    trader_base_url: str,
    on_panic: Callable[[str], Awaitable[None]],
) -> None:
    """Start the watchdog. `on_panic(reason)` is awaited when panic fires.
    Resets heartbeat to "now" so we don't immediately panic on first tick."""
    global _active_task, _stop_event, _last_ui_heartbeat, _panic_requested_reason
    if is_running():
        return
    _last_ui_heartbeat = time.time()
    _panic_requested_reason = None
    _stop_event = asyncio.Event()
    _active_task = asyncio.create_task(_loop(trader_base_url, on_panic, _stop_event))


async def stop() -> None:
    global _active_task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _active_task:
        try:
            await asyncio.wait_for(_active_task, timeout=2.0)
        except asyncio.TimeoutError:
            _active_task.cancel()
    _active_task = None
    _stop_event = None


async def _loop(
    trader_base_url: str,
    on_panic: Callable[[str], Awaitable[None]],
    stop_event: asyncio.Event,
) -> None:
    trader_misses = 0
    fired = False
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=TICK_SEC)
            break  # stop_event set
        except asyncio.TimeoutError:
            pass

        if fired:
            continue  # don't spam multiple panics

        # 1. Explicit panic request (manual button, app-quit)
        if _panic_requested_reason is not None:
            fired = True
            try: await on_panic(_panic_requested_reason)
            except Exception as e:  # noqa: BLE001
                logger.exception("on_panic raised: %s", e)
            continue

        # 2. UI heartbeat staleness
        age = last_heartbeat_age_sec()
        if age > UI_HEARTBEAT_TIMEOUT_SEC:
            fired = True
            try: await on_panic("ui-heartbeat-timeout")
            except Exception as e:  # noqa: BLE001
                logger.exception("on_panic raised: %s", e)
            continue

        # 3. Trader reachability
        try:
            async with httpx.AsyncClient(timeout=TRADER_HEALTH_TIMEOUT_SEC) as client:
                r = await client.get(f"{trader_base_url}/health")
            if r.status_code == 200:
                trader_misses = 0
            else:
                trader_misses += 1
        except (httpx.HTTPError, asyncio.TimeoutError):
            trader_misses += 1

        if trader_misses >= TRADER_FAILURE_THRESHOLD:
            fired = True
            try: await on_panic("trader-unreachable")
            except Exception as e:  # noqa: BLE001
                logger.exception("on_panic raised: %s", e)
