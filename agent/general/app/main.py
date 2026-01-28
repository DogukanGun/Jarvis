"""FastAPI server for the general agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_config
from .agent import run_agent, create_agent_executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageRequest(BaseModel):
    """Request body for agent messages."""

    message: str


class MessageResponse(BaseModel):
    """Response body for agent messages."""

    response: str
    error: str | None = None


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str
    ollama_host: str
    ollama_model: str
    tool_server_url: str


class CapabilitiesResponse(BaseModel):
    """Response body for capabilities."""

    tools: list[str]
    capabilities: dict[str, list[str]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    config = get_config()
    logger.info(f"Starting agent server...")
    logger.info(f"  Ollama host: {config.ollama_host}")
    logger.info(f"  Ollama model: {config.ollama_model}")
    logger.info(f"  Tool server: {config.tool_server_url}")
    yield
    logger.info("Shutting down agent server...")


app = FastAPI(
    title="Jarvis General Agent",
    description="A general-purpose LangChain ReAct agent with HTTP tool integration",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    config = get_config()
    return HealthResponse(
        status="healthy",
        ollama_host=config.ollama_host,
        ollama_model=config.ollama_model,
        tool_server_url=config.tool_server_url,
    )


@app.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    """Get agent capabilities."""
    return CapabilitiesResponse(
        tools=["web_search", "web_fetch", "exec", "browser", "cron"],
        capabilities={
            "Web & Research": [
                "Search the web using Brave Search or Perplexity",
                "Fetch and extract content from URLs",
                "Research topics and gather information",
            ],
            "Code Execution": [
                "Execute shell commands",
                "Run scripts and build commands",
                "System operations",
            ],
            "Browser Automation": [
                "Open and navigate web pages",
                "Take screenshots",
                "Click elements and fill forms",
                "Extract page content and interactive elements",
            ],
            "Task Scheduling": [
                "Create cron jobs with schedule expressions",
                "List and manage scheduled tasks",
                "Run jobs manually on demand",
            ],
        },
    )


@app.post("/agent", response_model=MessageResponse)
async def agent_endpoint(request: MessageRequest):
    """Process a message through the agent."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        response = await run_agent(request.message)
        return MessageResponse(response=response)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return MessageResponse(response="", error=str(e))


def start():
    """Start the server using uvicorn."""
    import uvicorn

    config = get_config()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    start()
