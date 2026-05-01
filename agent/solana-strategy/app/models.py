from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    user_id: str = "default"
    message: str
    target_tools: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    confirmed: bool = False


class ExecuteResponse(BaseModel):
    response: str
    report: Dict[str, Any] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    intents: List[Dict[str, Any]] = Field(default_factory=list)
    job_ids: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    job_id: Optional[str] = None


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    total: int


class TradeIntent(BaseModel):
    """A trade signal emitted by strategy tools.

    Strategy never signs or broadcasts. Intents are returned to the caller
    (router or desktop), who confirms with the user, then forwards to the
    trader service for execution.
    """

    action: str = Field(..., description="One of: swap, transfer, pumpfun_buy, pumpfun_sell")
    params: Dict[str, Any] = Field(..., description="Action-specific parameters")
    reason: str = Field("", description="Why this intent was generated")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    source_tool: Optional[str] = None
