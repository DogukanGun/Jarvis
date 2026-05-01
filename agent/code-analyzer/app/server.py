"""Code Analyzer — FastAPI Server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.models import ExecuteRequest, ExecuteResponse, ToolListResponse
from app.tools.registry import ToolRegistry
from app.tools.code.index_repo import IndexRepoTool
from app.tools.code.query_code import QueryCodeTool
from app.tools.code.get_context import GetContextTool
from app.tools.code.get_impact import GetImpactTool
from app.tools.code.get_routes import GetRoutesTool

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ToolRegistry.register(IndexRepoTool())
    ToolRegistry.register(QueryCodeTool())
    ToolRegistry.register(GetContextTool())
    ToolRegistry.register(GetImpactTool())
    ToolRegistry.register(GetRoutesTool())
    logger.info("Registered %d code analysis tools.", len(ToolRegistry.list_tools()))
    yield


app = FastAPI(
    title="Code Analyzer",
    description="Codebase knowledge graph agent for Jarvis",
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
        )
    except Exception as e:
        logger.error("Execute error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
