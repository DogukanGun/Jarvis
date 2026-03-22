"""Request/response schemas for the router API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="default")
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: str = "chat"
    tools_used: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentStatus(BaseModel):
    name: str
    url: str
    healthy: bool
    details: Optional[str] = None
