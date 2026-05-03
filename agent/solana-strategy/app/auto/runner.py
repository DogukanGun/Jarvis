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
from app.auto.pump_price import get_spot_price, PriceUnavailable
from app.auto import store, watchdog
from datetime import datetime

# Vendored from chainstacklabs/pumpfun-bonkfun-bot (Apache-2.0). The Position
# class encapsulates take-profit / stop-loss / max-hold semantics and the
# `should_exit(current_price)` decision. See vendor/chainstacklabs/NOTICE.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "chainstacklabs"))
from trading.position import Position as ChainstackPosition, ExitReason  # type: ignore  # noqa: E402

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
    # Position lifecycle (pumpfun_snipe). The runner exits naturally when all
    # open positions have closed and the user has requested graceful stop.
    # Exit conditions are handled by the vendored chainstacklabs `Position`
    # class — take-profit / stop-loss / max-hold time, whichever fires first.
    take_profit_pct: float | None = 0.5    # 0.5 = +50%; None disables
    stop_loss_pct: float | None = 0.3      # 0.3 = -30%; None disables
    max_hold_time: int | None = 60         # seconds; None disables


@dataclass
class TrackedPosition:
    """Local bookkeeping wrapped around a chainstacklabs Position."""
    inner: ChainstackPosition
    entry_sol: float                # what we paid
    sell_attempted: bool = False
    sold: bool = False
    last_error: Optional[str] = None


_positions: Dict[str, TrackedPosition] = {}
_no_more_buys: bool = False  # set when user requests graceful stop


_active_task: Optional[asyncio.Task[None]] = None
_active_config: Optional[RunnerConfig] = None
_stop_event: Optional[asyncio.Event] = None
_session_lost: bool = False  # set when the loopback rejects with 403
_panic_sell: bool = False
_panic_reason: Optional[str] = None
# When loaded from disk on startup but no session is active yet, we keep
# positions but don't try to sell until a fresh policy is set via
# resume_with_new_policy (Resume button).
_recovered: bool = False


# Panic priority fee — bumped from the normal 0.0005 SOL so panic sells land
# during congestion. See plan §4.3.
_PANIC_PRIORITY_FEE_SOL = 0.002


def is_panic() -> bool:
    return _panic_sell


def panic_reason() -> Optional[str]:
    return _panic_reason


def _persist_state() -> None:
    """Best-effort save; never raise — persistence failure mustn't break the loop."""
    try:
        policy = _active_config.policy_id if _active_config else None
        store.save(_positions, policy)
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-positions persist failed: %s", e)


async def _on_panic(reason: str) -> None:
    """Called by the watchdog when any panic condition fires."""
    global _panic_sell, _panic_reason, _no_more_buys
    if _panic_sell:
        return
    _panic_sell = True
    _panic_reason = reason
    _no_more_buys = True
    bus.publish("panic-mode-entered", {
        "reason": reason,
        "open_positions": [p.inner.mint for p in _positions.values() if not p.sold],
    })


def request_panic(reason: str) -> None:
    """Sync entry point exposed to /api/auto/panic."""
    watchdog.request_panic(reason)


def is_running() -> bool:
    return _active_task is not None and not _active_task.done()


def current_config() -> Optional[RunnerConfig]:
    return _active_config


def open_positions() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    now = time.time()
    for p in _positions.values():
        if p.sold:
            continue
        inner = p.inner
        try:
            entry_ts = inner.entry_time.timestamp()
        except (AttributeError, ValueError):
            entry_ts = now
        out.append({
            "mint": inner.mint,
            "symbol": inner.symbol,
            "entry_price": inner.entry_price,
            "entry_sol": p.entry_sol,
            "quantity": inner.quantity,
            "age_sec": max(0.0, now - entry_ts),
            "take_profit_price": inner.take_profit_price,
            "stop_loss_price": inner.stop_loss_price,
            "max_hold_time": inner.max_hold_time,
            "sell_attempted": p.sell_attempted,
            "last_error": p.last_error,
        })
    return out


async def stop_graceful() -> None:
    """Stop opening new positions; keep running until all positions close."""
    global _no_more_buys
    _no_more_buys = True
    bus.publish("stopping", {"reason": "graceful — no new buys, draining positions"})


async def resume_with_new_policy(new_policy_id: str) -> bool:
    """Recover from a session-lost state: swap in a fresh policy id and
    let the runner finish selling stuck positions. Returns True on success.
    """
    global _session_lost
    if _active_config is None:
        return False
    _active_config.policy_id = new_policy_id
    # Reset retry flags so previously-stuck positions get one more attempt.
    for p in _positions.values():
        if not p.sold:
            p.sell_attempted = False
            p.last_error = None
    _session_lost = False
    bus.publish("resumed", {
        "policy_id": new_policy_id,
        "stuck_positions": [p.inner.mint for p in _positions.values() if not p.sold],
    })
    return True


async def stop() -> None:
    """Hard stop — kill the runner immediately."""
    global _active_task, _active_config, _stop_event, _no_more_buys, _session_lost
    global _panic_sell, _panic_reason, _recovered
    if _stop_event:
        _stop_event.set()
    if _active_task:
        try:
            await asyncio.wait_for(_active_task, timeout=3.0)
        except asyncio.TimeoutError:
            _active_task.cancel()
    await watchdog.stop()
    _active_task = None
    _active_config = None
    _stop_event = None
    _no_more_buys = False
    _session_lost = False
    _panic_sell = False
    _panic_reason = None
    _recovered = False
    _positions.clear()
    # Hard stop = user explicitly requested abandonment of state.
    store.clear()
    bus.publish("stopped", {})


async def start(cfg: RunnerConfig) -> None:
    global _active_task, _active_config, _stop_event, _no_more_buys, _session_lost
    global _panic_sell, _panic_reason, _recovered
    if is_running():
        raise RuntimeError("auto-trade runner already active")
    _active_config = cfg
    _stop_event = asyncio.Event()
    _no_more_buys = False
    _session_lost = False
    _panic_sell = False
    _panic_reason = None
    _recovered = False
    _positions.clear()

    # Recovery: load any positions left over from a previous run that
    # crashed/was killed before draining.
    payload = store.load()
    if payload:
        recovered = _hydrate_positions(payload)
        if recovered:
            _recovered = True
            bus.publish("recovered", {
                "count": recovered,
                "policy_id_was": payload.get("policy_id"),
                "advice": "session policy may need re-authorization to sell these",
            })

    bus.publish("started", {
        "strategy": cfg.strategy,
        "policy_id": cfg.policy_id,
        "recovered_count": len([p for p in _positions.values() if not p.sold]),
    })
    _active_task = asyncio.create_task(_loop(cfg, _stop_event))
    # Watchdog runs alongside the main loop. on_panic flips _panic_sell.
    await watchdog.start(config.TRADER_BASE_URL, _on_panic)


def _hydrate_positions(payload: Dict[str, Any]) -> int:
    """Rebuild TrackedPositions from a persisted payload. Returns count loaded."""
    count = 0
    for d in store.positions_from_payload(payload):
        if d.get("sold"):
            continue
        try:
            entry_iso = d.get("entry_time_iso")
            entry_time = datetime.fromisoformat(entry_iso) if entry_iso else datetime.utcnow()
            inner = ChainstackPosition(
                mint=d["mint"],
                symbol=d.get("symbol") or d["mint"][:8],
                entry_price=float(d.get("entry_price") or 0.0),
                quantity=float(d.get("quantity") or 0.0),
                entry_time=entry_time,
                take_profit_price=d.get("take_profit_price"),
                stop_loss_price=d.get("stop_loss_price"),
                max_hold_time=d.get("max_hold_time"),
                is_active=bool(d.get("is_active", True)),
            )
            tracked = TrackedPosition(
                inner=inner,
                entry_sol=float(d.get("entry_sol") or 0.0),
                sell_attempted=False,  # let it retry on this run
                sold=False,
                last_error=d.get("last_error"),
            )
            _positions[inner.mint] = tracked
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to hydrate position %s: %s", d, e)
    return count


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

            # Natural exit: graceful stop requested AND no live positions.
            if _no_more_buys and not any(not p.sold for p in _positions.values()):
                bus.publish("drained", {"reason": "all positions closed"})
                store.clear()
                break

            # Fatal exit: the Electron loopback rejected a sign with 403.
            # In panic mode, we keep retrying — the user may resume mid-flight
            # and we don't want to bail with positions still on-chain. Outside
            # panic, treat 403 as terminal so we don't burn fees forever.
            if _session_lost and not _panic_sell:
                stuck = [p.inner.mint for p in _positions.values() if not p.sold]
                bus.publish("session-lost", {
                    "reason": "loopback returned 403 'no active session'",
                    "stuck_positions": stuck,
                    "advice": "re-authorize via the Auto-Trade tab to resume selling",
                })
                break

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
    # 1. Drain exits first — every position whose exit condition fired (or
    #    every position when in panic mode) gets sold.
    await _process_exits(cfg)

    # 2. Stop opening new entries if user requested graceful stop, panic
    #    fired, or budget is exhausted.
    if _no_more_buys or _panic_sell:
        return
    spent = sum(p.entry_sol for p in _positions.values())
    remaining_budget = cfg.total_budget_sol - spent
    if remaining_budget < cfg.max_buy_sol * 0.5:
        bus.publish("skip", {"reason": "budget exhausted; only draining positions now"})
        return

    # 3. Try to open a new position.
    from app.tools.strategy.pumpfun_scanner import next_qualifying_launch
    from app.tools.strategy.pumpfun_buy_builder import build_buy_tx

    candidate = await next_qualifying_launch(
        rug_score_max=cfg.rug_score_max,
        min_liquidity_sol=cfg.min_liquidity_sol,
    )
    if not candidate:
        bus.publish("skip", {"reason": "no qualifying launches this tick"})
        return
    if candidate["mint"] in _positions:
        bus.publish("skip", {"mint": candidate["mint"], "reason": "already holding"})
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

    sol = min(cfg.max_buy_sol, cfg.max_trade_sol, remaining_budget)
    lamports = int(sol * 1_000_000_000)
    sig = await _post_sign_and_send(
        cfg,
        tx_b64=unsigned_b64,
        action="pumpfun_buy",
        lamports_out=lamports,
        mint=candidate["mint"],
        reason=f"snipe {candidate['mint'][:6]}… rug={candidate.get('rug_score', '?')}",
    )
    if sig:
        # Get the entry price right after the buy lands so TP/SL anchors are
        # accurate. The actual `quantity` of tokens won't be known until the
        # SPL balance query at sell-time (Pump.fun bonding curve decides),
        # so we leave that at 0 and let the sell path query on-chain balance.
        try:
            entry_price = await get_spot_price(candidate["mint"])
        except PriceUnavailable as e:
            entry_price = 0.0
            bus.publish("warn", {
                "mint": candidate["mint"],
                "phase": "post-buy-price",
                "message": f"falling back to time-only exit: {e}",
            })

        inner = ChainstackPosition.create_from_buy_result(
            mint=candidate["mint"],
            symbol=candidate.get("symbol") or candidate["mint"][:8],
            entry_price=entry_price,
            quantity=0.0,  # filled in at sell time from on-chain balance
            take_profit_percentage=cfg.take_profit_pct if entry_price > 0 else None,
            stop_loss_percentage=cfg.stop_loss_pct if entry_price > 0 else None,
            max_hold_time=cfg.max_hold_time,
        )
        _positions[candidate["mint"]] = TrackedPosition(inner=inner, entry_sol=sol)
        _persist_state()
        bus.publish("position-opened", {
            "mint": candidate["mint"],
            "sol": sol,
            "entry_price": entry_price,
            "take_profit_price": inner.take_profit_price,
            "stop_loss_price": inner.stop_loss_price,
            "max_hold_time": inner.max_hold_time,
            "open_positions": len([p for p in _positions.values() if not p.sold]),
        })


async def _process_exits(cfg: RunnerConfig) -> None:
    """Check every open position; sell ones whose exit condition has fired.

    Exit logic is delegated to vendored chainstacklabs `Position.should_exit`,
    which evaluates take-profit / stop-loss / max-hold-time in that order.
    """
    from app.tools.strategy.pumpfun_sell_builder import build_sell_tx

    for mint, tracked in list(_positions.items()):
        if tracked.sold:
            continue
        # In normal mode, skip if a sell is already in flight (avoids double
        # signing). In panic mode, drop that gate — we want every retry the
        # tick allows because positions stuck mid-sale are exactly the ones
        # we need to land hardest.
        if tracked.sell_attempted and not _panic_sell:
            continue

        # Fetch fresh price for TP/SL evaluation; if unavailable, max-hold
        # time will still trigger eventually.
        current_price: float | None = None
        if tracked.inner.take_profit_price or tracked.inner.stop_loss_price:
            try:
                current_price = await get_spot_price(mint)
            except PriceUnavailable as e:
                logger.debug("price fetch for %s failed: %s", mint, e)
                current_price = None

        # `should_exit` needs *some* price to short-circuit TP/SL checks
        # without crashing — pass entry_price as a neutral fallback so only
        # the max-hold-time branch fires.
        decision_price = current_price if current_price is not None else tracked.inner.entry_price

        if _panic_sell:
            # Panic mode: bypass TP/SL/hold-time entirely.
            should, reason = True, ExitReason.MANUAL
        else:
            should, reason = tracked.inner.should_exit(decision_price)
        if not should:
            continue

        tracked.sell_attempted = True
        _persist_state()

        try:
            ui_amount = await _get_spl_ui_amount(mint)
        except Exception as e:  # noqa: BLE001
            tracked.last_error = f"balance query failed: {e}"
            bus.publish("error", {"mint": mint, "phase": "balance", "message": str(e)})
            tracked.sell_attempted = False
            continue
        if ui_amount <= 0:
            tracked.sold = True
            bus.publish("position-empty", {
                "mint": mint,
                "reason": "no SPL balance — buy may have failed",
            })
            continue

        # Bump priority fee in panic mode so sells land during congestion.
        priority_fee = _PANIC_PRIORITY_FEE_SOL if _panic_sell else 0.0005
        try:
            unsigned_b64 = await build_sell_tx(
                mint=mint,
                token_amount=ui_amount,
                wallet_pubkey=_wallet_pubkey_from_env(),
                priority_fee_sol=priority_fee,
            )
        except Exception as e:  # noqa: BLE001
            tracked.last_error = f"sell builder failed: {e}"
            bus.publish("error", {"mint": mint, "phase": "build-sell", "message": str(e)})
            tracked.sell_attempted = False
            continue

        sig = await _post_sign_and_send(
            cfg,
            tx_b64=unsigned_b64,
            action="pumpfun_sell",
            lamports_out=10_000,  # nominal — sells don't drain SOL beyond fee
            mint=mint,
            reason=f"exit {mint[:6]}… via {reason.value if reason else 'unknown'}",
        )
        if sig:
            tracked.sold = True
            tracked.inner.close_position(decision_price, reason or ExitReason.MANUAL)
            _persist_state()
            pnl: Dict[str, Any] = {}
            try:
                pnl = tracked.inner.get_pnl()
            except ValueError:
                pass
            bus.publish("position-closed", {
                "mint": mint,
                "exit_reason": "panic" if _panic_sell else (reason.value if reason else "manual"),
                "exit_price": decision_price,
                "entry_price": tracked.inner.entry_price,
                "pnl_pct": pnl.get("price_change_pct"),
                "tokens_sold": ui_amount,
                "signature": sig,
                "open_positions": len([p for p in _positions.values() if not p.sold]),
            })
        else:
            tracked.sell_attempted = False
            _persist_state()


async def _get_spl_ui_amount(mint: str) -> float:
    """Read the wallet's UI balance for a given SPL mint via JSON-RPC."""
    import os
    rpc = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
    owner = os.getenv("WALLET_PUBKEY", "")
    if not owner:
        raise RuntimeError("WALLET_PUBKEY not set")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            owner,
            {"mint": mint},
            {"encoding": "jsonParsed"},
        ],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(rpc, json=payload)
        r.raise_for_status()
        data = r.json()
    accounts = (data.get("result") or {}).get("value") or []
    total = 0.0
    for acct in accounts:
        info = acct.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        amt = info.get("tokenAmount", {}).get("uiAmount") or 0
        total += float(amt)
    return total


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
) -> Optional[str]:
    """Returns the tx signature on success, None on any failure."""
    bus.publish("decide", {"action": action, "mint": mint, "reason": reason})
    payload: Dict[str, Any] = {
        "policyId": cfg.policy_id,
        "tx": tx_b64,
        "action": action,
        "lamportsOut": lamports_out,
    }
    if mint:
        payload["mint"] = mint
    global _session_lost
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{config.TRADER_BASE_URL}/api/auto/sign-and-send", json=payload)
            if r.status_code == 403:
                bus.publish("rejected", {"action": action, "mint": mint, "reason": r.text})
                # 403 from the loopback path almost always means the active
                # session was ended. Mark the runner as session-lost so the
                # main loop bails on the next tick instead of retrying every
                # sell forever.
                if "no active session" in r.text or "policy denied" in r.text:
                    _session_lost = True
                return None
            # 423 = wallet manually locked but session still alive. Keep the
            # runner going; signing will resume when the wallet unlocks.
            if r.status_code == 423:
                bus.publish("paused", {"action": action, "mint": mint, "reason": "wallet locked"})
                return None
            r.raise_for_status()
            data = r.json()
        sig = data.get("signature")
        bus.publish("executed", {
            "action": action, "mint": mint, "signature": sig, "reason": reason,
        })
        return sig
    except Exception as e:  # noqa: BLE001
        bus.publish("error", {"action": action, "mint": mint, "message": str(e)})
        return None
