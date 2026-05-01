"""Solana Strategy — FastAPI Server."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import config
from app.models import ExecuteRequest, ExecuteResponse, ToolListResponse
from app.tools.registry import ToolRegistry
from app.tools.strategy.fetch_ohlcv import FetchOhlcvTool
from app.tools.strategy.indicator_signal import IndicatorSignalTool
from app.tools.strategy.make_intent import MakeIntentTool
from app.tools.strategy.copy_trade_watcher import CopyTradeWatcherTool
from app.auto import runner as auto_runner
from app.auto.events import bus

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ToolRegistry.register(FetchOhlcvTool())
    ToolRegistry.register(IndicatorSignalTool())
    ToolRegistry.register(MakeIntentTool())
    ToolRegistry.register(CopyTradeWatcherTool())
    logger.info("Registered %d strategy tools.", len(ToolRegistry.list_tools()))
    yield
    # Best-effort shutdown of any auto runner.
    try:
        await auto_runner.stop()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(
    title="Solana Strategy",
    description="Indicator-driven trading strategy agent for Jarvis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": config.AGENT_ID, "tools": len(ToolRegistry.list_tools())}


@app.get("/api/tools", response_model=ToolListResponse)
async def list_tools():
    tools = [t.model_dump() for t in ToolRegistry.list_tools()]
    return ToolListResponse(tools=tools, total=len(tools))


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    from app.agent.runner import run_agent

    try:
        result = await run_agent(
            user_id=req.user_id,
            message=req.message,
            target_tools=req.target_tools,
            parameters=req.parameters,
            confirmed=req.confirmed,
        )
        return ExecuteResponse(
            response=result.get("response", ""),
            report=result.get("report", {}),
            tools_used=result.get("tools_used", []),
            findings=result.get("findings", []),
            intents=result.get("intents", []),
        )
    except Exception as e:
        logger.error("Execute error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Auto-trade ─────────────────────────────────────────────────────────────────


class AutoStartRequest(BaseModel):
    strategy: str = Field(..., description="indicator | copy_trade | pumpfun_snipe")
    policy_id: str = Field(..., min_length=8)
    max_trade_sol: float = Field(..., gt=0)
    total_budget_sol: float = Field(..., gt=0)
    expires_at: float = Field(..., description="Unix epoch seconds")
    interval_sec: int = Field(30, ge=5, le=600)
    watchlist: List[str] = Field(default_factory=list)
    target_wallets: List[str] = Field(default_factory=list)
    copy_ratio: float = Field(0.01, gt=0, le=1.0)
    rug_score_max: float = Field(0.5, ge=0, le=1.0)
    min_liquidity_sol: float = Field(5.0, ge=0)
    max_buy_sol: float = Field(0.01, gt=0)


@app.post("/api/auto/start")
async def auto_start(req: AutoStartRequest) -> Dict[str, Any]:
    if auto_runner.is_running():
        raise HTTPException(409, "auto-trade runner already active; stop first")
    if req.strategy not in ("indicator", "copy_trade", "pumpfun_snipe"):
        raise HTTPException(400, f"unknown strategy {req.strategy}")
    if req.total_budget_sol < req.max_trade_sol:
        raise HTTPException(400, "total_budget_sol must be >= max_trade_sol")
    if req.expires_at <= time.time():
        raise HTTPException(400, "expires_at must be in the future")

    cfg = auto_runner.RunnerConfig(
        strategy=req.strategy,
        policy_id=req.policy_id,
        max_trade_sol=req.max_trade_sol,
        total_budget_sol=req.total_budget_sol,
        expires_at=req.expires_at,
        interval_sec=req.interval_sec,
        watchlist=req.watchlist,
        target_wallets=req.target_wallets,
        copy_ratio=req.copy_ratio,
        rug_score_max=req.rug_score_max,
        min_liquidity_sol=req.min_liquidity_sol,
        max_buy_sol=req.max_buy_sol,
    )
    await auto_runner.start(cfg)
    return {"ok": True, "strategy": req.strategy}


@app.post("/api/auto/stop")
async def auto_stop() -> Dict[str, Any]:
    await auto_runner.stop()
    return {"ok": True}


@app.get("/api/auto/status")
async def auto_status() -> Dict[str, Any]:
    cfg = auto_runner.current_config()
    return {
        "running": auto_runner.is_running(),
        "strategy": cfg.strategy if cfg else None,
        "policy_id": cfg.policy_id if cfg else None,
        "expires_at": cfg.expires_at if cfg else None,
    }


@app.get("/api/auto/events")
async def auto_events():
    async def gen():
        async for chunk in bus.stream():
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")
