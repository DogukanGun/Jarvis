"""
Episodic Memory HTTP API

FastAPI server exposing the MainGraph for memory operations.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from app.graphs.main_graph.graph import run_main_graph
from app.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis Episodic Memory API",
    description="API for querying and storing episodic memories",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request model for querying memory with context"""
    user_id: str
    prompt: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for memory query"""
    user_id: str
    prompt: str
    response: Optional[str] = None
    retrieved_episodes: list = []
    mem0_items: list = []
    task_type: Optional[str] = None
    entities: list = []
    error: Optional[str] = None


class StoreRequest(BaseModel):
    """Request model for storing a memory"""
    user_id: str
    prompt: str
    response: str
    context: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="episodic-memory")


@app.post("/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """
    Query episodic memory and get context for a prompt.

    This runs the full MainGraph which:
    1. Preprocesses the input
    2. Loads mem0 context if needed
    3. Retrieves relevant episodes
    4. Composes context
    5. Returns context (without LLM step for pure retrieval)
    """
    try:
        logger.info(f"Query request for user {request.user_id}: {request.prompt[:50]}...")

        # Run the main graph
        result = run_main_graph(
            user_id=request.user_id,
            prompt=request.prompt,
            context=request.context
        )

        # Extract relevant fields from result
        response = QueryResponse(
            user_id=request.user_id,
            prompt=request.prompt,
            response=result.get("llm_output") if isinstance(result.get("llm_output"), str) else None,
            retrieved_episodes=result.get("retrieved_episodes", []),
            mem0_items=result.get("mem0_items", []),
            task_type=result.get("task_type"),
            entities=result.get("entities", []),
            error=result.get("retrieval_error") or result.get("llm_error")
        )

        logger.info(f"Query completed. Episodes: {len(response.retrieved_episodes)}, Mem0: {len(response.mem0_items)}")
        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context")
async def get_context(request: QueryRequest):
    """
    Get memory context without running LLM.

    Returns retrieved episodes and mem0 items for the General Agent
    to use in its own LLM call.
    """
    try:
        logger.info(f"Context request for user {request.user_id}: {request.prompt[:50]}...")

        # Run the main graph
        result = run_main_graph(
            user_id=request.user_id,
            prompt=request.prompt,
            context=request.context
        )

        # Build context response
        context_response = {
            "user_id": request.user_id,
            "prompt": request.prompt,
            "normalized_prompt": result.get("normalized_prompt", request.prompt),
            "task_type": result.get("task_type", "general"),
            "entities": result.get("entities", []),
            "retrieved_episodes": result.get("retrieved_episodes", []),
            "mem0_items": result.get("mem0_items", []),
            "llm_context": result.get("llm_context", {}),
        }

        logger.info(f"Context retrieved. Episodes: {len(context_response['retrieved_episodes'])}")
        return context_response

    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store")
async def store_memory(request: StoreRequest):
    """
    Store an interaction in episodic memory.

    This triggers the memory write graph in the background.
    """
    try:
        logger.info(f"Store request for user {request.user_id}")

        # Run the main graph with the interaction
        # The enqueue_memory_write_graph node will handle storage
        context = request.context or {}
        context["store_interaction"] = True
        context["interaction_response"] = request.response

        result = run_main_graph(
            user_id=request.user_id,
            prompt=request.prompt,
            context=context
        )

        return {
            "status": "stored",
            "user_id": request.user_id,
            "memory_job_payload": result.get("memory_job_payload")
        }

    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the API server"""
    import os
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8085"))

    logger.info(f"Starting Episodic Memory API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
