#!/usr/bin/env python3
"""
Jarvis Hacker Agent - FastAPI Server

Exposes the hacker agent as a REST API for integration with other agents.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.graphs.hacker_graph import run_hacker_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory task storage (replace with Redis/DB for production)
tasks: Dict[str, "TaskResult"] = {}


# --- Enums ---

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Request/Response Models ---

class RunTaskRequest(BaseModel):
    """Request to run a hacker agent task."""
    task: str = Field(..., description="The task description for the agent", min_length=1)
    user_id: str = Field(default="default", description="User identifier for tracking")
    max_steps: int = Field(default=10, ge=1, le=50, description="Maximum execution steps")
    async_mode: bool = Field(default=False, description="Run task asynchronously")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task": "Scan the network 192.168.1.0/24 and find active hosts",
                    "user_id": "agent-001",
                    "max_steps": 10,
                    "async_mode": False
                }
            ]
        }
    }


class ToolExecution(BaseModel):
    """Details of a tool execution."""
    command: str
    exit_code: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class TaskResult(BaseModel):
    """Result of a hacker agent task."""
    task_id: str
    status: TaskStatus
    task: str
    user_id: str
    answer: Optional[str] = None
    tool_executions: List[ToolExecution] = []
    errors: List[str] = []
    created_at: datetime
    completed_at: Optional[datetime] = None


class RunTaskResponse(BaseModel):
    """Response for task execution."""
    task_id: str
    status: TaskStatus
    message: str
    result: Optional[TaskResult] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime


# --- Helper Functions ---

def _run_agent_sync(task_id: str, request: RunTaskRequest) -> TaskResult:
    """Run the hacker agent synchronously."""
    task_result = tasks[task_id]
    task_result.status = TaskStatus.RUNNING

    try:
        result = run_hacker_graph(
            user_input=request.task,
            user_id=request.user_id,
            max_steps=request.max_steps,
        )

        # Extract tool executions
        tool_history = result.get("tool_history", [])
        tool_executions = [
            ToolExecution(
                command=t.get("cmd", "unknown"),
                exit_code=t.get("exit_code", -1),
                stdout=t.get("stdout"),
                stderr=t.get("stderr"),
            )
            for t in tool_history
        ]

        # Update task result
        task_result.status = TaskStatus.COMPLETED
        task_result.answer = result.get("final_answer")
        task_result.tool_executions = tool_executions
        task_result.errors = result.get("errors", [])
        task_result.completed_at = datetime.utcnow()

    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        task_result.status = TaskStatus.FAILED
        task_result.errors.append(str(e))
        task_result.completed_at = datetime.utcnow()

    return task_result


async def _run_agent_async(task_id: str, request: RunTaskRequest):
    """Run the hacker agent asynchronously in a thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_agent_sync, task_id, request)


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Hacker Agent API starting up...")
    yield
    logger.info("Hacker Agent API shutting down...")


# --- FastAPI App ---

app = FastAPI(
    title="Jarvis Hacker Agent API",
    description="REST API for the Jarvis Hacker Agent - Security reconnaissance and network analysis",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="hacker-agent",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@app.post("/run", response_model=RunTaskResponse, tags=["Tasks"])
async def run_task(request: RunTaskRequest, background_tasks: BackgroundTasks):
    """
    Run a hacker agent task.

    - **task**: The task description (e.g., "Scan network 192.168.1.0/24")
    - **user_id**: Identifier for the requesting user/agent
    - **max_steps**: Maximum number of tool execution steps
    - **async_mode**: If true, returns immediately with task_id for polling
    """
    task_id = str(uuid.uuid4())

    # Create initial task result
    task_result = TaskResult(
        task_id=task_id,
        status=TaskStatus.PENDING,
        task=request.task,
        user_id=request.user_id,
        created_at=datetime.utcnow(),
    )
    tasks[task_id] = task_result

    if request.async_mode:
        # Run in background
        background_tasks.add_task(_run_agent_async, task_id, request)
        return RunTaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task queued for execution. Poll /tasks/{task_id} for status.",
        )
    else:
        # Run synchronously
        result = _run_agent_sync(task_id, request)
        return RunTaskResponse(
            task_id=task_id,
            status=result.status,
            message="Task completed" if result.status == TaskStatus.COMPLETED else "Task failed",
            result=result,
        )


@app.get("/tasks/{task_id}", response_model=TaskResult, tags=["Tasks"])
async def get_task(task_id: str):
    """
    Get the status and result of a task.

    Use this endpoint to poll for async task completion.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return tasks[task_id]


@app.get("/tasks", response_model=List[TaskResult], tags=["Tasks"])
async def list_tasks(
    user_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    limit: int = 100,
):
    """
    List all tasks, optionally filtered by user_id or status.
    """
    results = list(tasks.values())

    if user_id:
        results = [t for t in results if t.user_id == user_id]

    if status:
        results = [t for t in results if t.status == status]

    # Sort by created_at descending
    results.sort(key=lambda t: t.created_at, reverse=True)

    return results[:limit]


@app.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str):
    """Delete a task from the task store."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    del tasks[task_id]
    return {"message": f"Task {task_id} deleted"}


# --- Main ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
