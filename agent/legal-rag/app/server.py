"""Legal RAG — FastAPI server."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import config
from app.models import IngestStatus, QueryRequest, QueryResponse
from app.pipeline import RagPipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_pipeline: RagPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = RagPipeline()
    await _pipeline.initialize()
    logger.info("Legal RAG pipeline ready.")
    yield


app = FastAPI(
    title="Legal RAG",
    description="Graph-augmented legal document retrieval for Jarvis",
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
async def health() -> Dict[str, Any]:
    chunks = len(_pipeline.chunk_store.all()) if _pipeline else 0
    return {"status": "ok", "agent": config.AGENT_ID, "chunks_indexed": chunks}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    if req.stream:
        raise HTTPException(400, "Use /api/events for streaming")
    try:
        return await _pipeline.query(req)
    except Exception as e:
        logger.error("Query error: %s", e)
        raise HTTPException(500, str(e))


@app.post("/api/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)) -> Dict[str, str]:
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    if file.content_type not in ("application/pdf", "text/plain") and not (
        file.filename or ""
    ).lower().endswith((".pdf", ".txt")):
        raise HTTPException(400, "Only PDF and TXT files are supported")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Empty file")
    ingest_id = await _pipeline.ingest(pdf_bytes, file.filename or "document")
    return {"ingest_id": ingest_id, "status": "pending"}


@app.get("/api/ingest/status/{ingest_id}", response_model=IngestStatus)
async def ingest_status(ingest_id: str) -> IngestStatus:
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    status = _pipeline.ingest_status(ingest_id)
    if status is None:
        raise HTTPException(404, f"Ingest job {ingest_id} not found")
    return status


@app.get("/api/events")
async def sse_events(request: Request) -> StreamingResponse:
    """Server-Sent Events stream — emits progress events during active ingest/query."""
    async def _gen():
        while True:
            if await request.is_disconnected():
                break
            # Collect all in-flight ingest jobs and emit their status
            if _pipeline:
                for ingest_id, status in list(_pipeline.orchestrator._status.items()):
                    if status.status in ("processing", "pending"):
                        import json
                        data = json.dumps({
                            "kind": "ingest-progress",
                            "ingest_id": ingest_id,
                            "progress": status.progress,
                            "chunk_count": status.chunk_count,
                            "entity_count": status.entity_count,
                            "filename": status.filename,
                        })
                        yield f"data: {data}\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(_gen(), media_type="text/event-stream")
