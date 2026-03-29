"""Swiss Army Knife - FastAPI Server."""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import config
from app.models import (
    ExecuteRequest,
    ExecuteResponse,
    AsyncExecuteResponse,
    ConfirmRequest,
    JobStatusResponse,
    CommandRequest,
    CommandResponse,
    ToolListResponse,
)
from app.tools.registry import ToolRegistry

# Import all tool modules to trigger registration
from app.tools.wifi import aircrack, wifite, reaver, btlejack
from app.tools.network import bettercap, ettercap, mitmproxy_tool, scapy_tool
from app.tools.exploitation import metasploit, sqlmap, setoolkit
from app.tools.post_exploitation import merlin, sliver
from app.tools.password import john
from app.tools.monitoring import ntopng, lynis
from app.tools.ctf import rootthebox

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Swiss Army Knife",
    description="Security/network tool agent for Jarvis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# SSE broadcast infrastructure
# ---------------------------------------------------------------------------
_event_subscribers: list[asyncio.Queue] = []
_event_history: deque = deque(maxlen=500)


def broadcast_event(event: dict):
    """Push an event to all connected SSE clients and history buffer."""
    event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    _event_history.append(event)
    for queue in list(_event_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": config.AGENT_ID}


@app.get("/api/tools", response_model=ToolListResponse)
async def list_tools():
    """List all available tools and their metadata."""
    tools = [t.model_dump() for t in ToolRegistry.list_tools()]
    return ToolListResponse(tools=tools, total=len(tools))


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    """Execute the tool graph synchronously, tracking via job_store for dashboard visibility."""
    from app.graphs.tool_graph import run_tool_graph
    from app.services.job_store import job_store

    job_id = job_store.create_job(tool_name="graph", metadata={"message": req.message})
    job_store.update_status(job_id, "running")

    try:
        result = await run_tool_graph(
            user_id=req.user_id,
            message=req.message,
            target_tools=req.target_tools,
            parameters=req.parameters,
            confirmed=req.confirmed,
            job_id=job_id,
        )

        if result.get("requires_confirmation") and not result.get("confirmed"):
            job_store.update_status(job_id, "waiting_confirmation")
            return ExecuteResponse(
                response="Confirmation required before execution.",
                requires_confirmation=True,
                confirmation_prompt=result.get("confirmation_prompt", ""),
                job_id=job_id,
            )

        job_store.complete_job(job_id, result)

        return ExecuteResponse(
            response=result.get("response", ""),
            report=result.get("report", {}),
            tools_used=result.get("tools_used", []),
            findings=result.get("findings", []),
            job_ids=[job_id],
        )
    except Exception as e:
        logger.error(f"Execute error: {e}")
        job_store.fail_job(job_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute/async", response_model=AsyncExecuteResponse)
async def execute_async(req: ExecuteRequest):
    """Start async execution, return job_id."""
    from app.services.job_store import job_store
    import asyncio

    job_id = job_store.create_job(tool_name="graph", metadata={"message": req.message})
    job_store.update_status(job_id, "running")

    async def _run():
        try:
            from app.graphs.tool_graph import run_tool_graph  # inside try so import errors are caught
            result = await run_tool_graph(
                user_id=req.user_id,
                message=req.message,
                target_tools=req.target_tools,
                parameters=req.parameters,
                confirmed=req.confirmed,
                job_id=job_id,
            )
            job_store.complete_job(job_id, result)

            # Publish to Kafka so the router gets the result without polling
            try:
                from app.kafka.producer import SwissKnifeProducer
                producer = SwissKnifeProducer()
                producer.publish_task_completed(
                    task_id=job_id,
                    result=result,
                    thread_id=job_id,
                )
                producer.publish_scan_result(
                    task_id=job_id,
                    findings=result.get("findings", []),
                    tools_used=result.get("tools_used", []),
                    thread_id=job_id,
                )
                producer.close()
            except Exception as kafka_err:
                logger.warning("Failed to publish job %s result to Kafka: %s", job_id, kafka_err)

        except Exception as e:
            logger.exception("Async job %s failed: %s", job_id, e)
            job_store.fail_job(job_id, str(e))

            try:
                from app.kafka.producer import SwissKnifeProducer
                producer = SwissKnifeProducer()
                producer.publish_task_failed(task_id=job_id, error=str(e), thread_id=job_id)
                producer.close()
            except Exception as kafka_err:
                logger.warning("Failed to publish job %s failure to Kafka: %s", job_id, kafka_err)

    def _on_task_done(t: asyncio.Task) -> None:
        if not t.cancelled() and t.exception():
            exc = t.exception()
            logger.error("Async task for job %s raised unhandled exception: %s", job_id, exc)
            job_store.fail_job(job_id, str(exc))

    task = asyncio.create_task(_run())
    task.add_done_callback(_on_task_done)
    return AsyncExecuteResponse(
        job_id=job_id,
        status="started",
        message="Execution started. Poll /api/jobs/{job_id} for status.",
    )


@app.post("/api/execute/confirm/{job_id}")
async def confirm_execution(job_id: str, req: ConfirmRequest):
    """Confirm or deny execution of HIGH/CRITICAL tools."""
    from app.services.job_store import job_store

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if req.confirmed:
        job_store.confirm_job(job_id)
        return {"status": "confirmed", "job_id": job_id}
    else:
        job_store.fail_job(job_id, "User denied execution")
        return {"status": "denied", "job_id": job_id}


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get async job status."""
    from app.services.job_store import job_store

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        tool_name=job.get("tool_name", ""),
        started_at=job.get("started_at", ""),
        result=job.get("result"),
    )


@app.get("/api/jobs/{job_id}/output")
async def get_job_output(job_id: str, since: int = 0):
    """Get buffered output from a long-running tool."""
    from app.services.session_manager import session_manager

    output = await session_manager.get_output(job_id, since=since)
    if output is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"job_id": job_id, "output": output, "offset": since}


@app.post("/api/sessions/{job_id}/command", response_model=CommandResponse)
async def send_session_command(job_id: str, req: CommandRequest):
    """Send a command to an interactive session."""
    from app.services.session_manager import session_manager

    result = await session_manager.send_command(job_id, req.command)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return CommandResponse(output=result, success=True)


@app.get("/api/jobs")
async def list_all_jobs(status: str = None):
    """List all jobs, optionally filtered by status."""
    from app.services.job_store import job_store

    jobs = job_store.list_jobs(status=status)
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/api/events")
async def sse_events():
    """Server-Sent Events stream for real-time monitoring."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _event_subscribers.append(queue)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _event_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/events/history")
async def event_history():
    """Return recent event history for initial page load."""
    return list(_event_history)
