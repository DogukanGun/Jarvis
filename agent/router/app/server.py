"""
Router Agent FastAPI Server

Central orchestrator that routes user messages to sub-agents
(thinker, web_fetcher) with memory integration.
"""

import logging
import time
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.models import AgentStatus, ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis Router",
    description="Central orchestrator for Jarvis AI agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation store (per user_id)
_conversations: Dict[str, List[Dict[str, str]]] = {}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Process a user message through the router graph.

    1. Retrieves memory context
    2. Classifies intent (chat / research / web_fetch)
    3. Invokes appropriate sub-agent
    4. Generates response
    5. Writes to memory
    """
    from app.graphs.router_graph import run_router

    # Get conversation history
    history = _conversations.get(req.user_id, [])

    t0 = time.time()
    result = run_router(
        user_id=req.user_id,
        message=req.message,
        conversation_history=history,
    )
    duration_ms = round((time.time() - t0) * 1000)

    response_text = result.get("response", "Sorry, I couldn't process that.")
    intent = result.get("intent", "chat")
    tools_used = result.get("tools_used", [])

    # Update conversation history
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": response_text})
    # Keep last 20 messages
    _conversations[req.user_id] = history[-20:]

    return ChatResponse(
        response=response_text,
        intent=intent,
        tools_used=tools_used,
        metadata={
            "duration_ms": duration_ms,
            "user_id": req.user_id,
        },
    )


@app.get("/api/health")
async def health():
    """Health check with sub-agent connectivity."""
    return {
        "status": "ok",
        "service": "jarvis-router",
        "port": config.ROUTER_PORT,
    }


@app.get("/api/agents/status")
async def agents_status():
    """Check health of all connected sub-agents."""
    from app.clients.thinker_client import ThinkerClient
    from app.clients.web_fetcher_client import WebFetcherClient
    from app.clients.memory_client import MemoryClient
    from app.clients.swiss_knife_client import SwissKnifeClient

    agents = []

    # Thinker
    tc = ThinkerClient()
    agents.append(AgentStatus(
        name="thinker",
        url=config.THINKER_BASE_URL,
        healthy=tc.health_check(),
    ))
    tc.close()

    # Web Fetcher
    wf = WebFetcherClient()
    agents.append(AgentStatus(
        name="web_fetcher",
        url=config.WEB_FETCHER_BASE_URL,
        healthy=wf.health_check(),
    ))
    wf.close()

    # Memory
    mc = MemoryClient()
    agents.append(AgentStatus(
        name="memory",
        url=config.MEMORY_BASE_URL,
        healthy=mc.health_check(),
    ))
    mc.close()

    # Swiss Army Knife
    sk = SwissKnifeClient()
    agents.append(AgentStatus(
        name="swiss_army_knife",
        url=config.SWISS_KNIFE_BASE_URL,
        healthy=sk.health_check(),
    ))
    sk.close()

    return {"agents": [a.model_dump() for a in agents]}
