"""Compute indicator-based signals from a series of closes.

Returns the latest values of EMA(9), EMA(21), RSI(14), Bollinger(20),
plus a verdict ('buy' | 'sell' | 'hold') with simple, transparent rules:

- RSI < 30: oversold → buy bias
- RSI > 70: overbought → sell bias
- close < lower band AND RSI < 35: strong buy
- close > upper band AND RSI > 65: strong sell
- EMA9 crossing above EMA21: bullish bias confirmation
- EMA9 crossing below EMA21: bearish bias confirmation
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from app.indicators import bollinger, ema, latest, rsi
from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)


def _verdict(close: float, ema_fast: float, ema_slow: float, rsi_v: float, upper: float, lower: float) -> tuple[str, float, str]:
    notes: List[str] = []
    score = 0.0

    if not math.isnan(rsi_v):
        if rsi_v < 30:
            score += 1.5; notes.append(f"RSI {rsi_v:.1f} oversold")
        elif rsi_v > 70:
            score -= 1.5; notes.append(f"RSI {rsi_v:.1f} overbought")

    if not math.isnan(lower) and close < lower:
        score += 1.0; notes.append("close below lower Bollinger band")
    if not math.isnan(upper) and close > upper:
        score -= 1.0; notes.append("close above upper Bollinger band")

    if not (math.isnan(ema_fast) or math.isnan(ema_slow)):
        if ema_fast > ema_slow:
            score += 0.5; notes.append("EMA9 > EMA21 (bullish bias)")
        else:
            score -= 0.5; notes.append("EMA9 < EMA21 (bearish bias)")

    if score >= 1.0:
        verdict = "buy"
    elif score <= -1.0:
        verdict = "sell"
    else:
        verdict = "hold"

    confidence = min(abs(score) / 3.0, 1.0)
    reason = "; ".join(notes) if notes else "no strong signal"
    return verdict, confidence, reason


class IndicatorSignalTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="indicator_signal",
            display_name="Indicator Signal",
            category=ToolCategory.strategy,
            description=(
                "Compute EMA(9/21), RSI(14), and Bollinger(20) on a list of close "
                "prices and return a buy/sell/hold verdict. Pass `closes` as the most "
                "recent candle close prices in chronological order."
            ),
            capabilities=["technical-analysis"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="closes",
                    type="string",
                    description="JSON array of close prices, oldest first (e.g. '[1.02, 1.04, ...]')",
                ),
                ToolParameter(
                    name="rsi_period",
                    type="integer",
                    required=False,
                    default=14,
                    description="RSI period",
                ),
                ToolParameter(
                    name="bb_period",
                    type="integer",
                    required=False,
                    default=20,
                    description="Bollinger period",
                ),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        import json

        raw = params.get("closes")
        try:
            if isinstance(raw, str):
                closes = [float(x) for x in json.loads(raw)]
            else:
                closes = [float(x) for x in (raw or [])]
        except (TypeError, ValueError) as e:
            return ToolResult(success=False, error=f"closes parse error: {e}")

        if len(closes) < 25:
            return ToolResult(
                success=False,
                error=f"need at least ~25 candles for stable indicators; got {len(closes)}",
            )

        rsi_p = int(params.get("rsi_period", 14))
        bb_p = int(params.get("bb_period", 20))

        ema9 = ema(closes, 9)
        ema21 = ema(closes, 21)
        rsi_series = rsi(closes, rsi_p)
        mid, upper, lower = bollinger(closes, bb_p)

        last_close = closes[-1]
        verdict, confidence, reason = _verdict(
            last_close, latest(ema9), latest(ema21), latest(rsi_series), latest(upper), latest(lower)
        )

        out = {
            "verdict": verdict,
            "confidence": round(confidence, 2),
            "reason": reason,
            "indicators": {
                "close": last_close,
                "ema9": latest(ema9),
                "ema21": latest(ema21),
                "rsi": latest(rsi_series),
                "bb_mid": latest(mid),
                "bb_upper": latest(upper),
                "bb_lower": latest(lower),
            },
        }
        return ToolResult(
            success=True,
            raw_output=f"{verdict.upper()} (conf {confidence:.2f}) — {reason}",
            structured_output=out,
        )
