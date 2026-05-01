"""Pure-Python implementations of common technical indicators.

Clean-room reimplementation. Operates on lists of floats (closes) and
returns lists of indicator values, with NaN for periods that have
insufficient history.
"""

from __future__ import annotations

import math
from typing import List, Tuple


def ema(values: List[float], period: int) -> List[float]:
    if period <= 0:
        raise ValueError("period must be > 0")
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out: List[float] = []
    prev: float | None = None
    for i, v in enumerate(values):
        if i + 1 < period:
            out.append(math.nan)
            continue
        if prev is None:
            seed = sum(values[: period]) / period
            out.append(seed)
            prev = seed
            continue
        cur = v * k + prev * (1 - k)
        out.append(cur)
        prev = cur
    return out


def rsi(values: List[float], period: int = 14) -> List[float]:
    if period <= 0:
        raise ValueError("period must be > 0")
    n = len(values)
    if n == 0:
        return []
    out = [math.nan] * n
    if n <= period:
        return out

    gains: List[float] = [0.0] * n
    losses: List[float] = [0.0] * n
    for i in range(1, n):
        diff = values[i] - values[i - 1]
        gains[i] = max(diff, 0.0)
        losses[i] = max(-diff, 0.0)

    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
    out[period] = 100.0 - 100.0 / (1.0 + rs) if avg_loss > 0 else 100.0

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def bollinger(values: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """Returns (mid, upper, lower)."""
    n = len(values)
    if period <= 1:
        raise ValueError("period must be > 1")
    mid = [math.nan] * n
    upper = [math.nan] * n
    lower = [math.nan] * n
    if n < period:
        return mid, upper, lower
    for i in range(period - 1, n):
        window = values[i - period + 1 : i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        sd = math.sqrt(var)
        mid[i] = m
        upper[i] = m + num_std * sd
        lower[i] = m - num_std * sd
    return mid, upper, lower


def latest(seq: List[float]) -> float:
    """Return the last non-NaN value, or NaN if there's none."""
    for v in reversed(seq):
        if not math.isnan(v):
            return v
    return math.nan
