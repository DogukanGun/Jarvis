"""Pull recent close-price history for a Solana token.

Defaults to GeckoTerminal (free, no API key). Uses Birdeye instead when
BIRDEYE_API_KEY is configured. Both produce a chronological list of close
prices ready for indicator computation.
"""

from __future__ import annotations

from typing import Any, Dict

from app.market_data import fetch_closes, source_name
from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)


_VALID_INTERVALS = ["1m", "5m", "15m", "1H", "4H", "1D"]


class FetchOhlcvTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="fetch_ohlcv",
            display_name="Fetch OHLCV",
            category=ToolCategory.market,
            description=(
                "Fetch recent OHLCV close-price history for a Solana token mint. "
                "Returns a chronological list of closes ready for indicator "
                "computation. Free GeckoTerminal data is used by default; if "
                "BIRDEYE_API_KEY is set, Birdeye is used instead."
            ),
            capabilities=["price-history"],
            auth_level=AuthLevel.low,
            parameters=[
                ToolParameter(
                    name="mint",
                    type="string",
                    description="Solana SPL token mint address",
                ),
                ToolParameter(
                    name="interval",
                    type="string",
                    required=False,
                    default="15m",
                    choices=_VALID_INTERVALS,
                    description="Candle interval",
                ),
                ToolParameter(
                    name="lookback",
                    type="integer",
                    required=False,
                    default=200,
                    description="Number of candles to fetch",
                ),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        mint = str(params.get("mint", "")).strip()
        interval = str(params.get("interval", "15m"))
        lookback = int(params.get("lookback", 200))

        if not mint:
            return ToolResult(success=False, error="mint required")
        if interval not in _VALID_INTERVALS:
            return ToolResult(success=False, error=f"interval must be one of {_VALID_INTERVALS}")

        try:
            closes = await fetch_closes(mint, interval, lookback)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=f"price-history fetch failed: {e}")

        if not closes:
            return ToolResult(
                success=False,
                error=f"no candles returned for {mint} ({interval})",
            )

        return ToolResult(
            success=True,
            raw_output=f"Fetched {len(closes)} candles ({interval}) for {mint} via {source_name()}",
            structured_output={
                "mint": mint,
                "interval": interval,
                "closes": closes,
                "source": source_name(),
            },
        )
