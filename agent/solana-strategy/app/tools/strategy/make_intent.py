"""Emit a TradeIntent from strategy reasoning.

This tool never signs or broadcasts. It returns a structured intent that
the caller (router or desktop) shows to the user for confirmation, then
forwards to the trader service for execution.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

_VALID_ACTIONS = {"swap", "transfer", "pumpfun_buy", "pumpfun_sell"}


class MakeIntentTool(BaseTool):
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="make_trade_intent",
            display_name="Make Trade Intent",
            category=ToolCategory.strategy,
            description=(
                "Build a structured TradeIntent that the user can confirm and "
                "the trader service can execute. Use this once you've decided "
                "on a trade — never sign or broadcast directly."
            ),
            capabilities=["intent-emission"],
            auth_level=AuthLevel.high,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    choices=sorted(_VALID_ACTIONS),
                    description="Which trade to perform",
                ),
                ToolParameter(
                    name="params",
                    type="string",
                    description=(
                        "JSON object of action-specific params. "
                        "swap: {outputMint, amount, inputMint?, slippageBps?}. "
                        "transfer: {to, amount, mint?}."
                    ),
                ),
                ToolParameter(
                    name="reason",
                    type="string",
                    required=False,
                    default="",
                    description="Why this trade — shown to the user before they confirm",
                ),
                ToolParameter(
                    name="confidence",
                    type="number",
                    required=False,
                    default=0.5,
                    description="0.0 - 1.0 model confidence",
                ),
            ],
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = str(params.get("action", "")).strip()
        if action not in _VALID_ACTIONS:
            return ToolResult(success=False, error=f"action must be one of {sorted(_VALID_ACTIONS)}")

        raw = params.get("params")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError as e:
            return ToolResult(success=False, error=f"params JSON parse error: {e}")
        if not isinstance(payload, dict):
            return ToolResult(success=False, error="params must be a JSON object")

        intent = {
            "action": action,
            "params": payload,
            "reason": str(params.get("reason", "")),
            "confidence": float(params.get("confidence", 0.5)),
            "source_tool": "make_trade_intent",
        }

        return ToolResult(
            success=True,
            raw_output=f"INTENT: {action} {payload} ({intent['confidence']:.2f}) — {intent['reason']}",
            structured_output={"intent": intent},
        )
