"""Pydantic models for Legal RAG agent."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    user_id: str = "default"
    message: str
    stream: bool = False


class Citation(BaseModel):
    chunk_id: str
    source: str
    section: str = ""
    text_excerpt: str
    score: float


class GraphPath(BaseModel):
    nodes: List[str]
    edges: List[str]


class QueryResponse(BaseModel):
    response: str
    citations: List[Citation] = Field(default_factory=list)
    task_type: str = ""
    graph_paths: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)


class IngestStatus(BaseModel):
    ingest_id: str
    status: str  # pending | processing | done | failed
    progress: float = 0.0
    error: Optional[str] = None
    chunk_count: int = 0
    entity_count: int = 0
    filename: str = ""
