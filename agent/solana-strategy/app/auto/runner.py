"""Auto-trade runner — long-running async loop that decides + executes trades.

Strategies:
  - indicator      : runs `indicator_signal` against Birdeye OHLCV for a watchlist
  - copy_trade     : polls a target wallet's recent swaps and replicates them
  - pumpfun_snipe  : watches new Pump.fun launches and snipes per filter

The runner never signs. It either:
  - calls trader's POST /api/auto/swap (with x-jarvis-policy-id) for Jupiter swaps, or
  - builds an unsigned tx (Pump.fun) and POSTs to trader's /api/auto/sign-and-send.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.config import config
from app.indicators import bollinger, ema, latest, rsi  # noqa: F401
from app.auto.events import bus

logger = logging.getLogger(__name__)


@dataclass
class RunnerConfig:
    strategy: str  # 'indicator' | 'copy_trade' | 'pumpfun_snipe'
    policy_id: str
    max_trade_sol: float
    total_budget_sol: float
    expires_at: float
    interval_sec: int = 30
    # Strategy-specific:
    watchlist: List[str] = field(default_factory=list)         # mints (indicator)
    target_wallets: List[str] = field(default_factory=list)    # copy_trade
    copy_ratio: float = 0.01                                   # copy_trade
    rug_score_max: float = 0.5                                 # pumpfun_snipe
    min_liquidity_sol: float = 5.0                             # pumpfun_snipe
    max_buy_sol: float = 0.01                                  # pumpfun_snipe


_active_task: Optional[asyncio.Task[None]] = None
_active_config: Optional[RunnerConfig] = None
_stop_event: Optional[asyncio.Event] = None


def is_running() -> bool:
    return _active_task is not None and not _active_task.done()


def current_config() -> Optional[RunnerConfig]:
    return _active_config


async def stop() -> None:
    global _active_task, _active_config, _stop_event
    if _stop_event:
        _stop_event.set()
    if _active_task:
        try:
            await asyncio.wait_for(_active_task, timeout=3.0)
        except asyncio.TimeoutError:
            _active_task.cancel()
    _active_task = None
    _active_config = None
    _stop_event = None
    bus.publish("stopped", {})


async def start(cfg: RunnerConfig) -> None:
    global _active_task, _active_config, _stop_event
    if is_running():
        raise RuntimeError("auto-trade runner already active")
    _active_config = cfg
    _stop_event = asyncio.Event()
    bus.publish("started", {"strategy": cfg.strategy, "policy_id": cfg.policy_id})
    _active_task = asyncio.create_task(_loop(cfg, _stop_event))


# ── Loop ──────────────────────────────────────────────────────────────────────


async def _loop(cfg: RunnerConfig, stop_event: asyncio.Event) -> None:
    try:
        while not stop_event.is_set():
            if time.time() >= cfg.expires_at:
                bus.publish("expired", {})
                break
            try:
                if cfg.strategy == "indicator":
                    await _tick_indicator(cfg)
                elif cfg.strategy == "copy_trade":
                    await _tick_copy_trade(cfg)
                elif cfg.strategy == "pumpfun_snipe":
                    await _tick_pumpfun_snipe(cfg)
                else:
                    bus.publish("error", {"message": f"unknown strategy {cfg.strategy}"})
                    break
            except Exception as e:  # noqa: BLE001
                logger.exception("runner tick failed")
                bus.publish("error", {"message": str(e)})

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=cfg.interval_sec)
            except asyncio.TimeoutError:
                pass
    finally:
        bus.publish("ended", {})


# ── Indicator strategy ────────────────────────────────────────────────────────


_seen_indicator_state: Dict[str, str] = {}  # mint -> last verdict


async def _tick_indicator(cfg: RunnerConfig) -> None:
    if not cfg.watchlist:
        bus.publish("skip", {"reason": "empty watchlist"})
        return

    for mint in cfg.watchlist:
        try:
            closes = await _fetch_closes(mint, "15m", 80)
        except Exception as e:  # noqa: BLE001
            bus.publish("error", {"mint": mint, "message": f"ohlcv: {e}"})
            continue
        if len(closes) < 25:
            bus.publish("skip", {"mint": mint, "reason": f"only {len(closes)} candles"})
            continue
        ema9 = latest(ema(closes, 9))
        ema21 = latest(ema(closes, 21))
        rsi_v = latest(rsi(closes, 14))
        _, upper, lower = bollinger(closes, 20)
        u = latest(upper); l = latest(lower)
        last = closes[-1]

        verdict, reason = _indicator_verdict(last, ema9, ema21, rsi_v, u, l)
        prev = _seen_indicator_state.get(mint)
        _seen_indicator_state[mint] = verdict

        if verdict == "hold" or verdict == prev:
            bus.publish("skip", {"mint": mint, "reason": reason, "verdict": verdict})
            continue

        if verdict == "buy":
            sol = min(cfg.max_trade_sol, cfg.max_buy_sol)
            await _exec_swap(cfg, output_mint=mint, sol=sol, reason=reason)
        # "sell" path intentionally a no-op for indicator MVP
        # (would require knowing token holding amount + selling back to SOL).


def _indicator_verdict(
    close: float, ema9: float, ema21: float, rsi_v: float, upper: float, lower: float
) -> tuple[str, str]:
    score = 0.0
    notes: List[str] = []
    if not math.isnan(rsi_v):
        if rsi_v < 30: score += 1.5; notes.append(f"RSI {rsi_v:.1f} oversold")
        elif rsi_v > 70: score -= 1.5; notes.append(f"RSI {rsi_v:.1f} overbought")
    if not math.isnan(lower) and close < lower: score += 1.0; notes.append("close < lower band")
    if not math.isnan(upper) and close > upper: score -= 1.0; notes.append("close > upper band")
    if not (math.isnan(ema9) or math.isnan(ema21)):
        if ema9 > ema21: score += 0.5; notes.append("EMA9 > EMA21")
        else:            score -= 0.5; notes.append("EMA9 < EMA21")
    verdict = "buy" if score >= 1.0 else ("sell" if score <= -1.0 else "hold")
    return verdict, "; ".join(notes) if notes else "no signal"


async def _fetch_closes(mint: str, interval: str, lookback: int) -> List[float]:
    from app.market_data import fetch_closes
    return await fetch_closes(mint, interval, lookback)


# ── Copy-trade strategy ───────────────────────────────────────────────────────


_seen_signatures: Dict[str, set[str]] = {}


async def _tick_copy_trade(cfg: RunnerConfig) -> None:
    from app.tools.strategy.copy_trade_watcher import recent_jupiter_swaps

    if not cfg.target_wallets:
        bus.publish("skip", {"reason": "no target wallets"})
        return

    for target in cfg.target_wallets:
        seen = _seen_signatures.setdefault(target, set())
        try:
            swaps = await recent_jupiter_swaps(target, limit=5)
        except Exception as e:  # noqa: BLE001
            bus.publish("error", {"target": target, "message": str(e)})
            continue

        for swap in swaps:
            sig = swap.get("signature")
            if not sig or sig in seen:
                continue
            seen.add(sig)

            output_mint = swap.get("output_mint")
            in_amount_sol = float(swap.get("in_amount_sol", 0))
            if not output_mint:
                bus.publish("skip", {"target": target, "sig": sig, "reason": "no output mint"})
                continue

            sized_sol = max(in_amount_sol * cfg.copy_ratio, 0.001)
            sized_sol = min(sized_sol, cfg.max_trade_sol)
            await _exec_swap(
                cfg,
                output_mint=output_mint,
                sol=sized_sol,
                reason=f"copy {target[:6]}… sig={sig[:6]}…",
            )


# ── Pump.fun snipe strategy ───────────────────────────────────────────────────


async def _tick_pumpfun_snipe(cfg: RunnerConfig) -> None:
    from app.tools.strategy.pumpfun_scanner import next_qualifying_launch
    from app.tools.strategy.pumpfun_buy_builder import build_buy_tx

    candidate = await next_qualifying_launch(
        rug_score_max=cfg.rug_score_max,
        min_liquidity_sol=cfg.min_liquidity_sol,
    )
    if not candidate:
        bus.publish("skip", {"reason": "no qualifying launches this tick"})
        return

    try:
        unsigned_b64 = await build_buy_tx(
            mint=candidate["mint"],
            sol_amount=min(cfg.max_buy_sol, cfg.max_trade_sol),
            wallet_pubkey=_wallet_pubkey_from_env(),
        )
    except NotImplementedError:
        bus.publish("skip", {
            "mint": candidate["mint"],
            "reason": "pumpfun builder requires vendored chainstacklabs (not yet vendored)",
        })
        return
    except Exception as e:  # noqa: BLE001
        bus.publish("error", {"mint": candidate["mint"], "message": str(e)})
        return

    sol = min(cfg.max_buy_sol, cfg.max_trade_sol)
    lamports = int(sol * 1_000_000_000)
    await _post_sign_and_send(
        cfg,
        tx_b64=unsigned_b64,
        action="pumpfun_buy",
        lamports_out=lamports,
        mint=candidate["mint"],
        reason=f"snipe {candidate['mint'][:6]}… rug={candidate.get('rug_score', '?')}",
    )


# ── Execution helpers ─────────────────────────────────────────────────────────


def _wallet_pubkey_from_env() -> str:
    import os
    return os.getenv("WALLET_PUBKEY", "")


async def _exec_swap(cfg: RunnerConfig, output_mint: str, sol: float, reason: str) -> None:
    if sol <= 0:
        bus.publish("skip", {"reason": "sized 0 SOL", "mint": output_mint})
        return
    lamports = int(sol * 1_000_000_000)
    bus.publish("decide", {
        "action": "swap", "mint": output_mint, "sol": sol, "reason": reason,
    })
    payload = {
        "outputMint": output_mint,
        "amount": sol,
        "slippageBps": 100,
        "policyId": cfg.policy_id,
        "lamportsOut": lamports,
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{config.TRADER_BASE_URL}/api/auto/swap", json=payload)
            if r.status_code == 403:
                bus.publish("rejected", {"action": "swap", "mint": output_mint, "reason": r.text})
                return
            r.raise_for_status()
            data = r.json()
        bus.publish("executed", {
            "action": "swap", "mint": output_mint, "sol": sol,
            "signature": data.get("signature"), "reason": reason,
        })
    except Exception as e:  # noqa: BLE001
        bus.publish("error", {"action": "swap", "mint": output_mint, "message": str(e)})


async def _post_sign_and_send(
    cfg: RunnerConfig,
    tx_b64: str,
    action: str,
    lamports_out: int,
    mint: Optional[str],
    reason: str,
) -> None:
    bus.publish("decide", {"action": action, "mint": mint, "reason": reason})
    payload: Dict[str, Any] = {
        "policyId": cfg.policy_id,
        "tx": tx_b64,
        "action": action,
        "lamportsOut": lamports_out,
    }
    if mint:
        payload["mint"] = mint
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{config.TRADER_BASE_URL}/api/auto/sign-and-send", json=payload)
            if r.status_code == 403:
                bus.publish("rejected", {"action": action, "mint": mint, "reason": r.text})
                return
            r.raise_for_status()
            data = r.json()
        bus.publish("executed", {
            "action": action, "mint": mint, "signature": data.get("signature"), "reason": reason,
        })
    except Exception as e:  # noqa: BLE001
        bus.publish("error", {"action": action, "mint": mint, "message": str(e)})
